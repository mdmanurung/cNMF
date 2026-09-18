"""Reading the evidence back, with the one guard the schema cannot express.

`RESULTS.tsv` is tidy and invites `groupby(metric).mean()`. Across outer folds that
returns a meaningless number, because each fold refits its own gene panel and its own
per-gene scale: PROTOCOL §3.2 requires `G` to be "computed on training donors only,
frozen for the fold", so two folds are not measuring on a common axis.

Measured on the skeleton's SMOKE run: `Jaccard(G_0, G_1) = 0.639` — the folds shared 78
of 100 genes and had different `s_g`. Nothing in the 19 columns flags it.

The information needed to catch this is already recorded: `preprocessing_hash` includes
the hash of the fold's gene list, so it differs whenever the axes differ. What was missing
was anything that *used* it. That is all this module is.
"""
import csv

__all__ = ["PoolingError", "load_rows", "assert_poolable", "pooling_groups"]


class PoolingError(ValueError):
    """Rows that are not on a common measurement axis were about to be aggregated."""


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _preprocessing_by_experiment(experiments):
    """The identity a row must share to be poolable: **both** hashes, as a pair.

    `preprocessing_hash` alone is not enough, and the gap was not hypothetical. Feature B
    changes which cells reach `cnmf.prepare`, and `prepare` computes the per-gene scale
    `s_g` internally from exactly those cells — but `preprocessing_hash` carries `s_g_ddof`
    and **not** `s_g`, so both B arms hash identically. Measured: all four SMOKE
    configurations share `c9ba55b825846b53205c1816` at `outer_0`, while their scales differ
    by a median factor of 1.04 and up to 1.24. This function's own docstring promised to
    separate rows fitted on "different gene panels and per-gene scales"; on the scale half
    it was letting exactly that pooling through.

    `discovery_cells_hash` closes it without touching any hash formula. It is already a
    column, it already differs precisely when the arms differ, and it is **upstream** of
    `s_g` — the same cells deterministically give the same scale — so it is a stricter key
    than `s_g` would be, and it needs no quantization to survive BLAS noise on a replay.
    Adding `s_g` to `preprocessing_hash` instead would have versioned the guard, leaving
    older rows hashed under one formula and newer rows under another. See D016.
    """
    return {
        e["experiment_id"]: (e["preprocessing_hash"], e.get("discovery_cells_hash", ""))
        for e in experiments
    }


def assert_poolable(rows, experiments):
    """Raise unless every row shares one `(preprocessing_hash, discovery_cells_hash)`.

    Call this before any aggregation that crosses rows. It is deliberately strict: a
    caller that genuinely wants a cross-fold summary should say so by aggregating the
    groups from `pooling_groups` separately and reporting them separately, not by
    silencing a check.
    """
    lookup = _preprocessing_by_experiment(experiments)
    missing = sorted({r["experiment_id"] for r in rows} - set(lookup))
    if missing:
        raise PoolingError(
            f"{len(missing)} row(s) reference an experiment_id absent from EXPERIMENTS.tsv, "
            f"first {missing[0]}. Provenance cannot be checked, so pooling is refused."
        )
    hashes = {lookup[r["experiment_id"]] for r in rows}
    if len(hashes) > 1:
        n_pre = len({h[0] for h in hashes})
        detail = (
            f"{n_pre} distinct preprocessing_hash values"
            if n_pre > 1
            else "one preprocessing_hash but two or more discovery_cells_hash values, so "
            "they were fitted on the same gene panel from DIFFERENT CELLS and therefore on "
            "different per-gene scales"
        )
        raise PoolingError(
            f"rows span {detail}, so they are not on a common axis. Averaging them produces "
            "a number that describes no measurement. Aggregate within each group instead — "
            "see pooling_groups()."
        )
    return True


def pooling_groups(rows, experiments):
    """Partition rows into groups that *are* on a common axis, keyed by the
    `(preprocessing_hash, discovery_cells_hash)` pair. Aggregate within a group; report
    groups side by side. Two B arms land in different groups even though their gene panel
    is deliberately identical, because their per-gene scales are not."""
    lookup = _preprocessing_by_experiment(experiments)
    groups = {}
    for r in rows:
        groups.setdefault(lookup.get(r["experiment_id"], "UNKNOWN"), []).append(r)
    return groups


# ---------------------------------------------------------------- the feasibility gate

PRIMARY_LOSS = "heldout_squared_prediction_error_v1"


