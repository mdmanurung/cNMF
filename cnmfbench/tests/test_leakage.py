"""The leakage audit (P0-05).

PROTOCOL §3.2 calls the transform `training_fitted_and_leakage_audited` and then says
(`PROTOCOL.md:231-233`) that **"leakage audited" means the claim is tested, not
asserted**: P0-05 must demonstrate that perturbing held-out values leaves `G`, `s_g`, the
dictionary and the inference-panel usages *bitwise* unchanged.

`IMPLEMENTATION_PROMPT.md:192` is the full requirement:

    Required leakage tests must show that modifying held-out values does not change the
    dictionary, preprocessing state, usages inferred from the inference panel, rank
    selection on unrelated inner folds, or cache identities of training-only artifacts.
    Modifying true outer-test values may change its score, but never chosen
    hyperparameters. Test row-total normalization leakage explicitly.

Three design choices carry the whole file, and each is a way these tests could have been
written so that they proved nothing.

**1. They run the REAL runner, not a reimplementation of it.** A leakage suite built on a
hand-rolled copy of the pipeline tests the copy. `skeleton.run` is called end to end and
only `simulate` is substituted, so every guard, every ordering and every cNMF call is the
one that produces tracked rows. There is no test-only hook in production code.

**2. The perturbation is applied BEFORE `prepare`, to the dataset.** Perturbing the
training-only `.h5ad` after the split is vacuous: that file never contained held-out cells
in the first place, so every invariance would hold trivially and the suite would report
safety it had not checked. The dataset is perturbed and the split is then computed from
it, exactly as a real run would.

**3. There is a positive control.** A pipeline that ignored held-out data entirely would
pass every invariance in this file. `IMPLEMENTATION_PROMPT.md:192` requires that
modifying outer-test values *may change its score* — so the suite also asserts that the
score DOES move. Without it, `return 0.0` passes the audit.

**4. There is a same-input control, and it is a gate.** `PROGRESS.md:21` makes no bitwise
claim across BLAS builds, thread counts or platforms — the bitwise result in
`SOURCE_AUDIT.md` §1.5.1 is same-environment. So two *unperturbed* runs are compared
first. Without that, a failing invariance below is ambiguous between a real leak and
ordinary non-reproducibility, and the plausible-looking fix is to loosen the comparison to
D004's 1e-5 — which would let a real leak of size 1e-6 through forever and quietly
contradict `PROTOCOL.md:231-233`'s word *bitwise*.

**The perturbation is additive, not multiplicative.** `x *= 7` is a no-op wherever the
count is zero, and at SMOKE most entries are. A multiplicative perturbation would leave
much of the held-out matrix untouched and every invariance below would pass for the wrong
reason. Each test that depends on the perturbation asserts it actually landed.
"""
import json
import os
import shutil

import numpy as np
import pytest

pytestmark = pytest.mark.slow

SMOKE_CONFIG = "docs/benchmarks/configs/smoke_000m.yaml"
# ADDITIVE, and an integer so the matrix stays a count matrix. A multiplicative
# perturbation is a no-op on every zero entry, and at SMOKE most entries are zero.
PERTURB_ADD = 17


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _base_dataset(cfg):
    from cnmfbench.scenarios import build_params, seed_for
    from cnmfbench.simulate import simulate

    params = build_params(cfg["scenario"], cfg["evidence_tier"],
                          **(cfg.get("simulation_overrides") or {}))
    return simulate(params, cfg["scenario"], cfg["evidence_tier"],
                    seed_for(cfg["evidence_tier"]),
                    simulation_replicate=cfg.get("simulation_replicate", 0))


def _held_out_donors(cfg, ds):
    """The outer-test donors of fold 0 — computed the way the runner computes them."""
    from cnmfbench.splits import outer_donor_folds

    donors = np.asarray(ds.adata.obs["donor_id"]).astype(str)
    folds = outer_donor_folds(donors, cfg["validation"]["outer_donor_folds"], cfg["seed"])
    return folds[0].test_donors, donors


