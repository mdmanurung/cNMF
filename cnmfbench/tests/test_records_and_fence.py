"""Schema conformance, controlled vocabularies, and the fence.

The TSV schemas are the interface between this programme and anyone reading its evidence
later. Nothing in the repo defined them in code before this session, so these tests are
what keeps the committed headers and the writer from drifting apart.
"""
import csv
import os

import pytest

from cnmfbench import provisional as P
from cnmfbench import records as R

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _header(name):
    with open(os.path.join(REPO, "docs/benchmarks", name), encoding="utf-8") as fh:
        return tuple(next(csv.reader(fh, delimiter="\t")))


def _ok_result(**over):
    base = dict(
        experiment_id="e1", configuration="000", arm="full_training_pool",
        dataset_id="d", independent_unit_id="donor_000", independent_unit_type="donor",
        outer_split_id="outer_0", metric="heldout_squared_prediction_error_v1",
        value="1.0", evaluation_scope="per_donor", candidate_rank=3,
        n_eligible_units=30, n_failed_units=0, status="ok_provisional",
        artifact_path="results/x",
    )
    base.update(over)
    return base


# ------------------------------------------------------------------- schema conformance


def test_results_schema_matches_the_committed_header_exactly():
    assert R.RESULTS_COLUMNS == _header("RESULTS.tsv")


def test_experiments_schema_matches_the_committed_header_exactly():
    assert R.EXPERIMENTS_COLUMNS == _header("EXPERIMENTS.tsv")


def test_exactly_the_eleven_protocol_metrics_are_allowed():
    assert len(R.METRIC_DIRECTION) == 11
    with pytest.raises(ValueError, match="not one of PROTOCOL"):
        R.result_row(**_ok_result(metric="silhouette"))


def test_direction_uses_the_section_5_1_strings():
    assert set(R.METRIC_DIRECTION.values()) == {"lower_is_better", "higher_is_better"}
    row = R.result_row(**_ok_result())
    assert row["direction"] == "lower_is_better"


def test_a_direction_contradicting_the_vocabulary_is_rejected():
    with pytest.raises(ValueError, match="contradicts"):
        R.result_row(**_ok_result(direction="higher_is_better"))


def test_selected_rank_must_be_null_on_a_fixed_rank_row():
    """§5.3. A non-null value here would be the baseline selector running while `delta`
    is null, which §2 requires to refuse."""
    assert R.result_row(**_ok_result())["selected_rank"] == ""
    with pytest.raises(ValueError, match="selected_rank must be null"):
        R.result_row(**_ok_result(selected_rank=3))


def test_none_like_strings_are_rejected_but_a_true_null_is_kept():
    """A blank means "genuinely null"; NOT_COMPUTED means "could not be produced". The
    strings that look like data but are accidents must not reach the file."""
    assert R.result_row(**_ok_result(value=None))["value"] == ""
    with pytest.raises(ValueError, match="would be written as"):
        R.result_row(**_ok_result(value="nan"))
    assert R.result_row(**_ok_result(value=R.NOT_COMPUTED))["value"] == "NOT_COMPUTED"


def test_tabs_and_newlines_are_rejected():
    with pytest.raises(ValueError, match="tab or newline"):
        R.result_row(**_ok_result(artifact_path="a\tb"))


def test_unknown_or_missing_columns_are_rejected():
    with pytest.raises(ValueError, match="unknown"):
        R.result_row(**_ok_result(extra_column="x"))
    incomplete = _ok_result()
    del incomplete["dataset_id"]
    with pytest.raises(ValueError, match="missing"):
        R.result_row(**incomplete)


def test_arm_is_not_labelled_matched_budget_by_accident():
    """The skeleton uses every training-donor cell with no budget, which is
    `upstream_full_data`'s definition applied to a training fold. Labelling it
    matched_budget would silently confound the future B comparison."""
    assert "full_training_pool" in R.ARM
    with pytest.raises(ValueError, match="arm"):
        R.result_row(**_ok_result(arm="whatever"))


def test_experiment_id_is_deterministic_and_seed_sensitive():
    args = ("000", "full_training_pool", "d", "outer_0", 3)
    a = R.make_experiment_id(*args, {"seed": 1})
    assert a == R.make_experiment_id(*args, {"seed": 1})
    assert a != R.make_experiment_id(*args, {"seed": 2})
    assert a != R.make_experiment_id("000", "full_training_pool", "d", "outer_1", 3, {"seed": 1})


