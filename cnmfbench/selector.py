"""PROTOCOL §1 / §2 — the preregistered training-only baseline rank selector (P0-06).

Frozen elsewhere, implemented here. `PROTOCOL.md` §1 defines the primary rule
(`largest-among-stable`) and its sensitivity heuristic; §1.4 freezes four edge-case
behaviours; §2 freezes `delta`'s calibration procedure and, load-bearing for this module,
the *order* in which the null-`delta` refusal and the §1.4 edge cases are checked.

This implements `preregistered_training_only_baseline_surrogate` — the rule the A-OFF
baseline uses to be a fair opponent for feature A, not an official upstream cNMF
algorithm (§1, opening paragraph; `Stepwise_Guide.md:85`). A value returned here must
never be described as "cNMF selects rank by...".

`delta` is a frozen protocol constant, calibrated once at P1-01 per §2's procedure and
recorded in `DECISIONS.md`. This module does not calibrate it and does not read it from
any config file — the caller passes the value (or `None`, before it exists).
"""
import math
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from .contract import ContractViolation

__all__ = ["SelectionResult", "select_rank", "select_rank_predictive"]


@dataclass(frozen=True)
class SelectionResult:
    """One selector outcome.

    `selected_rank` is `None` only when every candidate K failed or was NaN (§1.4's
    fourth row, "failed or NaN K") — never as a stand-in for the null-`delta` refusal,
    which raises instead of returning a result.

    `sensitivity_rank` is `PROTOCOL.md` §1.3's heuristic, reported beside `selected_rank`
    in every row where a rank is selected. It is computed independently of `delta` and of
    the degenerate/boundary branches below, so a divergence from `selected_rank` is a
    reportable finding, never a bug to reconcile by adjusting either value.
    """

    selected_rank: Optional[int]
    sensitivity_rank: Optional[int]
    selector_degenerate: bool
    selector_boundary: bool
    n_failed_units: int
    eligible_grid: Tuple[int, ...]


def select_rank(silhouette_by_k: Mapping[int, float], delta: Optional[float]) -> SelectionResult:
    """PROTOCOL §2's five-step order, exactly (`PROTOCOL.md:143-147`). Do not reorder —
    §1.4's degenerate branch says "do not apply delta", and without evaluating the
    null-`delta` refusal first, a flat curve becomes a route to a selected rank while
    `delta` is still null. That is precisely the outcome the refusal exists to prevent.

        1. if delta is null            -> refuse (raise); no rank is returned
        2. drop failed/NaN K from grid -> if the grid is empty, fail the row (§1.4)
        3. if the curve is degenerate  -> select smallest K, selector_degenerate = True
        4. otherwise                   -> apply the §1.2 rule (largest-among-stable)
        5. set selector_boundary if K* is a grid endpoint

    `silhouette_by_k`: mapping {candidate_rank: silhouette}. A rank whose fit did not
    complete, or whose silhouette is `NaN`, belongs in this mapping (as `NaN`, or simply
    absent — both are treated identically) rather than being pre-filtered by the caller,
    so `n_failed_units` counts it per §1.4's fourth row ("never silently replace it with a
    neighbouring K").
    `delta`: the frozen protocol constant, or `None` while it is uncalibrated.

    Raises `ContractViolation` if `delta` is `None`. Never returns a rank in that case.
    """
    # ---- Step 1: refuse first, before anything about the grid is examined. ----
    if delta is None:
        raise ContractViolation(
            "PROTOCOL §2: delta is null. The selector refuses to run rather than "
            "falling back to a default — a value chosen at the point of use would be a "
            "value chosen after seeing the data. Calibrate delta per §2's procedure "
            "(development-tier controls, dispersion across optimizer seeds) before "
            "calling select_rank(). This check runs before the §1.4 edge cases, "
            "including the degenerate-curve branch, so a flat curve cannot be used to "
            "obtain a rank while delta is still null."
        )

    # ---- Step 2: drop failed/NaN K from the eligible grid. ----
    eligible = {
        int(k): float(v) for k, v in silhouette_by_k.items()
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    }
    n_failed = len(silhouette_by_k) - len(eligible)
    grid = tuple(sorted(eligible))

    if not grid:
        # Every K in the grid failed: no rank is selected. `status` (set by the caller)
        # distinguishes this from the fixed-rank convention (§5.3) by carrying a failure
        # value rather than "ok"/"ok_provisional".
        return SelectionResult(
            selected_rank=None, sensitivity_rank=None,
            selector_degenerate=False, selector_boundary=False,
            n_failed_units=n_failed, eligible_grid=(),
        )

    best = max(eligible.values())

    # §1.3 sensitivity heuristic, computed unconditionally: K*_sens = min argmax silhouette.
    # Ties resolve to the smaller K. Reported alongside K*, never substituted for it, and
    # computed the same way regardless of which branch below determines K*.
    sensitivity_rank = min(k for k in grid if eligible[k] == best)

    worst = min(eligible.values())

    # ---- Step 3: degenerate (flat) curve. delta is NOT applied here. ----
    if best - worst < 1e-6:
        k_star = grid[0]  # smallest K, per §1.4
        return SelectionResult(
            selected_rank=k_star, sensitivity_rank=sensitivity_rank,
            selector_degenerate=True,
            selector_boundary=(k_star == grid[0] or k_star == grid[-1]),
            n_failed_units=n_failed, eligible_grid=grid,
        )

    # ---- Step 4: §1.2 primary rule — largest-among-stable, not argmax. ----
    # Why largest, not argmax: on the common curve shape where silhouette sits near its
    # maximum and decays slowly, plain argmax returns the smallest grid value almost
    # every time, and a baseline that always selects K=2 would be beaten trivially by
    # feature A (`PROTOCOL.md:68-83`).
    stable = [k for k in grid if eligible[k] >= best - delta]
    k_star = max(stable)

    # ---- Step 5: boundary flag. Never auto-expand the grid. ----
    boundary = k_star == grid[0] or k_star == grid[-1]

    return SelectionResult(
        selected_rank=k_star, sensitivity_rank=sensitivity_rank,
        selector_degenerate=False, selector_boundary=boundary,
        n_failed_units=n_failed, eligible_grid=grid,
    )


def select_rank_predictive(mean_inner_error_by_k):
    """Feature A's selector (P1-02): minimum donor-averaged inner-validation loss.

    `mean_inner_error_by_k`: mapping {candidate_rank: mean over inner folds of
    the fold's equal-donor-mean held-out error}. Lower wins; exact ties go to
    the smaller K deterministically (IMPLEMENTATION_PROMPT.md P1: "deterministic
    preference for smaller K among exact/numerically defined ties"). No `delta`,
    no silhouette — this rule reads only inner-validation results, and the
    candidate fits, preprocessing, masks and aggregation are the caller's
    unchanged business.

    Returns `(k_star, boundary)` where `boundary` flags a grid endpoint (never
    auto-expands). Raises `ContractViolation` on an empty grid rather than
    returning a rank for a selection that never ran.
    """
    grid = tuple(sorted(mean_inner_error_by_k))
    if not grid:
        raise ContractViolation(
            "feature A's selector received no inner-validation scores: every "
            "inner fold failed or the grid is empty. Returning a rank here would "
            "be selecting on nothing."
        )
    best = min(mean_inner_error_by_k[k] for k in grid)
    candidates = [k for k in grid if mean_inner_error_by_k[k] == best]
    k_star = min(candidates)
    return int(k_star), bool(k_star == grid[0] or k_star == grid[-1])