def _perturbed(ds, rows, cols=None):
    """A copy of `ds` with the named cells' counts raised, before anything sees it.

    ADDITIVE on purpose: `x * 7` leaves every zero at zero, and at SMOKE most entries are
    zero, so a multiplicative perturbation would silently fail to perturb most of the
    held-out matrix. Integer so the result is still a count matrix — a float would change
    the dtype and trip the simulator's §6 contract checks on something other than the
    property under test.

    `cols=None` perturbs every gene.
    """
    import copy

    out = copy.deepcopy(ds)
    x = np.array(out.adata.X, dtype=out.adata.X.dtype, copy=True)
    if cols is None:
        x[rows, :] = x[rows, :] + PERTURB_ADD
    else:
        x[np.ix_(rows, cols)] = x[np.ix_(rows, cols)] + PERTURB_ADD
    out.adata.X = x
    assert not np.array_equal(np.asarray(out.adata.X), np.asarray(ds.adata.X)), (
        "the perturbation changed nothing; every test built on it would be vacuous"
    )
    return out


def _run(cfg_path, out_root, run_id, dataset):
    """Run the real pipeline with `simulate` substituted. No production hook."""
    import cnmfbench.skeleton as skeleton

    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(skeleton, "simulate", lambda *a, **k: dataset)
        return skeleton.run(cfg_path, out_root=out_root, run_id=run_id)
    finally:
        mp.undo()


AUDITED_FOLD = "outer_0"
"""The fold whose held-out donors are perturbed, and therefore the ONLY fold whose
artifacts may be asserted invariant.

With two outer folds the donors are partitioned, so `outer_0`'s test donors are
`outer_1`'s *training* donors. An invariance asserted across both folds is not a stronger
test, it is a false one — `test_perturbing_held_out_values_does_not_change_the_stability_curve`
asserts the other half explicitly, that `outer_1` DOES move."""


def _artifacts(run_dir, fold=AUDITED_FOLD):
    """Everything a leak would have to pass through, read back off disk."""
    import anndata as ad
    from cnmf import load_df_from_npz

    from cnmfbench.hashing import artifact_hash

    tmp = os.path.join(run_dir, fold, fold, "cnmf_tmp")
    genes_path = os.path.join(tmp, f"{fold}.overdispersed_genes.txt")
    if not os.path.exists(genes_path):
        genes_path = os.path.join(run_dir, fold, fold, f"{fold}.overdispersed_genes.txt")
    norm = ad.read_h5ad(os.path.join(tmp, f"{fold}.norm_counts.h5ad"))
    spectra = {}
    for name in sorted(os.listdir(tmp)):
        if ".consensus.df.npz" in name and ".spectra." in name:
            spectra[name] = load_df_from_npz(os.path.join(tmp, name)).values
    hashes = {
        n: artifact_hash(os.path.join(tmp, n))
        for n in sorted(os.listdir(tmp))
        if n.endswith((".npz", ".h5ad", ".txt"))
    }
    return {
        "G": list(norm.var_names),
        "training_cells": list(norm.obs_names),
        "norm_counts": np.asarray(norm.X, dtype=np.float64),
        "spectra": spectra,
        "artifact_hashes": hashes,
        "diagnostics": json.load(open(os.path.join(run_dir, "diagnostics.json"))),
    }


