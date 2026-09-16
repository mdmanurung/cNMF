"""The registry's job is to make two kinds of mistake impossible: running a scenario that
was never specified, and reading the sealed tier by accident."""
import dataclasses

import pytest

from cnmfbench.scenarios import (
    SCENARIOS,
    TIERS,
    SealedTierError,
    build_params,
    get_scenario,
    list_implemented,
    seed_for,
)
from cnmfbench.simulate import SimulationParams


def test_all_eight_scenarios_are_specified():
    # Specified before features B and C exist, so no scenario can be shaped around the
    # behaviour of the feature it tests.
    assert len(SCENARIOS) == 8


def test_exactly_the_three_planned_scenarios_are_implemented():
    assert set(list_implemented()) == {"base_identifiable", "A_weak", "A_null"}


def test_every_scenario_states_which_feature_it_tests():
    for name, s in SCENARIOS.items():
        assert s["feature"] in {"reference", "A", "B", "C"}, name
        assert s["rationale"].strip(), name


def test_unimplemented_scenario_raises_rather_than_falling_back():
    # A silent fallback would produce a RESULTS.tsv row labelled B_context that was
    # generated under base_identifiable, and nothing downstream could detect it.
    with pytest.raises(NotImplementedError):
        get_scenario("B_context")


def test_unknown_scenario_raises():
    with pytest.raises(KeyError):
        get_scenario("A_strong_probably")


def test_unknown_tier_raises():
    with pytest.raises(KeyError):
        build_params("base_identifiable", "PRODUCTION")


@pytest.mark.parametrize("name", ["base_identifiable", "A_weak", "A_null"])
@pytest.mark.parametrize("tier", ["SMOKE", "DEVELOPMENT"])
def test_implemented_scenarios_build_valid_params(name, tier):
    p = build_params(name, tier)
    assert isinstance(p, SimulationParams)
    assert p.k_true >= 1


def test_params_are_frozen():
    p = build_params("base_identifiable", "SMOKE")
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.lambda_separation = 99.0


def test_a_null_has_no_activity_program():
    assert build_params("A_null", "DEVELOPMENT").n_activity == 0


def test_a_weak_is_weaker_than_the_reference():
    base = build_params("base_identifiable", "DEVELOPMENT")
    weak = build_params("A_weak", "DEVELOPMENT")
    assert weak.lambda_separation < base.lambda_separation
    assert weak.p_active < base.p_active


def test_sealed_tier_requires_an_explicit_unseal():
    # PROTOCOL §6.4. Peeking must be a deliberate, greppable act.
    with pytest.raises(SealedTierError):
        seed_for("SEALED_CONFIRMATION")
    assert isinstance(seed_for("SEALED_CONFIRMATION", unseal=True), int)


def test_open_tiers_do_not_need_unsealing():
    assert seed_for("SMOKE") and seed_for("DEVELOPMENT")


def test_sealed_seed_differs_from_the_development_seed():
    assert seed_for("SEALED_CONFIRMATION", unseal=True) != seed_for("DEVELOPMENT")


def test_build_params_rejects_unknown_overrides():
    with pytest.raises(TypeError):
        build_params("base_identifiable", "SMOKE", lambda_seperation=3.0)


def test_gradient_overrides_change_the_parameters():
    # The depth and noise gradients sweep these without touching the inference engine.
    swept = build_params("base_identifiable", "SMOKE", mean_library=500.0)
    assert swept.mean_library == 500.0


def test_all_tiers_are_named():
    assert set(TIERS) == {"SMOKE", "DEVELOPMENT", "SEALED_CONFIRMATION"}
