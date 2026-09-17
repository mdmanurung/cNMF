"""The walking skeleton: the first end-to-end run that produces benchmark rows.

Configuration `000`, SMOKE tier, fixed rank across the candidate grid, driving the **real
pinned cNMF**. No feature switches, no rank selection, none of the P0-04 metrics.

Two structural choices carry most of the correctness:

**Training-only input.** Each fold writes an `.h5ad` containing only its training donors'
cells and runs cNMF on that. This is not an optimisation — PROTOCOL §3.3 requires it,
because `consensus()` refits usages against every cell present in the files it reads
(`cnmf.py:961-975`). With training-only inputs, `test_spectra_refit: forbidden` holds by
construction rather than by enforcement, and held-out cells never enter cNMF at all.

**One `prepare` per fold covering every candidate rank.** A second `prepare` in the same
directory overwrites `norm_counts.h5ad`, `tpm.h5ad` and `nmf_genes_list` while the
k-specific files survive, so a later read of the gene list would silently return another
fold's `G`. Preparing once also makes §4.1's "panels identical across all candidate ranks"
true by construction instead of by assertion.

WHAT THIS RUNNER MUST NEVER DO
------------------------------
Record which K won. Measured on this data, K=3 is the argmin of held-out loss in 10 of 10
(fold x panel-seed) cases, which makes it the most tempting number here. Any column, note
or diagnostic on an A-OFF row that names the winning rank **is the baseline selector under
another name**: it would be computed while `delta` is null (§2 requires refusal), derived
from outer-test outcomes (§1.5 forbids it), on an arm where §5.3 makes `selected_rank`
null by design. Emit the complete fixed-rank curve and stop.
"""
import argparse
import csv
import json
import os
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import yaml

from . import UPSTREAM_CNMF_SHA
from .contract import ContractViolation
from .hashing import cell_set_hash, artifact_hash
from .io import write_dataset
from .provisional import provisional, touched
from .records import (
    ARM, EXPERIMENTS_COLUMNS, NOT_COMPUTED, RESULTS_COLUMNS, contract_hash,
    environment_hash, experiment_row, implementation_sha, make_experiment_id,
    preprocessing_hash, protocol_hash, result_row, write_rows,
)
from .scenarios import build_params, seed_for
from .scoring import (
    count_unit_error, equal_donor_mean, null_dictionary, nnls_usages, scoreable_mask,
    squared_prediction_error, to_training_scale, training_gene_scale,
)
from .simulate import simulate
from .splits import gene_panel, outer_donor_folds

ARM_ID = "full_training_pool"
CONFIGURATION = "000"


def _utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _peak_mb():
    # ru_maxrss is a process LIFETIME high-water mark, so successive rows are monotone
    # non-decreasing. memory_scope says so rather than implying a per-experiment peak.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def check_preconditions(cfg, ablation):
    """Refuse rather than warn. Each of these silently changes what the rows mean."""
    root = _repo_root()

    recorded = ablation["protocol"]["sha256"]
    actual = protocol_hash()
    if recorded != actual:
        raise ContractViolation(
            f"PROTOCOL.md hash {actual} != {recorded} recorded in ablation_plan.yaml. "
            "The frozen rules are not the rules on disk."
        )

    diff = subprocess.run(
        ["git", "-C", root, "diff", UPSTREAM_CNMF_SHA, "--", "src/"],
        capture_output=True, text=True, check=True,
    ).stdout
    if diff.strip():
        raise ContractViolation(
            "src/cnmf/** differs from the pinned upstream SHA. The whole programme rests "
            "on the algorithm being unmodified."
        )

    if cfg["evidence_tier"] != "SMOKE" or cfg.get("allow_scientific_promotion") is not False:
        raise ContractViolation("this runner only writes SMOKE rows that cannot promote a feature")
    if ablation["scientific_gates"]["smoke_can_promote_feature"] is not False:
        raise ContractViolation("smoke_can_promote_feature must be false")
    if any(cfg["features"].values()):
        raise ContractViolation(f"features must all be off for {CONFIGURATION}: {cfg['features']}")
    if CONFIGURATION not in ablation["matched_budget_factorial"]["fixed_rank_configurations"]:
        raise ContractViolation(f"{CONFIGURATION} is not a fixed-rank configuration")

    if cfg["factorization"]["optimizer_starts"] < 4:
        raise ContractViolation(
            "optimizer_starts < 4 makes n_neighbors = int(0.30*n_iter) zero, so "
            "local_density divides by zero and consensus() dies reporting a threshold "
            "problem that raising the threshold cannot fix"
        )
    if cfg["factorization"]["num_highvar_genes"] >= cfg["simulation"]["genes"]:
        raise ContractViolation("num_highvar_genes must be below the gene count or HVG selection is a no-op")

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        if os.environ.get(var) != "1":
            raise ContractViolation(
                f"{var} is not 1; cpu_seconds_v1 would measure uncontrolled BLAS threading"
            )

    # The config duplicates the tier shape that scenarios.py defines. They agree today and
    # nothing keeps them agreeing, so divergence must stop the run rather than pick one.
    params = build_params(cfg["scenario"], cfg["evidence_tier"])
    sim = cfg["simulation"]
    for key, got, want in (
        ("donors", sim["donors"], params.n_donors),
        ("cells_per_donor", sim["cells_per_donor"], params.cells_per_donor),
        ("genes", sim["genes"], params.n_genes),
        ("true_programs", sim["true_programs"], params.k_true),
    ):
        if got != want:
            raise ContractViolation(
                f"config simulation.{key}={got} but scenarios.py gives {want}. Two sources "
                "of truth for the same number have diverged."
            )
    return params


