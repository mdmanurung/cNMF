"""P0-02 schema checks: unit tagging refuses cross-unit use, manifests carry
their §6.6 provenance, rank grids are validated before any fit reads them.

Like test_contract.py, every refusal here gets a case that triggers it — a
check never shown to fire is not evidence.
"""
import json
import os

import numpy as np
import pytest

from cnmfbench.contract import ContractViolation
from cnmfbench.schemas import (
    DATASET_MANIFEST_KEYS,
    ExpressionMatrix,
    UnitMismatch,
    validate_dataset_manifest,
    validate_rank_grid,
)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _manifest():
    return {
        "scenario_id": "base_identifiable",
        "tier": "SMOKE",
        "parameters": {"n_donors": 8},
        "seed": 1701,
        "simulation_replicate": 0,
        "protocol_version": "1.0.1",
        "dataset_manifest_hash": "0" * 64,
    }


def test_valid_matrix_unwraps_in_its_own_units():
    m = np.ones((3, 4))
    tagged = ExpressionMatrix(m, "training_scale")
    assert tagged.require_units("training_scale") is m


def test_cross_unit_use_raises_unit_mismatch():
    tagged = ExpressionMatrix(np.ones((3, 4)), "raw_counts")
    with pytest.raises(UnitMismatch, match="training_scale"):
        tagged.require_units("training_scale")


def test_unknown_unit_string_is_refused_at_construction():
    with pytest.raises(ContractViolation, match="§6.2"):
        ExpressionMatrix(np.ones((2, 2)), "log_norm")


def test_all_three_protocol_units_construct():
    for units in ("raw_counts", "training_scale", "tpm"):
        assert ExpressionMatrix(np.ones((2, 2)), units).units == units


def test_valid_manifest_returns_its_hash():
    assert validate_dataset_manifest(_manifest()) == "0" * 64


def test_manifest_missing_a_key_is_refused():
    bad = _manifest()
    del bad["seed"]
    with pytest.raises(ContractViolation, match="missing keys"):
        validate_dataset_manifest(bad)


def test_manifest_with_a_truncated_hash_is_refused():
    bad = _manifest()
    bad["dataset_manifest_hash"] = "0" * 12
    with pytest.raises(ContractViolation, match="full-length"):
        validate_dataset_manifest(bad)


def test_manifest_with_a_non_hex_hash_is_refused():
    bad = _manifest()
    bad["dataset_manifest_hash"] = "z" * 64
    with pytest.raises(ContractViolation, match="hexadecimal"):
        validate_dataset_manifest(bad)


def test_real_simulator_manifest_satisfies_the_schema():
    from cnmfbench.scenarios import build_params, seed_for
    from cnmfbench.simulate import simulate

    ds = simulate(build_params("base_identifiable", "SMOKE"), "base_identifiable",
                  "SMOKE", seed_for("SMOKE"))
    assert validate_dataset_manifest(ds.manifest) == ds.dataset_manifest_hash


def test_committed_manifest_example_satisfies_the_schema():
    path = os.path.join(REPO, "docs/benchmarks/registry/dataset_manifest_example.json")
    with open(path, encoding="utf-8") as fh:
        example = json.load(fh)
    assert set(DATASET_MANIFEST_KEYS) <= set(example)
    validate_dataset_manifest(example)


def test_valid_grid_returns_sorted_tuple():
    assert validate_rank_grid([4, 2, 3]) == (2, 3, 4)


def test_empty_grid_is_refused():
    with pytest.raises(ContractViolation, match="empty"):
        validate_rank_grid([])


def test_non_positive_rank_is_refused():
    with pytest.raises(ContractViolation, match="positive integers"):
        validate_rank_grid([2, 0, 3])


def test_duplicated_rank_is_refused():
    with pytest.raises(ContractViolation, match="duplicates"):
        validate_rank_grid([2, 3, 3])