def test_protocol_hash_matches_the_value_recorded_in_ablation_plan():
    import yaml

    with open(os.path.join(REPO, "docs/benchmarks/configs/ablation_plan.yaml"), encoding="utf-8") as fh:
        recorded = yaml.safe_load(fh)["protocol"]["sha256"]
    assert R.protocol_hash() == recorded


# ------------------------------------------------------------------------------ writing


def test_merge_refuses_a_duplicate_row(tmp_path):
    path = tmp_path / "RESULTS.tsv"
    R.write_rows(str(path), [], R.RESULTS_COLUMNS)
    rows = [R.result_row(**_ok_result())]
    R.merge_into_tracked(str(path), rows, R.RESULTS_COLUMNS)
    with pytest.raises(ValueError, match="already present"):
        R.merge_into_tracked(str(path), rows, R.RESULTS_COLUMNS)


def test_merge_preserves_the_header_and_appends(tmp_path):
    path = tmp_path / "RESULTS.tsv"
    R.write_rows(str(path), [], R.RESULTS_COLUMNS)
    R.merge_into_tracked(str(path), [R.result_row(**_ok_result())], R.RESULTS_COLUMNS)
    with open(path, encoding="utf-8") as fh:
        lines = list(csv.reader(fh, delimiter="\t"))
    assert tuple(lines[0]) == R.RESULTS_COLUMNS
    assert len(lines) == 2


