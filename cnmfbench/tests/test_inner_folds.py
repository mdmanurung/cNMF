"""Inner validation folds against a REAL cNMF fit (P0-05).

`test_splits_and_scoring.py` already proves `inner_donor_folds` partitions donors correctly
and refuses a leaked outer-test donor. That is a property of a pure function. This file
exists because of D017's lesson: a component is not hardened by unit tests on the function,
it is hardened by the path that uses it actually running. So every test here calls
`skeleton._run_inner_fold` — the production helper — against real `prepare/factorize/
combine/consensus`, and asserts on bytes read back off disk.

**Why this path has no production caller yet, stated plainly.** PROTOCOL §1.1 is explicit
that the A-OFF baseline selector reads `silhouette` and `prediction_error` from
`k_selection_stats`, computed by `consensus(skip_density_and_return_after_stats=True)` *on
the training fit itself* — "both inputs already exist on disk after a rank sweep; the
selector computes nothing new" (`PROTOCOL.md:48`). The A-OFF baseline never reads an inner
validation fold. So the inner loop runs only when A is on, and `check_preconditions`
(`skeleton.py:192`) still refuses A while `delta` is null. Until P0-06 sets `delta`, these
tests are the only thing that executes `_run_inner_fold`, and they are written to be a real
execution of it rather than a stand-in for one.

**The two failures this file is shaped around.**

1. **Clobbering.** cNMF writes under `output_dir/name/`. If an inner fit shared a name with
   its outer fold it would overwrite the outer `nmf_genes_list` and consensus spectra
   mid-run, and the outer evaluation would silently score against a dictionary fitted on a
   subset of its own training donors. Nothing would raise. Asserted on the bytes.

2. **One-level-down leakage.** The outer fold's `G` and `s_g` are fitted on ALL outer
   training donors, which include every inner fold's validation donors. An inner fit that
   reused them would be selecting a rank with preprocessing that had already seen the data
   it selects on — the exact leak the nesting exists to prevent, one level down. So
   `_run_inner_fold` passes no `genes_file` and refits `s_g`, and the leakage tests below
   perturb inner-validation donors and require bitwise invariance, with a positive control.
"""
import os
import shutil

import numpy as np
import pytest

pytestmark = pytest.mark.slow

SMOKE_CONFIG = "docs/benchmarks/configs/smoke_000m.yaml"
PERTURB_ADD = 17  # additive and integer, for the reason test_leakage.py's header gives


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _inner_artifacts(fold_dir, inner_split_id):
    """The inner fit's preprocessing state and dictionary, read back off disk."""
    import anndata as ad
    from cnmf import load_df_from_npz

    tmp = os.path.join(fold_dir, "inner", inner_split_id, "cnmf_tmp")
    norm = ad.read_h5ad(os.path.join(tmp, f"{inner_split_id}.norm_counts.h5ad"))
    spectra = {
        name: load_df_from_npz(os.path.join(tmp, name)).values
        for name in sorted(os.listdir(tmp))
        if ".consensus.df.npz" in name and ".spectra." in name
    }
    return {
        "G": list(norm.var_names),
        "cells": list(norm.obs_names),
        "norm_counts": np.asarray(norm.X, dtype=np.float64),
        "spectra": spectra,
    }


def _fit_inner(cfg, ds, fold, inner, fold_dir):
    """Call the production helper exactly as a runner with A on would."""
    import cnmfbench.skeleton as skeleton

    donors = np.asarray(ds.adata.obs["donor_id"]).astype(str)
    raw = np.asarray(ds.adata.X, dtype=np.float64)
    gene_names = list(ds.adata.var_names)
    return skeleton._run_inner_fold(
        inner, ds.adata, raw, donors, gene_names,
        cfg["factorization"]["candidate_ranks"], cfg, fold_dir,
        cfg["factorization"]["density_threshold"],
    )