def verify_transform_matches_cnmf(raw_train_on_g, norm_counts_x, s_g, tol=1e-5):
    """Assert the harness's `s_g` is the divisor cNMF actually used.

    If these disagree, the held-out transform is in different units from the dictionary,
    every prediction error is wrong by a per-gene factor, and **nothing crashes**.

    On this path they agree by construction: `compute_tpm` copies the input (`cnmf.py:249`)
    so density follows the input, the simulator writes a dense integer `X`, and the dense
    branch is literally `std(axis=0, ddof=1)` (`cnmf.py:542`). The check exists because
    that is a *branch condition on an input property* — switching the simulator to sparse
    output silently takes the other branch.

    Deliberately not `tpm_stats.__std`, which is `ddof=0`, computed on TPM, over all genes
    (`cnmf.py:436-440`) — a different quantity that would appear to work.
    """
    ours = to_training_scale(raw_train_on_g, s_g)
    theirs = np.asarray(norm_counts_x, dtype=np.float64)
    denom = np.sqrt((theirs**2).sum())
    rel = np.sqrt(((ours - theirs) ** 2).sum()) / denom if denom > 0 else float("nan")
    if not (rel < tol):
        raise ContractViolation(
            f"harness transform differs from cNMF's norm_counts by relative Frobenius "
            f"{rel:.3e} (tolerance {tol:.0e}, D004). Every value this run would write is "
            "on the wrong scale."
        )
    return rel