@pytest.fixture(scope="module")
def audit(tmp_path_factory):
    """Two real runs whose datasets differ ONLY in outer-test donors' counts.

    Module-scoped: the pair costs two SMOKE cNMF runs and every test below reads it.
    """
    import yaml

    root = _repo_root()
    cfg_path = os.path.join(root, SMOKE_CONFIG)
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    ds = _base_dataset(cfg)
    test_donors, donors = _held_out_donors(cfg, ds)
    held_out_rows = np.flatnonzero(np.isin(donors, np.asarray(test_donors)))
    assert held_out_rows.size, "no held-out cells; the audit would be vacuous"

    out_root = str(tmp_path_factory.mktemp("leakage"))
    clean = _run(cfg_path, out_root, "leak-clean", ds)
    # The same-input control: identical dataset, second run. Compared in
    # `test_two_identical_runs_agree_bitwise_in_this_environment`, which gates the rest.
    repeat = _run(cfg_path, out_root, "leak-repeat", ds)
    dirty = _run(cfg_path, out_root, "leak-dirty", _perturbed(ds, held_out_rows))

    payload = {
        "cfg": cfg, "cfg_path": cfg_path, "ds": ds, "donors": donors,
        "test_donors": test_donors, "held_out_rows": held_out_rows,
        "clean_dir": clean["run_dir"], "dirty_dir": dirty["run_dir"],
        "clean": _artifacts(clean["run_dir"]), "dirty": _artifacts(dirty["run_dir"]),
        "repeat": _artifacts(repeat["run_dir"]),
    }
    yield payload
    shutil.rmtree(out_root, ignore_errors=True)


# ------------------------------------------------------------- the gate on everything else


def test_two_identical_runs_agree_bitwise_in_this_environment(audit):
    """THE GATE. Every invariance below compares two runs and asserts bitwise equality.
    That is only a test of leakage if bitwise equality holds for two runs of the SAME
    input — otherwise a failure is ambiguous between a leak and ordinary
    non-reproducibility, and the tempting repair is to loosen to D004's 1e-5, which would
    let a real leak of size 1e-6 through forever.

    `PROGRESS.md:21` deliberately makes no bitwise claim across BLAS builds, thread counts
    or platforms. This asserts it holds *here*, which is the only place it is being used.
    If this fails, the leakage suite cannot run as written and that is the finding — do
    not relax the comparisons below.
    """
    a, b = audit["clean"], audit["repeat"]
    assert a["G"] == b["G"], "G is not reproducible run to run; the audit cannot proceed"
    np.testing.assert_array_equal(a["norm_counts"], b["norm_counts"])
    assert set(a["spectra"]) == set(b["spectra"]) and a["spectra"]
    for name in sorted(a["spectra"]):
        np.testing.assert_array_equal(
            a["spectra"][name], b["spectra"][name],
            err_msg=f"{name} differs between two runs of identical input",
        )


# ------------------------------------------------- the precondition these tests rest on


def test_the_perturbation_touched_held_out_cells_and_no_training_cell(audit):
    """If the perturbation reached a training cell, every invariance below would be
    measuring its own setup rather than the pipeline. `G` depends on cNMF's Fano ranking
    over training cells, so it is bitwise-stable only while the training matrix is."""
    clean, dirty = audit["clean"], audit["dirty"]
    assert clean["training_cells"] == dirty["training_cells"], "the split itself moved"
    held_out = set(np.asarray(audit["ds"].adata.obs_names)[audit["held_out_rows"]])
    assert not (set(clean["training_cells"]) & held_out), (
        "a perturbed cell reached cNMF; §3.3 requires training-only inputs"
    )
    np.testing.assert_array_equal(
        clean["norm_counts"], dirty["norm_counts"],
        err_msg="the training matrix cNMF saw differs between runs",
    )


# --------------------------------------- IMPLEMENTATION_PROMPT.md:192, clause by clause


def test_perturbing_held_out_values_does_not_change_G(audit):
    """Preprocessing state, part 1. `G` is chosen by Fano ranking; if held-out cells
    entered that ranking, the gene universe itself would depend on the test set."""
    assert audit["clean"]["G"] == audit["dirty"]["G"]


def test_perturbing_held_out_values_does_not_change_s_g(audit):
    """Preprocessing state, part 2, and the one D016 makes load-bearing: `s_g` sets the
    units every loss is expressed in, so a leak here would move every number at once."""
    from cnmfbench.scoring import training_gene_scale

    scales = []
    for key, run_dir in (("clean", audit["clean_dir"]), ("dirty", audit["dirty_dir"])):
        art = audit[key]
        raw = np.asarray(audit["ds"].adata.X, dtype=np.float64)
        gene_names = list(audit["ds"].adata.var_names)
        g_pos = np.array([gene_names.index(g) for g in art["G"]])
        rows = np.array([list(audit["ds"].adata.obs_names).index(c)
                         for c in art["training_cells"]])
        scales.append(training_gene_scale(raw[np.ix_(rows, g_pos)]))
    np.testing.assert_array_equal(scales[0], scales[1])


