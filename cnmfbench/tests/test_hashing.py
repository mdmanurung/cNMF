"""PROTOCOL §7 hash convention.

These tests pin the *convention*, not the implementation. If one fails after a refactor,
the correct response is almost never to update the expected value: §7 says any change to
these rules increments `hash_convention_version` and invalidates comparison of hashes
across the boundary.
"""
import pytest

from cnmfbench.hashing import artifact_hash, canonical_json, cell_set_hash, parameter_hash


def test_canonical_json_sorts_keys_and_strips_whitespace():
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_parameter_hash_is_insensitive_to_key_order():
    assert parameter_hash({"a": 1, "b": [2, 3]}) == parameter_hash({"b": [2, 3], "a": 1})


def test_parameter_hash_distinguishes_int_and_float():
    # 1 and 1.0 are different generative parameters; a hash that collides them would let
    # two materially different datasets share a dataset_manifest_hash (§6.6).
    assert parameter_hash({"x": 1}) != parameter_hash({"x": 1.0})


def test_canonical_json_preserves_non_ascii():
    assert canonical_json({"k": "é"}) == '{"k":"é"}'


def test_canonical_json_rejects_nan():
    # NaN is not valid JSON. Accepting it would produce a hash that no other
    # implementation could reproduce, which defeats the purpose of §7.
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})


def test_cell_set_hash_is_order_independent():
    assert cell_set_hash(["c1", "c0", "c2"]) == cell_set_hash(["c0", "c1", "c2"])


def test_cell_set_hash_rejects_duplicates():
    # A split containing the same cell twice is a splitter bug; a hash that silently
    # collapsed it would make that bug invisible in every downstream comparison.
    with pytest.raises(ValueError):
        cell_set_hash(["c0", "c0"])


def test_cell_set_hash_includes_trailing_newline():
    import hashlib

    expected = hashlib.sha256("a\nb\n".encode("utf-8")).hexdigest()
    assert cell_set_hash(["b", "a"]) == expected


def test_artifact_hash_is_over_file_bytes(tmp_path):
    import hashlib

    p = tmp_path / "f.bin"
    payload = b"\x00\x01binary payload\n"
    p.write_bytes(payload)
    assert artifact_hash(p) == hashlib.sha256(payload).hexdigest()


def test_hashes_are_full_length_lowercase_hex():
    h = parameter_hash({"a": 1})
    assert len(h) == 64 and h == h.lower()
