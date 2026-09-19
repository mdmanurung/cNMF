"""P0-07 — content-keyed run cache with atomic success sentinels (cache/restart).

A cached run directory is valid only while its inputs, options and code are
unchanged. The cache key folds in:

- the run configuration content (not its path or mtime),
- the frozen protocol hash and ablation-plan contract hash,
- the implementation revision (`implementation_sha`) and upstream SHA,
- the evidence tier / scenario / seeds that enter `experiment_id`.

A run writes `SUCCESS.json` atomically (tmp file + `os.replace`) only after its
outputs validate. Any directory without a matching sentinel is treated as
interrupted or stale and must be recomputed, never silently reused. This is
what the P0 gate's cache/restart checks read, and what un-fenced
`skeleton.run` (P0-07, D027).
"""

import json
import os

from .hashing import parameter_hash

__all__ = [
    "SUCCESS_FILENAME",
    "cache_key",
    "write_atomic_json",
    "mark_success",
    "read_sentinel",
    "is_valid",
    "needs_recompute",
]

SUCCESS_FILENAME = "SUCCESS.json"


def cache_key(payload):
    """Deterministic content key for a run. Same inputs/options/code ⇒ same key."""
    return parameter_hash(payload)


def write_atomic_json(path, obj):
    """Write JSON atomically: tmp file in the same directory + `os.replace`.

    A reader never observes a half-written file, so an interrupted write cannot
    masquerade as a completed one.
    """
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def mark_success(run_dir, key, extra=None):
    """Record a completed, validated run. Atomic — the only success signal."""
    payload = {"cache_key": key}
    if extra:
        payload.update(extra)
    write_atomic_json(os.path.join(run_dir, SUCCESS_FILENAME), payload)
    return payload


def read_sentinel(run_dir):
    """Return the sentinel payload, or `None` when absent or unreadable.

    Absent/unreadable means interrupted or never completed — never valid.
    """
    path = os.path.join(run_dir, SUCCESS_FILENAME)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def is_valid(run_dir, key):
    """True only when a readable sentinel carries exactly this run's key."""
    sentinel = read_sentinel(run_dir)
    return bool(sentinel) and sentinel.get("cache_key") == key


def needs_recompute(run_dir, key):
    """The restart rule: recompute unless a matching sentinel exists.

    Covers the four mandatory invalidation axes — changed inputs, changed
    options, changed code, interrupted outputs — because all four either alter
    the key or leave no sentinel behind.
    """
    return not is_valid(run_dir, key)