def feasibility_verdict(rows, diagnostics, k_true, k_max):
    """Evaluate the three pre-registered criteria. **Does not choose a rank.**

    The criteria and their thresholds are fixed in
    `registry/p0-03_development_feasibility_PREREGISTRATION.md`, committed before the run
    that this evaluates. They are reproduced here as constants rather than parameters so
    that calling this function cannot quietly change them.

    Note what this returns and what it does not: a GO/NO-GO on whether a usable K-curve
    *exists*. It never reports which K minimises error. `delta` is null, §2 requires the
    selector to refuse, and `000` is a fixed-rank configuration — a "winning K" recorded
    on an A-OFF row would be the baseline selector under another name.
    """
    import numpy as np

    per_donor = {}
    for r in rows:
        if r["metric"] != PRIMARY_LOSS or r["evaluation_scope"] != "per_donor":
            continue
        per_donor.setdefault(int(r["candidate_rank"]), {})[r["independent_unit_id"]] = float(
            r["value"]
        )
    missing = {k_true, k_max} - set(per_donor)
    if missing:
        raise ValueError(f"no per-donor rows at rank(s) {sorted(missing)}")

    # Criterion 1 — paired per donor. Pairing within a donor cancels the fold's gene
    # panel and per-gene scale, so donors from different folds are comparable in the
    # DIFFERENCE even though their levels are not. Donors are the independent unit (§3.5).
    shared = sorted(set(per_donor[k_true]) & set(per_donor[k_max]))
    diffs = np.array([per_donor[k_max][d] - per_donor[k_true][d] for d in shared])
    if len(diffs) < 2:
        raise ValueError(f"need at least 2 paired donors, got {len(diffs)}")
    se = float(diffs.std(ddof=1) / np.sqrt(len(diffs)))
    mean_diff = float(diffs.mean())
    # A zero-variance difference is the STRONGEST evidence of curve structure, not the
    # absence of it: every donor moved by the same amount. Treating se == 0 as a failure
    # (an earlier version did) inverts the criterion exactly where it is most decisive.
    c1 = bool(mean_diff > 0) if se == 0 else bool(mean_diff > 3 * se)

    # Criteria 2 and 3 are per fold; a single failing fold fails the run.
    folds = []
    for d in diagnostics:
        floor = d["poisson_error_floor_per_cell"]
        obs = {k: _fold_mean(rows, d["outer_split_id"], k) for k in (k_true, k_max)}
        ratio_true, ratio_max = obs[k_true] / floor, obs[k_max] / floor
        sil_range = d["silhouette_dynamic_range"]
        folds.append({
            "outer_split_id": d["outer_split_id"],
            "poisson_floor_per_cell": floor,
            f"observed_k{k_true}": obs[k_true], f"observed_k{k_max}": obs[k_max],
            "ratio_k_true": ratio_true, "ratio_k_max": ratio_max,
            # Fail only if BOTH ends sit on the floor: one end near it is fine, both
            # means there is no signal left anywhere on the curve.
            "criterion_2_not_flat": bool(not (ratio_true < 1.02 and ratio_max < 1.02)),
            "silhouette_dynamic_range": sil_range,
            "criterion_3_not_degenerate": bool(sil_range > 1e-6),
        })

    c2 = all(f["criterion_2_not_flat"] for f in folds)
    c3 = all(f["criterion_3_not_degenerate"] for f in folds)
    return {
        "k_true": k_true, "k_max": k_max, "n_paired_donors": len(shared),
        "mean_paired_difference": mean_diff, "paired_se": se,
        "paired_t": (mean_diff / se) if se > 0 else float("inf" if mean_diff > 0 else "nan"),
        "criterion_1_curve_structure": c1,
        "criterion_2_not_flat_by_arithmetic": c2,
        "criterion_3_silhouette_not_degenerate": c3,
        "verdict": "GO" if (c1 and c2 and c3) else "NO-GO",
        "folds": folds,
    }


def _fold_mean(rows, outer_split_id, k):
    """Returns the FIRST matching row, so `rows` must come from a single run.

    `verdict_for_run` only ever hands it one run's own shard, which is why this is safe today.
    Handed the tracked `RESULTS.tsv` it would not be: that file now holds two DEVELOPMENT runs
    whose `outer_split_id` and `candidate_rank` are identical, and this would silently take
    whichever appears first. Use `assert_poolable` before aggregating anything that crosses
    runs.
    """
    for r in rows:
        if (r["metric"] == PRIMARY_LOSS and r["evaluation_scope"] == "equal_donor_mean"
                and r["outer_split_id"] == outer_split_id and r["candidate_rank"] == str(k)):
            return float(r["value"])
    raise ValueError(f"no equal_donor_mean row for {outer_split_id} at k={k}")


def verdict_for_run(run_dir):
    """Evaluate a completed run's own shards. `K_true` comes from the dataset manifest and
    `K_max` from the grid that was actually run, so neither is chosen by the caller."""
    import json
    import os

    rows = load_rows(os.path.join(run_dir, "results.tsv"))
    with open(os.path.join(run_dir, "diagnostics.json"), encoding="utf-8") as fh:
        diagnostics = json.load(fh)
    with open(os.path.join(run_dir, "dataset", "manifest.json"), encoding="utf-8") as fh:
        params = json.load(fh)["parameters"]
    k_true = params["n_identity"] + params["n_activity"]
    k_max = max(int(r["candidate_rank"]) for r in rows if r["candidate_rank"])
    return feasibility_verdict(rows, diagnostics, k_true, k_max)


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Evaluate the pre-registered feasibility criteria.")
    ap.add_argument("run_dir")
    args = ap.parse_args()
    print(json.dumps(verdict_for_run(args.run_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