def test_merge_rejects_a_mismatched_header(tmp_path):
    path = tmp_path / "bad.tsv"
    path.write_text("a\tb\n", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        R.merge_into_tracked(str(path), [], R.RESULTS_COLUMNS)


# ------------------------------------------------- the committed evidence is consistent


def _tracked(name):
    with open(os.path.join(REPO, "docs/benchmarks", name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_results_and_experiments_agree_on_cost():
    """The defect this guards against shipped once: RESULTS timed only the marginal
    consensus+scoring while EXPERIMENTS added an amortised share of the shared fit, so the
    two files disagreed by ~2.2x for the same experiment_id and the column a comparison
    reads made factorization free. Both are now rendered from one object; this keeps them
    that way."""
    results = {(r["experiment_id"], r["metric"]): r["value"] for r in _tracked("RESULTS.tsv")}
    experiments = _tracked("EXPERIMENTS.tsv")
    if not experiments:
        pytest.skip("no rows written yet")
    for e in experiments:
        for metric, column in (("wall_seconds_v1", "wall_seconds"),
                               ("cpu_seconds_v1", "cpu_seconds"),
                               ("peak_memory_mb_v1", "peak_memory_mb")):
            assert results[(e["experiment_id"], metric)] == e[column], (
                f"{e['experiment_id']}: {metric} != {column}"
            )


def test_shared_fit_cost_is_attributed_exactly_once():
    """One prepare/factorize/combine per fold serves every candidate rank, so its cost
    belongs to no single rank. It gets its own row with candidate_rank empty; per-rank
    rows carry marginal cost only. Summing the fold's rows therefore gives the true total
    with no double counting."""
    experiments = _tracked("EXPERIMENTS.tsv")
    if not experiments:
        pytest.skip("no rows written yet")
    # Group by the fold identity carried in `experiment_id` itself, which is
    # `{configuration}-{arm}-{dataset_id}[-{variant}]-{outer_split_id}-{rank}-{digest}`;
    # dropping the last two segments leaves exactly the fold.
    #
    # Two weaker keys were tried and both collided. `outer_split_id` alone collides across
    # runs, since every run names its folds `outer_0`, `outer_1`, ... Adding `dataset_id` and
    # the configuration bits still collides, because a `variant` run reuses the same dataset
    # and the label appears **only inside the id** — EXPERIMENTS.tsv has no `variant` column
    # (D014's recorded trade-off; `preprocessing_hash` is what distinguishes such rows by
    # content). The id prefix is the one key that carries every distinction.
    by_fold = {}
    for e in experiments:
        by_fold.setdefault(tuple(e["experiment_id"].split("-")[:-2]), []).append(e)
    for fold, rows in by_fold.items():
        fit = [r for r in rows if r["candidate_rank"] == ""]
        per_rank = [r for r in rows if r["candidate_rank"] != ""]
        assert len(fit) == 1, f"{fold}: expected exactly one fit-scope row, got {len(fit)}"
        assert per_rank, f"{fold}: no per-rank rows"
        # The shared fit dominates; a per-rank row carrying it too would show up here.
        assert float(fit[0]["wall_seconds"]) > max(float(r["wall_seconds"]) for r in per_rank)


def test_every_written_row_is_provisional_and_cannot_promote():
    """While the fence stands, every row must say so and must sit at a tier that cannot
    promote a feature. The two must not drift apart."""
    rows = _tracked("RESULTS.tsv")
    if not rows:
        pytest.skip("no rows written yet")
    assert not P.registry_is_empty()
    assert {r["status"] for r in rows} == {"ok_provisional"}
    assert {e["evidence_tier"] for e in _tracked("EXPERIMENTS.tsv")} <= {"SMOKE", "DEVELOPMENT"}
    assert all(e["prototype"] == "true" for e in _tracked("EXPERIMENTS.tsv"))


# -------------------------------------------------------------------------- the fence


def test_registry_and_decorators_agree_in_both_directions():
    """A registry entry without a decorator un-fences a component silently; a decorator
    without an entry cannot be read by the gate. Both must fail loudly."""
    import importlib
    import pkgutil

    import cnmfbench

    decorated = set()
    for mod in pkgutil.iter_modules(cnmfbench.__path__):
        m = importlib.import_module(f"cnmfbench.{mod.name}")
        for obj in vars(m).values():
            cid = getattr(obj, "__cnmfbench_provisional__", None)
            if cid:
                decorated.add(cid)
    assert decorated == set(P.PROVISIONAL)


def test_the_gate_is_blocked_while_components_are_provisional():
    assert not P.registry_is_empty()


def test_every_provisional_component_names_a_real_ledger_task():
    """Checks the owner against the ACTUAL task ledger, not a hardcoded prefix.

    The earlier version asserted `startswith("P0-")`, which was true only while the fence
    held P0 components alone; it failed the moment features B and C added entries owned by
    P2-01 and P3-01, both of which are real tasks. Reading the ledger is also strictly
    stronger than the prefix check ever was, because it catches a typo'd or retired task id
    — which is the failure that would actually orphan a fenced component.
    """
    import re

    with open(os.path.join(REPO, "docs/planning/PROGRESS.md"), encoding="utf-8") as fh:
        ledger = set(re.findall(r"^\|\s*((?:S0|P[0-9])-[0-9]+)\s*\|", fh.read(), re.M))
    assert len(ledger) >= 20, f"failed to parse the task ledger, found {len(ledger)}"
    for c in P.PROVISIONAL.values():
        assert c.owner_task in ledger, (
            f"{c.component_id} is owned by {c.owner_task!r}, which is not a task in "
            "PROGRESS.md. A fenced component whose owner does not exist can never be "
            "hardened, because no task will ever come up that claims it."
        )
        assert c.reason and c.hardening_requires


def test_calling_a_provisional_component_records_it():
    """`splits.gene_panel` and `scoring.nnls_usages` were un-fenced at D021, so a still-
    fenced component is needed to exercise this. `outer_donor_folds` remains fenced,
    reassigned to P0-06."""
    from cnmfbench.splits import outer_donor_folds

    P.reset_touched()
    assert P.touched() == ()
    outer_donor_folds([f"d{i}" for i in range(8)], 2, 1)
    assert "splits.outer_donor_folds" in P.touched()


def test_cited_rows_check_is_scoped_not_a_whole_file_scan():
    """Provisional rows stay in RESULTS.tsv forever and correctly. A whole-file scan
    would block the gate permanently no matter how much hardening happened."""
    rows = [{"experiment_id": "old", "status": "ok_provisional"},
            {"experiment_id": "new", "status": "ok"}]
    assert P.cited_rows_are_not_provisional(rows, ["new"])
    assert not P.cited_rows_are_not_provisional(rows, ["old"])


def test_the_throwaway_reference_is_not_imported_by_the_real_path():
    """D006's named hazard: `diagnostics._score_split` must be read as reference and not
    become the implementation. It is also cited P0-03 evidence, so it must not change."""
    import pathlib

    for path in pathlib.Path(REPO, "cnmfbench").glob("*.py"):
        if path.name == "diagnostics.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "_score_split" not in text, f"{path.name} references the throwaway scorer"
        assert "_equal_donor_mean_sse" not in text, f"{path.name} references the throwaway aggregator"


# ------------------------------------------------------------------- the pooling guard


def test_pooling_across_folds_is_refused():
    """Measured at SMOKE: Jaccard(G_0, G_1) = 0.639, so the folds are not on a common
    axis and averaging them describes no measurement. The schema cannot express that;
    preprocessing_hash can, and this is what uses it."""
    from cnmfbench.analysis import PoolingError, assert_poolable, pooling_groups

    rows, experiments = _tracked("RESULTS.tsv"), _tracked("EXPERIMENTS.tsv")
    if not rows:
        pytest.skip("no rows written yet")
    groups = pooling_groups(rows, experiments)
    assert len(groups) > 1, "expected per-fold preprocessing_hash values to differ"
    with pytest.raises(PoolingError, match="common axis"):
        assert_poolable(rows, experiments)
    # Within one group it must succeed — the guard must not block valid aggregation.
    assert assert_poolable(next(iter(groups.values())), experiments)


def test_pooling_across_the_two_B_arms_is_refused_although_their_gene_panel_is_identical():
    """The gap `preprocessing_hash` alone could not see.

    Feature B holds `G` deliberately constant across its arms — verified byte-identical, via
    `prepare(genes_file=...)` — so every input to `preprocessing_hash` is the same on both
    sides and the two arms hash IDENTICALLY (measured: `c9ba55b825846b53205c1816` for all
    four SMOKE configurations at `outer_0`). What differs is `s_g`, which `prepare` computes
    from whichever cells the sampling rule drew, by a median factor of 1.04 and up to 1.24.

    So the guard's own promise — rows spanning "different gene panels and per-gene scales"
    are refused — was false on the scale half, and a cross-arm `groupby().mean()` would have
    been permitted. `discovery_cells_hash` is what makes the arms distinguishable. See D016.
    """
    from cnmfbench.analysis import PoolingError, assert_poolable

    experiments = [
        {"experiment_id": "b_off", "preprocessing_hash": "same", "discovery_cells_hash": "A"},
        {"experiment_id": "b_on", "preprocessing_hash": "same", "discovery_cells_hash": "B"},
    ]
    rows = [{"experiment_id": "b_off"}, {"experiment_id": "b_on"}]
    assert len({e["preprocessing_hash"] for e in experiments}) == 1, (
        "this test is only meaningful while the two arms share a preprocessing_hash"
    )
    with pytest.raises(PoolingError, match="DIFFERENT CELLS"):
        assert_poolable(rows, experiments)
    assert assert_poolable(rows[:1], experiments), "one arm alone must still pool"


def test_pooling_guard_refuses_rows_with_no_provenance():
    from cnmfbench.analysis import PoolingError, assert_poolable

    with pytest.raises(PoolingError, match="absent from EXPERIMENTS"):
        assert_poolable([{"experiment_id": "ghost"}], [])


# ----------------------------------------------------------- the §4.1 panel-identity audit


def test_a_comparison_spanning_two_mask_ids_is_refused():
    """PROTOCOL §4.1: 'the harness must refuse such a comparison rather than report it.'
    `assert_poolable` would catch this only indirectly, as a `preprocessing_hash`
    difference that could equally mean a different s_g or num_highvar_genes — this names
    the panel specifically."""
    from cnmfbench.analysis import PoolingError, assert_panels_identical

    experiments = [
        {"experiment_id": "e1", "mask_id": "panelA"},
        {"experiment_id": "e2", "mask_id": "panelB"},
    ]
    rows = [{"experiment_id": "e1"}, {"experiment_id": "e2"}]
    with pytest.raises(PoolingError, match="DIFFERENT gene panels"):
        assert_panels_identical(rows, experiments)
    assert assert_panels_identical(rows[:1], experiments)


def test_fit_scope_rows_with_no_computed_panel_do_not_trip_the_audit():
    """Fit-scope and failed rows carry `mask_id=NOT_COMPUTED` (`skeleton.py`). Counting
    that as a distinct panel would make every comparison that includes one falsely look
    like it spans two panels — the same reason `assert_poolable` skips rows it cannot
    place, but stated for this check specifically since NOT_COMPUTED is not simply absent."""
    from cnmfbench.analysis import assert_panels_identical

    experiments = [
        {"experiment_id": "fit", "mask_id": "NOT_COMPUTED"},
        {"experiment_id": "rank2", "mask_id": "panelA"},
        {"experiment_id": "rank3", "mask_id": "panelA"},
    ]
    rows = [{"experiment_id": "fit"}, {"experiment_id": "rank2"}, {"experiment_id": "rank3"}]
    assert assert_panels_identical(rows, experiments)


def test_panel_identity_holds_within_the_tracked_evidence_per_outer_fold():
    """Measured against the tracked rows: within one outer fold (where one `prepare` call
    serves every candidate rank by construction, `skeleton.py`'s own comment on the fit
    row), every configuration's ranked rows must share one mask_id."""
    from cnmfbench.analysis import assert_panels_identical

    rows, experiments = _tracked("RESULTS.tsv"), _tracked("EXPERIMENTS.tsv")
    if not rows:
        pytest.skip("no rows written yet")
    # Scoped to (dataset_manifest_hash, outer_split_id): `outer_0` is reused across
    # SMOKE, DEVELOPMENT and every simulation replicate, and those are different
    # datasets with independently-fit gene panels — grouping by outer_split_id alone
    # would mix runs that were never meant to be one comparison.
    by_fold = {}
    for e in experiments:
        key = (e.get("dataset_manifest_hash", ""), e.get("outer_split_id", ""))
        by_fold.setdefault(key, []).append(e["experiment_id"])
    ranked_rows = [r for r in rows if r.get("candidate_rank")]
    for (dataset_hash, fold), ids in by_fold.items():
        if not fold:
            continue
        fold_rows = [r for r in ranked_rows if r["experiment_id"] in set(ids)]
        if fold_rows:
            assert assert_panels_identical(fold_rows, experiments)


def test_panel_audit_refuses_rows_with_no_provenance():
    from cnmfbench.analysis import PoolingError, assert_panels_identical

    with pytest.raises(PoolingError, match="absent from EXPERIMENTS"):
        assert_panels_identical([{"experiment_id": "ghost"}], [])


def test_a_variant_changes_the_id_and_its_absence_leaves_every_existing_id_untouched():
    """The invariant `same id => same experiment` was violated in practice: the convergence
    diagnostic re-ran DEVELOPMENT with max_optimizer_iterations 300 -> 1000, giving the same
    configuration, arm, dataset and seeds with different numbers, so both runs produced the
    same id and `merge_into_tracked` refused the second as a contradiction.

    `variant` repairs it, and the second assertion is the one that matters for cost: because
    the label is folded in ONLY when set, every id written before it existed stays valid and
    no evidence needs regenerating.
    """
    args = ("000", "full_training_pool", "base_identifiable_DEVELOPMENT_r0", "outer_0", 7)
    seeds = {"seed": 90210, "panel_seed": 20260918}
    plain = R.make_experiment_id(*args, seeds)
    with_variant = R.make_experiment_id(*args, seeds, variant="conv1000")

    assert plain != with_variant, "a variant run must not collide with the run it diagnoses"
    assert "conv1000" in with_variant, "the label must be readable in the id, not only hashed"
    assert R.make_experiment_id(*args, seeds, variant=None) == plain
    assert R.make_experiment_id(*args, seeds, variant="") == plain


def test_every_tracked_id_is_shaped_like_its_own_columns():
    """Checks the readable *prefix* of each tracked id against the columns that can supply it.

    Deliberately narrow, and the docstring says so because an earlier version of this test
    overclaimed. **It cannot verify that ids are unchanged**, which is D014's actual claim: it
    never inspects the digest, so a change to `make_experiment_id`'s payload would leave every
    prefix intact and this test green.

    A faithful round-trip is not possible against the current schema. `EXPERIMENTS.tsv` has no
    `configuration` column, no `seeds` and no `variant`, so **a row does not carry enough to
    reconstruct its own `experiment_id`** — recorded as a second D014 trade-off rather than
    papered over with a test that looks stronger than it is. Adding those columns is a header
    change, which is P0-07's business.
    """
    experiments = _tracked("EXPERIMENTS.tsv")
    if not experiments:
        pytest.skip("no rows written yet")
    for e in experiments:
        head, _, tail = e["experiment_id"].partition(f"-{e['arm']}-")
        assert tail, f"{e['experiment_id']} does not contain its own arm {e['arm']!r}"
        assert head, f"{e['experiment_id']} has no configuration segment"
        assert tail.startswith(e["dataset_id"]), (
            f"{e['experiment_id']} does not carry its own dataset_id {e['dataset_id']!r}"
        )
        assert e["outer_split_id"] in tail, (
            f"{e['experiment_id']} does not carry its own outer_split_id"
        )