def test_perturbing_held_out_values_does_not_change_the_dictionary(audit):
    """The dictionary is what every downstream number is computed against. §3.3 already
    forbids refitting it on test data; this shows test data cannot reach it at all."""
    clean, dirty = audit["clean"]["spectra"], audit["dirty"]["spectra"]
    assert set(clean) == set(dirty) and clean, "no consensus spectra were produced"
    for name in sorted(clean):
        np.testing.assert_array_equal(
            clean[name], dirty[name],
            err_msg=f"{name} moved when only held-out counts changed",
        )


def test_perturbing_held_out_values_does_not_change_cache_identities(audit):
    """"Cache identities of training-only artifacts". Hashes rather than contents,
    because P0-07 will key a cache on exactly these and a cache that rebuilt when a test
    donor changed would be both wrong and expensive."""
    clean, dirty = audit["clean"]["artifact_hashes"], audit["dirty"]["artifact_hashes"]
    moved = sorted(n for n in set(clean) & set(dirty) if clean[n] != dirty[n])
    assert not moved, f"training-only artifacts changed: {moved}"


def test_perturbing_held_out_values_does_not_change_the_stability_curve(audit):
    """"Rank selection on unrelated inner folds." The selector is not implemented yet
    (`delta` is null and §2 requires refusal), so the auditable surface is its INPUT: the
    silhouette curve the rule reads. If that is invariant, no selector built on it can
    leak through this route, and this test starts failing the day one is wired in wrongly.

    **The claim is scoped to `outer_0`, and the scoping is the point.** With two outer
    folds the donors are partitioned, so fold 0's TEST donors are fold 1's TRAINING
    donors. Perturbing them *must* move `outer_1`'s curve — that is the split working, not
    a leak. An earlier version of this test asserted invariance across every fold and
    failed on `outer_1` for exactly that reason.

    So both halves are asserted: invariant where the donors are held out, and **moved**
    where the same donors are training data. The second half is a positive control — it
    shows the perturbation is large enough to move a silhouette curve at all, which is
    what makes the first half evidence rather than an artifact of a perturbation too
    small to matter.
    """
    clean = {d["outer_split_id"]: d for d in audit["clean"]["diagnostics"]}
    dirty = {d["outer_split_id"]: d for d in audit["dirty"]["diagnostics"]}
    assert set(clean) == set(dirty)

    assert clean["outer_0"]["silhouette_by_k"] == dirty["outer_0"]["silhouette_by_k"], (
        "outer_0's stability curve moved although only its held-out donors changed"
    )

    if "outer_1" in clean:
        assert clean["outer_1"]["silhouette_by_k"] != dirty["outer_1"]["silhouette_by_k"], (
            "outer_1's curve did NOT move, although the perturbed donors are its TRAINING "
            "donors. Either the perturbation never reached a fit, or the fold assignment "
            "is not what this test assumes — and outer_0's invariance above is then "
            "evidence of nothing."
        )


# ------------------------------------------------------- the row-total normalization test