@provisional("skeleton.run")
def run(config_path, out_root, run_id=None, dry_run=False):
    """One end-to-end SMOKE run. Returns a summary dict; writes shards, not tracked TSVs."""
    root = _repo_root()
    with open(config_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    with open(os.path.join(root, "docs/benchmarks/configs/ablation_plan.yaml"), encoding="utf-8") as fh:
        ablation = yaml.safe_load(fh)

    params = check_preconditions(cfg, ablation)
    run_id = run_id or f"p0skel-{CONFIGURATION}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    run_dir = os.path.join(out_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # /home is 96% full (B003); keep every cache off it.
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(run_dir, ".mpl"))
    os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(run_dir, ".numba"))

    tier = cfg["evidence_tier"]
    scenario = cfg["scenario"]
    replicate = 0
    dataset_id = f"{scenario}_{tier}_r{replicate}"
    ds = simulate(params, scenario, tier, seed_for(tier), simulation_replicate=replicate)
    write_dataset(ds, os.path.join(run_dir, "dataset"))

    if dry_run:
        return {"run_id": run_id, "run_dir": run_dir, "dry_run": True,
                "dataset_manifest_hash": ds.dataset_manifest_hash}

    adata = ds.adata
    donors = np.asarray([str(d) for d in adata.obs["donor_id"]])
    raw = np.asarray(adata.X, dtype=np.float64)
    gene_names = list(adata.var_names)
    ranks = list(cfg["factorization"]["candidate_ranks"])
    density_threshold = cfg["factorization"]["density_threshold"]

    folds = outer_donor_folds(donors, cfg["validation"]["outer_donor_folds"], cfg["seed"])
    results, experiments, diagnostics = [], [], []

    provenance_common = dict(
        protocol_hash=protocol_hash(),
        contract_hash=contract_hash(ablation),
        upstream_sha=UPSTREAM_CNMF_SHA,
        implementation_sha_or_patch_hash=implementation_sha(),
        environment_hash=environment_hash(),
    )

    for fold in folds:
        fold_dir = os.path.join(run_dir, fold.outer_split_id)
        try:
            fold_out = _run_fold(
                fold, adata, raw, donors, gene_names, ranks, cfg, params, ds,
                fold_dir, dataset_id, provenance_common, density_threshold,
            )
        except Exception as exc:  # noqa: BLE001 — a failed fold must not lose the others
            experiments.append(_failed_experiment_row(
                fold, dataset_id, ds, cfg, fold_dir, provenance_common, exc,
            ))
            results.append(result_row(
                experiment_id=make_experiment_id(CONFIGURATION, ARM_ID, dataset_id,
                                                 fold.outer_split_id, None,
                                                 {"seed": cfg["seed"]}),
                configuration=CONFIGURATION, arm=ARM_ID, dataset_id=dataset_id,
                independent_unit_id=fold.outer_split_id, independent_unit_type="experiment",
                outer_split_id=fold.outer_split_id, metric="failed_fits_v1",
                value=len(ranks), evaluation_scope="experiment", candidate_rank="",
                n_eligible_units=len(ranks), n_failed_units=len(ranks),
                status="fit_failed", artifact_path=os.path.relpath(fold_dir, root),
            ))
            continue
        results.extend(fold_out["results"])
        experiments.extend(fold_out["experiments"])
        diagnostics.extend(fold_out["diagnostics"])

    write_rows(os.path.join(run_dir, "results.tsv"), results, RESULTS_COLUMNS)
    write_rows(os.path.join(run_dir, "experiments.tsv"), experiments, EXPERIMENTS_COLUMNS)
    with open(os.path.join(run_dir, "diagnostics.json"), "w", encoding="utf-8") as fh:
        json.dump(diagnostics, fh, indent=2, sort_keys=True)

    return {
        "run_id": run_id, "run_dir": run_dir,
        "n_results": len(results), "n_experiments": len(experiments),
        "provisional_components": touched(),
        "dataset_manifest_hash": ds.dataset_manifest_hash,
    }


def _failed_experiment_row(fold, dataset_id, ds, cfg, fold_dir, prov, exc):
    now = _utc()
    return experiment_row(
        experiment_id=make_experiment_id(CONFIGURATION, ARM_ID, dataset_id,
                                         fold.outer_split_id, None, {"seed": cfg["seed"]}),
        prototype="true", feature_A="false", feature_B="false", feature_C="false",
        arm=ARM_ID, status="failed", evidence_tier=cfg["evidence_tier"],
        dataset_id=dataset_id, dataset_manifest_hash=ds.dataset_manifest_hash,
        simulation_replicate=0, outer_split_id=fold.outer_split_id, inner_split_id="",
        mask_id=NOT_COMPUTED, sampling_replicate=0, optimizer_seed=cfg["seed"],
        candidate_rank="", selected_rank=None, artifact_dir=os.path.relpath(fold_dir, _repo_root()),
        command=" ".join(sys.argv), started_utc=now, finished_utc=now, exit_code=1,
        wall_seconds=NOT_COMPUTED, cpu_seconds=NOT_COMPUTED, peak_memory_mb=NOT_COMPUTED,
        memory_scope="parent_process_peak_rss_lifetime",
        failure_reason=f"{type(exc).__name__}: {exc}".replace("\t", " ").replace("\n", " ")[:400],
        notes=f"provisional={','.join(touched())}",
        discovery_cells_hash=NOT_COMPUTED, factor_bank_hash=NOT_COMPUTED,
        preprocessing_hash=NOT_COMPUTED, **prov,
    )


