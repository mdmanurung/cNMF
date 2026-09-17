"""The feasibility gate and the sealed-tier refusal.

`feasibility_verdict` decides whether the benchmark can resolve rank at all. Its
thresholds are pre-registered in
`docs/benchmarks/registry/p0-03_development_feasibility_PREREGISTRATION.md`, committed
before the run they govern, so these tests pin the behaviour rather than the numbers.
"""
import pytest

from cnmfbench.analysis import feasibility_verdict


def _rows(per_donor_by_k, fold="outer_0"):
    """Build RESULTS-shaped rows: per-donor values plus their equal_donor_mean."""
    out = []
    for k, per_donor in per_donor_by_k.items():
        for donor, value in per_donor.items():
            out.append(dict(
                metric="heldout_squared_prediction_error_v1", evaluation_scope="per_donor",
                candidate_rank=str(k), independent_unit_id=donor, value=repr(value),
                outer_split_id=fold, experiment_id=f"e-{fold}-k{k}",
            ))
        out.append(dict(
            metric="heldout_squared_prediction_error_v1", evaluation_scope="equal_donor_mean",
            candidate_rank=str(k), independent_unit_id="ALL_TEST_DONORS",
            value=repr(sum(per_donor.values()) / len(per_donor)),
            outer_split_id=fold, experiment_id=f"e-{fold}-k{k}",
        ))
    return out


def _diag(floor, sil_range, fold="outer_0"):
    return [{"outer_split_id": fold, "poisson_error_floor_per_cell": floor,
             "silhouette_dynamic_range": sil_range}]


def test_go_when_all_three_criteria_pass():
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 10.0 + 0.1 * i for i, d in enumerate(donors)},
                  10: {d: 14.0 + 0.13 * i for i, d in enumerate(donors)}})
    v = feasibility_verdict(rows, _diag(floor=9.0, sil_range=0.1), k_true=7, k_max=10)
    assert v["verdict"] == "GO"
    assert v["criterion_1_curve_structure"]
    assert v["n_paired_donors"] == 12


def test_a_zero_variance_difference_passes_rather_than_failing():
    """Every donor moving by the same amount is the strongest possible evidence of curve
    structure. An earlier implementation treated se == 0 as a failure, inverting the
    criterion exactly where it is most decisive."""
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 10.0 for d in donors}, 10: {d: 14.0 for d in donors}})
    v = feasibility_verdict(rows, _diag(floor=9.0, sil_range=0.1), k_true=7, k_max=10)
    assert v["paired_se"] == 0.0
    assert v["criterion_1_curve_structure"]
    assert v["verdict"] == "GO"


def test_a_zero_variance_difference_in_the_wrong_direction_still_fails():
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 14.0 for d in donors}, 10: {d: 10.0 for d in donors}})
    v = feasibility_verdict(rows, _diag(floor=9.0, sil_range=0.1), k_true=7, k_max=10)
    assert not v["criterion_1_curve_structure"]


def test_no_go_when_the_curve_has_no_structure():
    """K_max barely differs from K_true relative to the donor-to-donor spread."""
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 10.0 + i for i, d in enumerate(donors)},
                  10: {d: 10.0 + i + (0.1 if i % 2 else -0.1) for i, d in enumerate(donors)}})
    v = feasibility_verdict(rows, _diag(floor=9.0, sil_range=0.1), k_true=7, k_max=10)
    assert not v["criterion_1_curve_structure"]
    assert v["verdict"] == "NO-GO"


def test_no_go_when_both_ends_sit_on_the_poisson_floor():
    """Flat by arithmetic: no selector can work, whatever its rule. Fails only when BOTH
    ends are within 2% of the floor — one end near it is normal."""
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 10.0 for d in donors}, 10: {d: 10.1 for d in donors}})
    v = feasibility_verdict(rows, _diag(floor=10.0, sil_range=0.1), k_true=7, k_max=10)
    assert not v["criterion_2_not_flat_by_arithmetic"]
    assert v["verdict"] == "NO-GO"


def test_one_end_near_the_floor_is_not_a_failure():
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 10.0 + 0.05 * i for i, d in enumerate(donors)},
                  10: {d: 13.0 + 0.05 * i for i, d in enumerate(donors)}})
    v = feasibility_verdict(rows, _diag(floor=9.95, sil_range=0.1), k_true=7, k_max=10)
    assert v["criterion_2_not_flat_by_arithmetic"]


def test_no_go_when_the_silhouette_curve_is_degenerate():
    """Below PROTOCOL §1.4's 1e-6 the degenerate branch fires and the baseline always
    picks the smallest K, making 000 vs 100 meaningless."""
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 10.0 + 0.1 * i for i, d in enumerate(donors)},
                  10: {d: 14.0 + 0.1 * i for i, d in enumerate(donors)}})
    v = feasibility_verdict(rows, _diag(floor=9.0, sil_range=1e-9), k_true=7, k_max=10)
    assert not v["criterion_3_silhouette_not_degenerate"]
    assert v["verdict"] == "NO-GO"


def test_verdict_never_reports_which_rank_won():
    """A 'winning K' on an A-OFF row would be the baseline selector under another name:
    computed while `delta` is null (§2 requires refusal), from outer-test outcomes (§1.5
    forbids it), on an arm where §5.3 makes selected_rank null by design."""
    donors = [f"d{i}" for i in range(12)]
    rows = _rows({7: {d: 10.0 + 0.1 * i for i, d in enumerate(donors)},
                  10: {d: 14.0 + 0.1 * i for i, d in enumerate(donors)}})
    v = feasibility_verdict(rows, _diag(floor=9.0, sil_range=0.1), k_true=7, k_max=10)
    serialised = repr(v).lower()
    for forbidden in ("selected", "best_k", "argmin", "winner", "chosen"):
        assert forbidden not in serialised


def test_missing_rank_is_an_error_not_a_silent_skip():
    rows = _rows({7: {"d0": 1.0, "d1": 2.0}})
    with pytest.raises(ValueError, match="no per-donor rows"):
        feasibility_verdict(rows, _diag(9.0, 0.1), k_true=7, k_max=10)


def test_runner_refuses_the_sealed_tier():
    """Two independent guards: this one, and `scenarios.seed_for` requiring unseal=True.
    A runner reachable by configuration would make the seal a convention, not a
    mechanism."""
    import yaml

    from cnmfbench.contract import ContractViolation
    from cnmfbench.records import _repo_root
    from cnmfbench.skeleton import check_preconditions

    root = _repo_root()
    with open(f"{root}/docs/benchmarks/configs/development.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    with open(f"{root}/docs/benchmarks/configs/ablation_plan.yaml", encoding="utf-8") as fh:
        ablation = yaml.safe_load(fh)
    cfg["evidence_tier"] = "SEALED_CONFIRMATION"
    with pytest.raises(ContractViolation, match="not runnable here"):
        check_preconditions(cfg, ablation)


def test_runner_refuses_when_promotion_is_allowed():
    import yaml

    from cnmfbench.contract import ContractViolation
    from cnmfbench.records import _repo_root
    from cnmfbench.skeleton import check_preconditions

    root = _repo_root()
    with open(f"{root}/docs/benchmarks/configs/development.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    with open(f"{root}/docs/benchmarks/configs/ablation_plan.yaml", encoding="utf-8") as fh:
        ablation = yaml.safe_load(fh)
    cfg["allow_scientific_promotion"] = True
    with pytest.raises(ContractViolation, match="may promote"):
        check_preconditions(cfg, ablation)
