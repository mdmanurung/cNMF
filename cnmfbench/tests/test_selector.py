"""PROTOCOL §1 / §2 — the baseline rank selector, one test per frozen branch.

The load-bearing test in this file is `test_flat_curve_still_refuses_while_delta_is_null`:
§1.4's degenerate-curve branch says "select the smallest K, do not apply delta", and
without §2's normative check-ordering (null-delta refusal evaluated first, before any
§1.4 edge case), a flat curve would be a route to a selected rank while delta is still
null — exactly what the refusal exists to prevent.
"""
import math

import pytest

from cnmfbench.contract import ContractViolation
from cnmfbench.selector import select_rank


def test_null_delta_refuses_even_on_an_ordinary_curve():
    with pytest.raises(ContractViolation, match="delta is null"):
        select_rank({2: 0.5, 3: 0.9, 4: 0.7}, delta=None)


def test_flat_curve_still_refuses_while_delta_is_null():
    """The ordering test. A flat curve (§1.4's degenerate branch) must NOT bypass the
    null-delta refusal — refusal is step 1, evaluated before the grid is even examined."""
    flat = {2: 0.90000001, 3: 0.9, 4: 0.90000002}
    with pytest.raises(ContractViolation, match="delta is null"):
        select_rank(flat, delta=None)


def test_degenerate_curve_selects_smallest_k_and_does_not_apply_delta():
    flat = {2: 0.90000001, 3: 0.9, 4: 0.90000002}
    result = select_rank(flat, delta=1e-9)  # a delta too small to matter if it were applied
    assert result.selected_rank == 2
    assert result.selector_degenerate is True
    assert result.selector_boundary is True  # smallest K is a grid endpoint


def test_primary_rule_is_largest_among_stable_not_argmax():
    """§1.2's rationale: on a curve near its maximum that decays slowly, argmax alone
    would return the smallest grid value; largest-among-stable returns a larger one."""
    curve = {2: 1.0, 3: 0.999, 4: 0.998, 5: 0.997, 6: 0.5}
    result = select_rank(curve, delta=0.01)
    assert result.selected_rank == 5  # largest K within 0.01 of the max (1.0): 6 is not
    assert result.sensitivity_rank == 2  # argmax, ties -> smaller K
    assert result.selector_degenerate is False


def test_ties_take_the_largest_k_for_the_primary_rule():
    """§1.4's "ties" row: several K satisfy the rule with equal silhouette; the rule
    already takes the largest. Kept non-degenerate (range >= 1e-6) so this exercises the
    §1.2 tie-break rather than the degenerate branch."""
    curve = {2: 0.9, 3: 0.9, 4: 0.5, 5: 0.9}
    result = select_rank(curve, delta=0.0)
    assert result.selected_rank == 5


def test_sensitivity_heuristic_ties_resolve_to_the_smaller_k():
    curve = {2: 0.9, 3: 0.9, 4: 0.5}
    result = select_rank(curve, delta=0.0)
    assert result.sensitivity_rank == 2


def test_search_boundary_flag_set_when_k_star_is_a_grid_endpoint():
    curve = {2: 0.5, 3: 0.6, 4: 1.0}
    result = select_rank(curve, delta=0.0)
    assert result.selected_rank == 4
    assert result.selector_boundary is True


def test_search_boundary_flag_not_set_for_an_interior_k_star():
    curve = {2: 0.6, 3: 1.0, 4: 0.5}
    result = select_rank(curve, delta=0.0)
    assert result.selected_rank == 3
    assert result.selector_boundary is False


def test_failed_or_nan_k_is_dropped_and_counted_never_substituted():
    curve = {2: 0.9, 3: float("nan"), 4: 0.85}
    result = select_rank(curve, delta=0.1)
    assert result.eligible_grid == (2, 4)
    assert result.n_failed_units == 1
    assert result.selected_rank == 4  # within delta of the max among the eligible grid


def test_none_value_is_also_treated_as_failed():
    curve = {2: 0.9, 3: None, 4: 0.85}
    result = select_rank(curve, delta=0.1)
    assert result.eligible_grid == (2, 4)
    assert result.n_failed_units == 1


def test_all_k_failed_returns_no_rank_rather_than_refusing():
    curve = {2: float("nan"), 3: None}
    result = select_rank(curve, delta=0.1)
    assert result.selected_rank is None
    assert result.sensitivity_rank is None
    assert result.eligible_grid == ()
    assert result.n_failed_units == 2


def test_never_auto_expands_the_grid():
    """Selecting a boundary K never widens the eligible set beyond what was passed in."""
    curve = {2: 0.5, 3: 0.6, 4: 1.0}
    result = select_rank(curve, delta=100.0)  # huge delta -> every K is "stable"
    assert result.selected_rank == 4  # still the largest of the GIVEN grid, not beyond it
    assert result.eligible_grid == (2, 3, 4)