def _run_fold(fold, adata, raw, donors, gene_names, ranks, cfg, params, ds,
              fold_dir, dataset_id, prov, density_threshold):
    """One outer fold: fit on training donors only, then score every candidate rank."""
    from cnmf import cNMF
    from cnmf.cnmf import load_df_from_npz

    root = _repo_root()
    os.makedirs(fold_dir, exist_ok=True)
    is_train = np.isin(donors, np.asarray(fold.train_donors))
    train_ids = [str(c) for c in adata.obs_names[is_train]]

    # PROTOCOL §3.3: cNMF sees training cells and nothing else.
    train_path = os.path.join(fold_dir, "train_counts.h5ad")
    adata[is_train].copy().write_h5ad(train_path)

    started, t0, c0 = _utc(), time.perf_counter(), time.process_time()
    obj = cNMF(output_dir=fold_dir, name=fold.outer_split_id)
    obj.prepare(
        counts_fn=train_path, components=ranks,
        n_iter=cfg["factorization"]["optimizer_starts"],
        num_highvar_genes=cfg["factorization"]["num_highvar_genes"],
        seed=cfg["seed"], beta_loss=cfg["factorization"]["loss"],
        max_NMF_iter=cfg["factorization"]["max_optimizer_iterations"],
    )
    obj.factorize(worker_i=0, total_workers=1)
    obj.combine()
    fit_wall, fit_cpu = time.perf_counter() - t0, time.process_time() - c0

    # `G` in cNMF's own order. Written with '\n'.join and no trailing newline; rstrip
    # guards a future upstream change, since a trailing newline injects an empty label.
    with open(obj.paths["nmf_genes_list"], encoding="utf-8") as fh:
        g_list = fh.read().rstrip("\n").split("\n")
    g_pos = np.array([gene_names.index(g) for g in g_list])

    s_g = training_gene_scale(raw[np.ix_(np.flatnonzero(is_train), g_pos)])

    import anndata as ad
    norm = ad.read_h5ad(obj.paths["normalized_counts"])
    if list(norm.var_names) != g_list:
        raise ContractViolation("norm_counts gene order differs from nmf_genes_list")
    transform_rel_error = verify_transform_matches_cnmf(
        raw[np.ix_(np.flatnonzero(is_train), g_pos)], np.asarray(norm.X), s_g
    )

    panel = gene_panel(g_list, cfg["validation"]["inference_gene_fraction"],
                       cfg["validation"]["panel_seed"])
    inf_pos = np.array([g_list.index(g) for g in panel.inference_genes])
    val_pos = np.array([g_list.index(g) for g in panel.validation_genes])

    pre_hash = preprocessing_hash({
        "gene_panel_G": cell_set_hash(g_list),
        "num_highvar_genes": cfg["factorization"]["num_highvar_genes"],
        "s_g_ddof": 1, "transform": "training_fitted_and_leakage_audited",
        "inference_gene_fraction": cfg["validation"]["inference_gene_fraction"],
        "panel_seed": cfg["validation"]["panel_seed"], "mask_id": panel.mask_id,
        "nnls_solver": "scipy.optimize.nnls",
        "density_threshold": density_threshold,
        "n_iter": cfg["factorization"]["optimizer_starts"],
        "max_NMF_iter": cfg["factorization"]["max_optimizer_iterations"],
        "beta_loss": cfg["factorization"]["loss"],
    })
    discovery_hash = cell_set_hash(train_ids)

    # Held-out cells, transformed with the TRAINING scale and never refitted.
    test_rows = np.flatnonzero(~is_train)
    raw_test_g = raw[np.ix_(test_rows, g_pos)]
    x_test = to_training_scale(raw_test_g, s_g)
    keep = scoreable_mask(raw_test_g[:, inf_pos])
    x_test, test_donors = x_test[keep], donors[test_rows][keep]
    n_excluded = int((~keep).sum())

    x_train_scaled = to_training_scale(raw[np.ix_(np.flatnonzero(is_train), g_pos)], s_g)
    null_v = null_dictionary(x_train_scaled)  # scaled, not raw — a 4x error if confused

    diagnostics = [_fold_diagnostics(fold, ds, g_list, g_pos, panel, s_g, obj, ranks,
                                     density_threshold, transform_rel_error, n_excluded,
                                     norm, x_test, inf_pos, val_pos, test_rows[keep])]
    results, experiments = [], []

    for k in ranks:
        t1, c1 = time.perf_counter(), time.process_time()
        obj.consensus(k=k, density_threshold=density_threshold,
                      show_clustering=False, build_ref=False)
        dt_repl = str(density_threshold).replace(".", "_")
        v = load_df_from_npz(obj.paths["consensus_spectra"] % (k, dt_repl))
        if list(v.columns) != g_list:
            raise ContractViolation("consensus_spectra gene order differs from G")
        v_arr = v.values.astype(np.float64)  # median_spectra: K x |G|, rows sum to 1

        u = nnls_usages(x_test[:, inf_pos], v_arr[:, inf_pos])
        loss_train_scale = squared_prediction_error(x_test[:, val_pos], u, v_arr[:, val_pos])
        loss_counts = count_unit_error(x_test[:, val_pos], u, v_arr[:, val_pos], s_g[val_pos])
        u_null = nnls_usages(x_test[:, inf_pos], null_v[:, inf_pos])
        loss_null = squared_prediction_error(x_test[:, val_pos], u_null, null_v[:, val_pos])
        wall, cpu = time.perf_counter() - t1, time.process_time() - c1

        exp_id = make_experiment_id(CONFIGURATION, ARM_ID, dataset_id, fold.outer_split_id, k,
                                    {"seed": cfg["seed"],
                                     "panel_seed": cfg["validation"]["panel_seed"]})
        artifact = os.path.relpath(obj.paths["consensus_spectra"] % (k, dt_repl), root)
        common = dict(experiment_id=exp_id, configuration=CONFIGURATION, arm=ARM_ID,
                      dataset_id=dataset_id, outer_split_id=fold.outer_split_id,
                      candidate_rank=k, status="ok_provisional", artifact_path=artifact)

        for metric, per_cell in (
            ("heldout_squared_prediction_error_v1", loss_train_scale),
            ("heldout_squared_prediction_error_counts_v1", loss_counts),
            ("null_squared_prediction_error_v1", loss_null),
        ):
            agg = equal_donor_mean(per_cell, test_donors)
            for donor, val in sorted(agg.per_donor.items()):
                n_cells = int((test_donors == donor).sum())
                results.append(result_row(
                    **common, independent_unit_id=donor, independent_unit_type="donor",
                    metric=metric, value=repr(val), evaluation_scope="per_donor",
                    n_eligible_units=n_cells, n_failed_units=0,
                ))
            results.append(result_row(
                **common, independent_unit_id="ALL_TEST_DONORS",
                independent_unit_type="donor", metric=metric, value=repr(agg.value),
                evaluation_scope="equal_donor_mean",
                n_eligible_units=agg.n_eligible_donors, n_failed_units=agg.n_failed_donors,
            ))

        for metric, val in (("wall_seconds_v1", wall), ("cpu_seconds_v1", cpu),
                            ("peak_memory_mb_v1", _peak_mb()), ("failed_fits_v1", 0)):
            results.append(result_row(
                **common, independent_unit_id=exp_id, independent_unit_type="experiment",
                metric=metric, value=repr(float(val)) if metric != "failed_fits_v1" else 0,
                evaluation_scope="experiment", n_eligible_units=1, n_failed_units=0,
            ))

        experiments.append(experiment_row(
            experiment_id=exp_id, prototype="true", feature_A="false", feature_B="false",
            feature_C="false", arm=ARM_ID, status="completed",
            evidence_tier=cfg["evidence_tier"], dataset_id=dataset_id,
            dataset_manifest_hash=ds.dataset_manifest_hash, simulation_replicate=0,
            outer_split_id=fold.outer_split_id, inner_split_id="", mask_id=panel.mask_id,
            sampling_replicate=0, optimizer_seed=cfg["seed"], candidate_rank=k,
            selected_rank=None, discovery_cells_hash=discovery_hash,
            factor_bank_hash=artifact_hash(obj.paths["merged_spectra"] % k),
            preprocessing_hash=pre_hash,
            artifact_dir=os.path.relpath(fold_dir, root), command=" ".join(sys.argv),
            started_utc=started, finished_utc=_utc(), exit_code=0,
            wall_seconds=repr(wall + fit_wall / len(ranks)),
            cpu_seconds=repr(cpu + fit_cpu / len(ranks)),
            peak_memory_mb=repr(_peak_mb()),
            memory_scope="parent_process_peak_rss_lifetime", failure_reason="",
            notes=(f"provisional={','.join(touched())}; arm=full_training_pool_no_cell_budget; "
                   f"density_threshold={density_threshold}; fit cost shared across "
                   f"{len(ranks)} ranks from one prepare/factorize/combine"),
            **prov,
        ))

    return {"results": results, "experiments": experiments, "diagnostics": diagnostics}