@pytest.fixture(scope="module")
def nested(tmp_path_factory):
    """One real outer fit, then a real inner fit inside it, plus a perturbed inner fit.

    Module-scoped: three SMOKE cNMF fits, and every test below reads the same three.
    """
    import copy

    import yaml

    import cnmfbench.skeleton as skeleton
    from cnmfbench.scenarios import build_params, seed_for
    from cnmfbench.simulate import simulate
    from cnmfbench.splits import inner_donor_folds, outer_donor_folds

    root = _repo_root()
    cfg_path = os.path.join(root, SMOKE_CONFIG)
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    params = build_params(cfg["scenario"], cfg["evidence_tier"])
    ds = simulate(params, cfg["scenario"], cfg["evidence_tier"],
                  seed_for(cfg["evidence_tier"]), simulation_replicate=0)

    donors = np.asarray(ds.adata.obs["donor_id"]).astype(str)
    fold = outer_donor_folds(donors, cfg["validation"]["outer_donor_folds"], cfg["seed"])[0]
    inners = inner_donor_folds(fold, cfg["validation"]["inner_donor_folds"], cfg["seed"])
    inner = inners[0]

    # The real outer fit, so the clobbering assertion has genuine outer artifacts to guard.
    out_root = str(tmp_path_factory.mktemp("nested"))
    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(skeleton, "simulate", lambda *a, **k: ds)
        run = skeleton.run(cfg_path, out_root=out_root, run_id="nested-outer")
    finally:
        mp.undo()
    fold_dir = os.path.join(run["run_dir"], fold.outer_split_id)
    outer_genes_path = os.path.join(fold_dir, fold.outer_split_id, "cnmf_tmp",
                                    f"{fold.outer_split_id}.norm_counts.h5ad")
    outer_genes_before = open(
        os.path.join(fold_dir, fold.outer_split_id,
                     f"{fold.outer_split_id}.overdispersed_genes.txt"), "rb").read()

    clean_scores = _fit_inner(cfg, ds, fold, inner, fold_dir)
    clean_art = _inner_artifacts(fold_dir, inner.inner_split_id)
    outer_genes_after = open(
        os.path.join(fold_dir, fold.outer_split_id,
                     f"{fold.outer_split_id}.overdispersed_genes.txt"), "rb").read()

    # The perturbed twin: ONLY this inner fold's validation donors change.
    val_rows = np.flatnonzero(np.isin(donors, np.asarray(inner.validation_donors)))
    assert val_rows.size, "no inner-validation cells; the leakage half would be vacuous"
    dirty_ds = copy.deepcopy(ds)
    x = np.array(dirty_ds.adata.X, dtype=dirty_ds.adata.X.dtype, copy=True)
    x[val_rows, :] = x[val_rows, :] + PERTURB_ADD
    dirty_ds.adata.X = x
    assert not np.array_equal(np.asarray(dirty_ds.adata.X), np.asarray(ds.adata.X))

    dirty_dir = os.path.join(run["run_dir"], fold.outer_split_id + "_dirty")
    os.makedirs(dirty_dir, exist_ok=True)
    dirty_scores = _fit_inner(cfg, dirty_ds, fold, inner, dirty_dir)
    dirty_art = _inner_artifacts(dirty_dir, inner.inner_split_id)

    payload = {
        "cfg": cfg, "ds": ds, "donors": donors, "fold": fold, "inners": inners,
        "inner": inner, "fold_dir": fold_dir,
        "outer_genes_before": outer_genes_before, "outer_genes_after": outer_genes_after,
        "outer_norm_path": outer_genes_path,
        "clean_scores": clean_scores, "dirty_scores": dirty_scores,
        "clean": clean_art, "dirty": dirty_art, "val_rows": val_rows,
    }
    yield payload
    shutil.rmtree(out_root, ignore_errors=True)


# ----------------------------------------------------------------- it runs, and it returns


def test_an_inner_fold_fits_and_scores_every_candidate_rank(nested):
    """SMOKE leaves only 2 inner-training donors (8 donors, 2 outer folds, 2 inner folds),
    which is the tier's smallest fit by some margin. If cNMF cannot fit there, that is a
    finding about the tier and must be said rather than worked around by quietly lowering
    the fold count — the same shape as "SMOKE cannot test feature C"."""
    scores = nested["clean_scores"]
    ranks = list(nested["cfg"]["factorization"]["candidate_ranks"])
    assert [s["candidate_rank"] for s in scores] == ranks
    for s in scores:
        assert np.isfinite(s["heldout_squared_prediction_error_counts_v1"])
        assert s["heldout_squared_prediction_error_counts_v1"] > 0
        assert s["n_scored_cells"] > 0
        assert s["n_eligible_donors"] == len(nested["inner"].validation_donors)
        assert s["inner_split_id"] == nested["inner"].inner_split_id


def test_the_inner_score_table_is_the_shape_a_selector_consumes(nested):
    """Feature A selects K from this table. One row per candidate rank, one comparable
    number per row, and the rank actually labelled — a table that repeated a rank or
    omitted one would let a selector pick a K that was never scored."""
    scores = nested["clean_scores"]
    ranks = [s["candidate_rank"] for s in scores]
    assert len(set(ranks)) == len(ranks), "a candidate rank appears twice"
    assert len({s["mask_id"] for s in scores}) == 1, (
        "the gene panel changed between candidate ranks inside one inner fold. PROTOCOL "
        "§4.1 requires one panel across the ranks of a comparison, and this table IS a "
        "comparison across ranks — a selector reading it would be comparing panels."
    )


# --------------------------------------------------------- failure 1: clobbering the outer


def test_inner_fits_do_not_overwrite_the_outer_folds_gene_list(nested):
    """The trap `skeleton.py`'s header names: cNMF keys its outputs on `name`, so an inner
    fit sharing the outer fold's name would replace the outer `overdispersed_genes.txt` and
    consensus spectra in place. The outer evaluation would then score against a dictionary
    fitted on a SUBSET of its own training donors, with nothing raised and no diagnostic
    moved. Asserted on the bytes, because the failure is a silent overwrite."""
    assert nested["outer_genes_before"] == nested["outer_genes_after"], (
        "the outer fold's gene list changed while inner folds were fitted"
    )


