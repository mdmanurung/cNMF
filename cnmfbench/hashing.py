"""PROTOCOL §7 hash convention, one function per kind of thing.

The point of §7 is that a hash is reproducible *without reading the code that produced
it*. So each function here implements one table row literally, and the docstring states
the rule in the protocol's own terms. Changing any rule here increments
`hash_convention_version` and invalidates comparison across the boundary — it is not a
refactor.
"""
import hashlib
import json

from . import HASH_CONVENTION_VERSION

__all__ = [
    "canonical_json",
    "parameter_hash",
    "artifact_hash",
    "cell_set_hash",
    "HASH_CONVENTION_VERSION",
]


def canonical_json(obj):
    """Canonical JSON per §7: sorted keys, no insignificant whitespace, UTF-8, non-ASCII
    preserved, floats in `repr` form.

    Python 3's json encoder already uses `float.__repr__` for floats, which is the
    shortest string that round-trips — that is what "repr form" means here. It is
    asserted rather than assumed, because a future encoder change would silently alter
    every parameter hash in the programme.
    """
    text = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return text


def parameter_hash(obj):
    """§7 'parameter-like': sha256 over canonical JSON.

    Used for `protocol_hash`, `contract_hash`, `preprocessing_hash`,
    `dataset_manifest_hash` and `environment_hash`. Returns full-length lowercase hex;
    §7 forbids truncation in recorded output.
    """
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def artifact_hash(path):
    """§7 'artifact': sha256 over the file bytes, unmodified.

    Used for `factor_bank_hash`, file-level integrity, and `protocol.sha256` itself.
    Read in chunks so a multi-GB counts file does not have to fit in memory.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cell_set_hash(cell_ids):
    """§7 'cell set': sha256 over the newline-joined, lexicographically sorted cell ids,
    UTF-8, **trailing newline included**.

    Used for `discovery_cells_hash`. Sorting makes the hash independent of the order the
    splitter happened to emit, which is the property that lets two runs be compared at
    all. Duplicates are an error rather than being silently collapsed: a split that
    contains the same cell twice is a bug in the splitter, and a hash that hides it
    would make that bug invisible in every downstream comparison.
    """
    ids = list(cell_ids)
    if any(not isinstance(c, str) for c in ids):
        raise TypeError("cell ids must be strings (PROTOCOL §6.1)")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate cell ids in cell set")
    payload = "\n".join(sorted(ids)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
