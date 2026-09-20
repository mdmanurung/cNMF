"""The fence: which harness components are throwaway, in code rather than in prose.

D006 chose to build the splitter and scorer thin and harden them at P0-02/P0-04/P0-05,
and recorded the standing risk in its own trade-offs section: *"the thin split/scorer/
runner written in the skeleton session is throwaway-grade by construction, and the
standing risk is that it becomes load-bearing and is never hardened."*

Prose has not prevented that before — three items specified in the P0-03 plan were
approved and then silently dropped, and nothing caught it because nothing cross-checked
plan text against state. So the fence lives here, where a gate check can read it.

Three layers:

1. **Registry + decorator.** `@provisional` marks a function and, *when called*, records
   that it ran. Runtime tracking rather than static marking: a component that is
   registered but never invoked is not in the path of the rows being written.
2. **Propagation.** Every row emitted by a run whose touched-set is non-empty carries
   `status = ok_provisional` and names the components in `notes`. The evidence says of
   itself that throwaway code produced it.
3. **Two gate checks**, deliberately separate:
   - `registry_is_empty()` — code-level. False while any `@provisional` decorator
     remains. This is the one that blocks the P0 gate.
   - `cited_rows_are_not_provisional()` — data-level, scoped to the experiment ids a
     gate actually cites. Never a whole-file scan: historical provisional rows stay in
     `RESULTS.tsv` forever, correctly, because throwaway code really did produce them,
     and a whole-file scan would jam the gate permanently.
"""
import functools
from dataclasses import dataclass

__all__ = [
    "ProvisionalComponent",
    "PROVISIONAL",
    "provisional",
    "touched",
    "reset_touched",
    "registry_is_empty",
    "cited_rows_are_not_provisional",
]


@dataclass(frozen=True)
class ProvisionalComponent:
    component_id: str
    owner_task: str  # the ledger task that must harden it
    reason: str
    hardening_requires: str


PROVISIONAL = {
    c.component_id: c
    for c in [
    ]
}

_touched = set()


def provisional(component_id):
    """Mark a function as throwaway-grade and record that it ran.

    Registration is checked at decoration time, so a typo or a registry entry deleted
    without its decorator fails at import rather than silently un-fencing a component.
    """
    if component_id not in PROVISIONAL:
        raise KeyError(
            f"{component_id!r} is decorated @provisional but absent from PROVISIONAL. "
            "Add the entry — the registry is what the gate reads."
        )

    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _touched.add(component_id)
            return fn(*args, **kwargs)

        wrapper.__cnmfbench_provisional__ = component_id
        return wrapper

    return decorate


def touched():
    """Component ids that actually ran in this process, sorted."""
    return tuple(sorted(_touched))


def reset_touched():
    _touched.clear()


def registry_is_empty():
    """**The P0 gate check.** False while any component is still throwaway.

    Closing it means deleting decorators and registry entries together, in a commit with
    a decision entry — not forgetting to look.
    """
    return not PROVISIONAL


def cited_rows_are_not_provisional(rows, experiment_ids):
    """Data-level check, scoped to the experiment ids a gate actually cites.

    Deliberately not a whole-file scan. Provisional rows stay in `RESULTS.tsv`
    permanently and correctly — throwaway code produced them — so a scan over the whole
    file would block the gate forever no matter how much hardening happened afterwards.
    """
    cited = set(experiment_ids)
    return not any(
        r.get("experiment_id") in cited and str(r.get("status", "")).endswith("_provisional")
        for r in rows
    )
