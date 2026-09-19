"""P0-02 — data/artifact schemas, orientation and provenance checks.

Validation of PROTOCOL §6 only; this module must not redefine it (D006 guard
clause). What `contract.py` already covers (orientation, dtype, identifiers,
donor column, emptiness, truth shapes, row-sum-to-1 units) is not repeated
here. What was missing from the ledger row — "schema tests; manifest examples;
explicit expression units" — lives here:

1. **Explicit expression units** (§6.2). Three normalizations circulate (raw
   integer counts, training-scale `X`, TPM) and conflating them silently
   invalidates a result — the same failure class D013 records for spectra
   (`Spectra` refuses a cross-unit comparison) and D016 measures for `s_g`
   drift. `ExpressionMatrix` carries its unit system as data; `require_units`
   raises `UnitMismatch` instead of returning a number on the wrong scale.
2. **Manifest examples.** `DATASET_MANIFEST_KEYS` freezes the required keys of
   a dataset manifest (§6.6: scenario, tier, parameters, seed, replicate,
   protocol version, hash; plus file hashes after writing). The committed
   example at `docs/benchmarks/registry/dataset_manifest_example.json`
   shows the shape without carrying any large data.
3. **Rank-grid validation.** Candidate grids come from run configuration and
   are frozen before the run (§1.1, §1.4: never auto-expand). An empty grid,
   a non-positive rank or a duplicated rank is a schema error, refused here
   rather than producing a silently degenerate selector input.
"""

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from .contract import ContractViolation

__all__ = [
    "EXPRESSION_UNITS",
    "UnitMismatch",
    "ExpressionMatrix",
    "DATASET_MANIFEST_KEYS",
    "validate_dataset_manifest",
    "validate_rank_grid",
]

# PROTOCOL §6.2, exactly: simulator output, X (§3.2), and the TPM unit that
# `gene_spectra_tpm` artifacts carry. No other string is a unit.
EXPRESSION_UNITS = ("raw_counts", "training_scale", "tpm")


class UnitMismatch(ContractViolation):
    """An operation was given matrices in different expression units."""


@dataclass(frozen=True)
class ExpressionMatrix:
    """A matrix with its §6.2 unit system attached.

    `require_units` is the only way to unwrap: code that needs a particular
    unit names it, and a mismatch raises instead of computing on the wrong
    scale. This mirrors `recovery.Spectra` (D013) — the lesson there was that
    a docstring cannot fail a test run, but a type that refuses can.
    """

    matrix: np.ndarray
    units: str

    def __post_init__(self):
        if self.units not in EXPRESSION_UNITS:
            raise ContractViolation(
                f"unknown expression units {self.units!r}; expected one of "
                f"{list(EXPRESSION_UNITS)} (PROTOCOL §6.2)"
            )

    def require_units(self, expected):
        """Return the matrix iff its units equal `expected`, else raise."""
        if self.units != expected:
            raise UnitMismatch(
                f"expected {expected} but got {self.units} (PROTOCOL §6.2). "
                "Convert explicitly instead of comparing across unit systems."
            )
        return self.matrix


# §6.6 manifest keys. `files` appears only after writing (io.write_dataset
# adds it); every other key must be present from generation.
DATASET_MANIFEST_KEYS = (
    "scenario_id",
    "tier",
    "parameters",
    "seed",
    "simulation_replicate",
    "protocol_version",
    "dataset_manifest_hash",
)


def validate_dataset_manifest(manifest):
    """Check a dataset manifest carries the §6.6 provenance, nothing invented.

    Returns the manifest hash when valid. Unknown extra keys are permitted
    (writers add `files` after writing); missing keys or a non-64-hex hash
    are refused.
    """
    missing = [k for k in DATASET_MANIFEST_KEYS if k not in manifest]
    if missing:
        raise ContractViolation(
            f"dataset manifest is missing keys {missing} (PROTOCOL §6.6)"
        )
    digest = manifest["dataset_manifest_hash"]
    if not (isinstance(digest, str) and len(digest) == 64):
        raise ContractViolation(
            "dataset_manifest_hash must be a full-length hex digest (§7 forbids "
            "truncation in recorded output)"
        )
    try:
        int(digest, 16)
    except ValueError:
        raise ContractViolation("dataset_manifest_hash is not hexadecimal")
    return digest


def validate_rank_grid(ranks):
    """Check a candidate rank grid before any fit or selection reads it.

    Non-empty, positive integers, unique — anything else would silently
    degenerate the §1.4 edge cases (an empty grid is not "all K failed", a
    duplicated rank double-counts one K in the largest-among-stable rule).
    Returns the sorted tuple the selector consumes.
    """
    grid = tuple(ranks)
    if not grid:
        raise ContractViolation("candidate rank grid is empty (PROTOCOL §1.1)")
    if any(not isinstance(k, (int, np.integer)) or int(k) <= 0 for k in grid):
        raise ContractViolation(
            f"candidate ranks must be positive integers, got {list(grid)}"
        )
    if len(set(int(k) for k in grid)) != len(grid):
        raise ContractViolation(
            f"candidate rank grid contains duplicates: {list(grid)}"
        )
    return tuple(sorted(int(k) for k in grid))


def validate_mapping_keys(mapping, required, what):
    """Shared helper: refuse a provenance mapping missing required keys."""
    missing = [k for k in required if k not in mapping]
    if missing:
        raise ContractViolation(f"{what} is missing keys {missing}")
    return True
