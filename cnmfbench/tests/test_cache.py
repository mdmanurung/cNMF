"""P0-07 cache/restart tests: invalidation on changed inputs, options, code
and interrupted outputs; atomic sentinel behaviour; the restart rule.
"""
import json
import os

from cnmfbench import cache


def test_cache_key_is_deterministic_and_sensitive(tmp_path):
    payload = {"config": {"seed": 1}, "code": "abc", "tier": "SMOKE"}
    assert cache.cache_key(payload) == cache.cache_key(dict(payload))
    changed_input = {"config": {"seed": 2}, "code": "abc", "tier": "SMOKE"}
    changed_option = {"config": {"seed": 1}, "code": "abc", "tier": "DEVELOPMENT"}
    changed_code = {"config": {"seed": 1}, "code": "abd", "tier": "SMOKE"}
    assert cache.cache_key(changed_input) != cache.cache_key(payload)
    assert cache.cache_key(changed_option) != cache.cache_key(payload)
    assert cache.cache_key(changed_code) != cache.cache_key(payload)


def test_missing_sentinel_is_interrupted_and_needs_recompute(tmp_path):
    run_dir = str(tmp_path / "run")
    os.makedirs(run_dir)
    key = cache.cache_key({"a": 1})
    assert cache.read_sentinel(run_dir) is None
    assert not cache.is_valid(run_dir, key)
    assert cache.needs_recompute(run_dir, key)


def test_mark_success_then_valid_no_recompute(tmp_path):
    run_dir = str(tmp_path / "run")
    os.makedirs(run_dir)
    key = cache.cache_key({"a": 1})
    cache.mark_success(run_dir, key)
    assert cache.is_valid(run_dir, key)
    assert not cache.needs_recompute(run_dir, key)


def test_changed_key_invalidates_existing_sentinel(tmp_path):
    run_dir = str(tmp_path / "run")
    os.makedirs(run_dir)
    cache.mark_success(run_dir, cache.cache_key({"seed": 1}))
    new_key = cache.cache_key({"seed": 2})
    assert not cache.is_valid(run_dir, new_key)
    assert cache.needs_recompute(run_dir, new_key)


def test_corrupt_sentinel_is_treated_as_interrupted(tmp_path):
    run_dir = str(tmp_path / "run")
    os.makedirs(run_dir)
    with open(os.path.join(run_dir, cache.SUCCESS_FILENAME), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert cache.read_sentinel(run_dir) is None
    assert cache.needs_recompute(run_dir, cache.cache_key({"a": 1}))


def test_sentinel_write_is_atomic_and_complete(tmp_path):
    run_dir = str(tmp_path / "run")
    os.makedirs(run_dir)
    key = cache.cache_key({"a": 1})
    cache.mark_success(run_dir, key, extra={"note": "done"})
    leftovers = [p for p in os.listdir(run_dir) if ".tmp-" in p]
    assert leftovers == []
    with open(os.path.join(run_dir, cache.SUCCESS_FILENAME), encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["cache_key"] == key
    assert payload["note"] == "done"
