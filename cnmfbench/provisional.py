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
        ProvisionalComponent(
            component_id="splits.outer_donor_folds",
            owner_task="P0-06",
            reason="Reassigned from P0-05 at D021. The nesting this entry originally "
            "required now exists (`inner_donor_folds`), is property-tested, and is "
            "exercised against real cNMF fits in `test_inner_folds.py`. But no production "
            "run calls it: `check_preconditions` refuses feature A while `delta` is null "
            "(§2), so the inner loop's only caller today is the test suite. Un-fencing it "
            "here would repeat D017 — a component declared hardened while the path that "
            "would exercise it in production does not run.",
            hardening_requires="`delta` set (P0-06) and feature A runnable, so the inner "
            "loop is exercised by a real run rather than by tests alone.",
        ),
        ProvisionalComponent(
            component_id="skeleton.run",
            owner_task="P0-07",
            reason="Linear in-process driver. No cache, no restart, no CI, no SLURM.",
            hardening_requires="The P0-07 workflow with restart and cache-invalidation tests.",
        ),
        ProvisionalComponent(
            component_id="features.consensus_c",
            owner_task="P3-01",
            reason="Feature C reimplements upstream's consensus aggregation harness-side, "
            "because `cnmf.py` may not be edited. Its OFF path is pinned against "
            "`cnmf.consensus` by test, but only at the tiers run so far — and the "
            "tie-breaking rule for which contribution survives (nearest the cluster "
            "centroid) is a choice this implementation made, not a reading of the "
            "ablation plan. See D015.",
            hardening_requires="The OFF-path equivalence asserted at every tier a result "
            "is claimed at, and the tie-break rule either fixed in the ablation plan or "
            "shown not to change the C effect.",
        ),
        ProvisionalComponent(
            component_id="features.discovery_sample_b",
            owner_task="P2-01",
            reason="Feature B's matched-budget draw. The redistribution rule for donors "
            "holding fewer cells than their equal share is this implementation's choice. "
            "`hold_preprocessing_constant_across_B` holds for G — frozen into both arms via "
            "`prepare(genes_file=...)`, verified byte-identical — and CANNOT hold for s_g, "
            "which `cnmf.prepare` computes from whichever cells the rule drew; measured "
            "drift median 1.04, max 1.24. See D016.",
            hardening_requires="Sampling replicates, so the draw's variance is reported "
            "rather than assumed negligible — currently one draw per arm, which is why B is "
            "INCONCLUSIVE and not 'no effect'. NOT an audit asserting s_g identical across "
            "arms: D016 shows that cannot be met while `src/cnmf/**` is unmodifiable. The "
            "drift is reported instead, and cross-arm endpoints are read in count units.",
        ),
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