def test_a_held_out_cells_library_total_cannot_reach_its_inference_usages(audit):
    """`test_library_total_normalization: forbidden` (`ablation_plan.yaml:61`), tested.

    PROTOCOL §3.1 gives the reason: TPM normalizes a cell by its total across ALL genes,
    which for a held-out cell includes its validation panel — so the cell's own held-out
    values would reach the usages estimated from its inference panel. cNMF's
    `compute_tpm` **does** normalize by row totals; what makes that safe is that cNMF only
    ever sees training cells (§3.3).

    So this changes a held-out cell's library total *through its validation panel only*
    and asserts its inference-panel usages do not move by a single bit. Bitwise is
    achievable because `nnls_usages` uses `scipy.optimize.nnls` rather than a
    tolerance-based solver — `scoring.py:79-81` records that the solver was chosen for
    this test.
    """
    from cnmfbench.scoring import nnls_usages, scoreable_mask, to_training_scale, training_gene_scale
    from cnmfbench.splits import gene_panel

    art = audit["clean"]
    cfg, ds = audit["cfg"], audit["ds"]
    gene_names = list(ds.adata.var_names)
    g_list = art["G"]
    g_pos = np.array([gene_names.index(g) for g in g_list])
    panel = gene_panel(g_list, cfg["validation"]["inference_gene_fraction"],
                       cfg["validation"]["panel_seed"])
    inf_pos = np.array([g_list.index(g) for g in panel.inference_genes])

    raw = np.asarray(ds.adata.X, dtype=np.float64)
    train_rows = np.array([list(ds.adata.obs_names).index(c) for c in art["training_cells"]])
    s_g = training_gene_scale(raw[np.ix_(train_rows, g_pos)])
    v = next(iter(sorted(art["spectra"])))
    dictionary = art["spectra"][v]

    val_gene_cols = g_pos[np.array([g_list.index(g) for g in panel.validation_genes])]
    dirty_ds = _perturbed(ds, audit["held_out_rows"], val_gene_cols)
    dirty_raw = np.asarray(dirty_ds.adata.X, dtype=np.float64)

    rows = audit["held_out_rows"]
    before_g, after_g = raw[np.ix_(rows, g_pos)], dirty_raw[np.ix_(rows, g_pos)]
    keep = scoreable_mask(before_g[:, inf_pos])

    totals_before = raw[rows, :].sum(axis=1)
    totals_after = dirty_raw[rows, :].sum(axis=1)
    assert np.any(totals_after != totals_before), (
        "the perturbation did not change any library total, so this test checks nothing"
    )
    np.testing.assert_array_equal(
        before_g[:, inf_pos], after_g[:, inf_pos],
        err_msg="the perturbation touched the inference panel; it must touch only validation genes",
    )

    u_before = nnls_usages(to_training_scale(before_g, s_g)[keep][:, inf_pos],
                           dictionary[:, inf_pos])
    u_after = nnls_usages(to_training_scale(after_g, s_g)[keep][:, inf_pos],
                          dictionary[:, inf_pos])
    np.testing.assert_array_equal(
        u_before, u_after,
        err_msg="a held-out cell's validation-panel counts reached its inference usages",
    )


# ------------------------------------------------------------------- the positive control


def test_perturbing_outer_test_values_DOES_change_the_score(audit):
    """Without this, the file is worthless: a pipeline that ignored held-out data
    entirely would satisfy every invariance above. `IMPLEMENTATION_PROMPT.md:192` says
    modifying true outer-test values "may change its score, but never chosen
    hyperparameters" — so the score must move while everything above stays fixed."""
    import csv

    def losses(run_dir):
        out = {}
        with open(os.path.join(run_dir, "results.tsv"), newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if (r["evaluation_scope"] == "equal_donor_mean"
                        and r["metric"].startswith("heldout_squared_prediction_error")):
                    out[(r["outer_split_id"], r["candidate_rank"], r["metric"])] = float(r["value"])
        return out

    clean, dirty = losses(audit["clean_dir"]), losses(audit["dirty_dir"])
    assert clean and set(clean) == set(dirty)

    # Scoped to the audited fold, and for the same reason the stability-curve test is:
    # `outer_1`'s losses move because the perturbed donors are its TRAINING donors. If
    # `moved` were collected across both folds, `outer_1` would mask an invariant
    # `outer_0` — which is the exact failure this control exists to catch.
    audited = [k for k in clean if k[0] == AUDITED_FOLD]
    assert audited, f"no {AUDITED_FOLD} loss rows; the control cannot run"
    moved = [k for k in audited if clean[k] != dirty[k]]
    assert moved, (
        f"{AUDITED_FOLD}'s held-out scores are identical after perturbing its held-out "
        "counts. Either the perturbation never reached scoring, or the evaluator ignores "
        "held-out data — and in either case every invariance in this file is vacuous."
    )