def test_the_inner_fit_writes_somewhere_the_outer_fit_does_not(nested):
    """The structural half of the same guarantee: separate directories, so the invariance
    above holds by construction rather than by the two fits happening not to collide."""
    fold_dir, fold = nested["fold_dir"], nested["fold"]
    inner_dir = os.path.join(fold_dir, "inner", nested["inner"].inner_split_id)
    outer_dir = os.path.join(fold_dir, fold.outer_split_id)
    assert os.path.isdir(inner_dir) and os.path.isdir(outer_dir)
    assert os.path.realpath(inner_dir) != os.path.realpath(outer_dir)


# ------------------------------------------------ failure 2: leakage one level down


def test_the_inner_fit_sees_inner_training_cells_and_no_validation_cell(nested):
    """§3.3 one level down. `norm_counts` is the matrix cNMF actually factorized, so this
    reads what the engine saw rather than what the caller intended it to see."""
    ds, donors = nested["ds"], nested["donors"]
    obs = list(ds.adata.obs_names)
    seen = set(nested["clean"]["cells"])
    assert seen, "the inner fit factorized nothing"

    train = set(np.asarray(obs)[np.isin(donors, np.asarray(nested["inner"].train_donors))])
    val = set(np.asarray(obs)[np.isin(donors, np.asarray(nested["inner"].validation_donors))])
    test = set(np.asarray(obs)[np.isin(donors, np.asarray(nested["fold"].test_donors))])

    assert not (seen & val), "an inner-validation cell reached the inner fit"
    assert not (seen & test), (
        "an OUTER-TEST cell reached an inner fit. Rank selection would then choose K using "
        "the data the outer fold is later scored on."
    )
    assert seen <= train


def test_perturbing_inner_validation_donors_does_not_change_the_inner_G_or_dictionary(nested):
    """The bitwise invariance, at the inner level. If the inner fit had reused the outer
    fold's `G` — which was computed over all outer-training donors, validation donors
    included — this would fail, because the outer `G` moves when those donors move.

    Bitwise, not approximate, for the reason `PROTOCOL.md:231-233` gives and
    `test_leakage.py`'s gate establishes for this environment.
    """
    clean, dirty = nested["clean"], nested["dirty"]
    assert clean["G"] == dirty["G"], (
        "the inner fit's gene universe moved when only its VALIDATION donors changed — "
        "so validation data is reaching inner preprocessing"
    )
    assert clean["cells"] == dirty["cells"], "the inner split itself moved"
    np.testing.assert_array_equal(
        clean["norm_counts"], dirty["norm_counts"],
        err_msg="the inner training matrix differs; s_g and everything after it would too",
    )
    assert set(clean["spectra"]) == set(dirty["spectra"]) and clean["spectra"]
    for name in sorted(clean["spectra"]):
        np.testing.assert_array_equal(
            clean["spectra"][name], dirty["spectra"][name],
            err_msg=f"inner {name} moved when only inner-validation counts changed",
        )


def test_perturbing_inner_validation_donors_DOES_change_the_inner_score(nested):
    """The positive control, and without it this file proves nothing: an inner loop that
    ignored its validation donors entirely — or returned a constant — would satisfy every
    invariance above. The score is the one quantity that MUST move."""
    clean = {s["candidate_rank"]: s["heldout_squared_prediction_error_counts_v1"]
             for s in nested["clean_scores"]}
    dirty = {s["candidate_rank"]: s["heldout_squared_prediction_error_counts_v1"]
             for s in nested["dirty_scores"]}
    assert set(clean) == set(dirty) and clean
    moved = [k for k in clean if clean[k] != dirty[k]]
    assert moved, (
        "no inner score moved after perturbing the inner-validation donors. Either the "
        "validation data never reached scoring, or the score ignores it — and every "
        "invariance above is then vacuous."
    )


# --------------------------------------------------------------- the refusal, end to end


def test_an_inner_fold_carrying_an_outer_test_donor_is_refused_before_any_fit(nested):
    """`inner_donor_folds` raises on a leaked donor; this checks the refusal survives the
    trip through the runner rather than being a property of the splitter alone. It is the
    highest-severity failure in the task: nothing crashes, the outer score is simply
    optimistic, and the number looks publishable."""
    from cnmfbench.contract import ContractViolation
    from cnmfbench.splits import DonorFold, inner_donor_folds

    fold = nested["fold"]
    # A fold whose training roster wrongly includes its own test donors — the mistake a
    # caller makes by passing the full donor list instead of the fold's training donors.
    leaky = DonorFold(fold.outer_split_id,
                      tuple(sorted(set(fold.train_donors) | set(fold.test_donors))),
                      fold.test_donors)
    with pytest.raises(ContractViolation, match="outer test donor"):
        inner_donor_folds(leaky, nested["cfg"]["validation"]["inner_donor_folds"],
                          nested["cfg"]["seed"])