def _fold_diagnostics(fold, ds, g_list, g_pos, panel, s_g, obj, ranks, density_threshold,
                      transform_rel_error, n_excluded, norm, x_test, inf_pos, val_pos,
                      scored_cell_rows):
    """The three deferred checks plus the carrier count, all as labelled diagnostics.

    None of these may enter `RESULTS.tsv`: `silhouette`, `hvg_retention` and
    `poisson_error_floor` are not among §5.2's 11 permitted metric names, and §5.1 forbids
    writing a name not on that list.
    """
    from .diagnostics import hvg_retention, poisson_error_floor

    # `poisson_error_floor` indexes `lam[np.ix_(cells, genes)]` and `gene_std[genes]`, so
    # BOTH must be on the FULL gene axis. Passing the |G|-length `s_g` with full-axis gene
    # indices returns a silently wrong-scale number, so the scatter is explicit here.
    s_g_full = np.full(ds.adata.n_vars, np.nan)
    s_g_full[g_pos] = s_g
    val_full = g_pos[val_pos]
    error_floor = poisson_error_floor(ds.expected_counts, s_g_full, scored_cell_rows, val_full)

    sil = {}
    for k in ranks:
        stats = obj.consensus(k=k, density_threshold=density_threshold,
                              show_clustering=False,
                              skip_density_and_return_after_stats=True)
        sil[k] = float(np.asarray(stats).ravel()[2])  # k, local_density_threshold, silhouette, error
    sil_range = max(sil.values()) - min(sil.values())

    # §1.5 permits reading true structure as an explicitly labelled diagnostic, never as
    # an input to a split or a fit. Recorded because the carrier split is asymmetric by
    # construction at this seed and would otherwise be misread as a scorer bug.
    train_idx = [i for i, d in enumerate(sorted(set(str(x) for x in ds.adata.obs["donor_id"])))
                 if d in set(fold.train_donors)]
    carriers = ds.donor_eligibility[train_idx].sum(axis=0).tolist()

    ident = np.linalg.svd(np.asarray(norm.X)[:, inf_pos], compute_uv=False)
    return {
        "outer_split_id": fold.outer_split_id,
        "train_donors": list(fold.train_donors),
        "n_genes_G": len(g_list),
        "mask_id": panel.mask_id,
        "n_inference_genes": len(panel.inference_genes),
        "n_validation_genes": len(panel.validation_genes),
        "transform_rel_frobenius_vs_cnmf": transform_rel_error,
        "s_g_min": float(s_g.min()), "s_g_max": float(s_g.max()),
        "silhouette_by_k": sil,
        "silhouette_dynamic_range": sil_range,
        "degenerate_branch_would_fire": bool(sil_range < 1e-6),
        "hvg_retention_per_program": hvg_retention(ds, g_pos),
        # Summed over scored cells; divide by n_donors-weighted cells to compare against
        # an equal_donor_mean value. Reported raw so the comparison is explicit.
        "poisson_error_floor_total": error_floor,
        "poisson_error_floor_per_cell": error_floor / max(len(scored_cell_rows), 1),
        "n_training_carriers_per_identity_program": carriers,
        "n_cells_excluded_zero_inference_counts": n_excluded,
        "n_test_cells_scored": int(x_test.shape[0]),
        "inference_panel_min_singular_value": float(ident.min()),
        "inference_panel_condition_number": float(ident.max() / ident.min()),
    }


def merge(run_dir):
    """Promote one run's shards into the tracked TSVs.

    Deliberately a separate command. A run writes only into its own directory, so a crash
    or an interrupted fold leaves version-controlled evidence untouched, and promoting it
    is an act someone chose to take.
    """
    from .records import merge_into_tracked

    root = _repo_root()
    counts = {}
    for shard, tracked, columns in (
        ("results.tsv", "docs/benchmarks/RESULTS.tsv", RESULTS_COLUMNS),
        ("experiments.tsv", "docs/benchmarks/EXPERIMENTS.tsv", EXPERIMENTS_COLUMNS),
    ):
        with open(os.path.join(run_dir, shard), newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        counts[shard] = merge_into_tracked(os.path.join(root, tracked), rows, columns)
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="docs/benchmarks/configs/smoke.yaml")
    ap.add_argument("--out-root", default="results/exploratory")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--merge", metavar="RUN_DIR",
                    help="promote a completed run's shards into the tracked TSVs")
    args = ap.parse_args()
    if args.merge:
        print(json.dumps(merge(args.merge), indent=2, sort_keys=True))
        return 0
    summary = run(args.config, args.out_root, args.run_id, args.dry_run)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
