"""P4-03 comparator scoring: gene-set Jaccard for GeneNMF MPs and cNMF top-50.

Reads (all pre-existing or R-produced, nothing refit here):
- truth marker sets from each scenario's dataset truth.npz,
- GeneNMF MP gene lists from results/scratch/genenmf_<scen>/out/mp_genes.csv,
- cNMF consensus spectra at K_true=7 from the rep0 000 runs' fold dirs.

Writes docs/benchmarks/registry/p4-03_comparator.tsv (tracked report, not
benchmark rows — comparator evidence lives outside RESULTS.tsv by design).
"""
import csv
import glob
import json
import os

import numpy as np
import pandas as pd

from cnmfbench.recovery import TOP_GENES_N, recovery_jaccard, top_genes

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRATCH = os.path.join(REPO, "results/scratch")
RUNS = os.path.join(REPO, "results/exploratory")
OUT = os.path.join(REPO, "docs/benchmarks/registry/p4-03_comparator.tsv")

SCENARIOS = {
    "B_imbalanced": "p2-04-development-000B-imbalanced-rep0",
    "B_balanced": "p2-04-development-000B-balanced-rep0",
    "B_context": "p2-04-development-000B-context-rep0",
}
K_TRUE = 7


def truth_markers(scen):
    for run in (SCENARIOS[scen],):
        truth = np.load(os.path.join(RUNS, run, "dataset", "truth.npz"),
                        allow_pickle=True)
        genes = [str(g) for g in truth["gene_ids"]]
        mask = np.asarray(truth["marker_mask"], dtype=bool)
        # Same separator normalization as the fitted sides (Seurat rewrites
        # gene_00001 -> gene-00001; §5.5 compares on names, not separators).
        return [frozenset(g.replace("_", "-") for g in np.array(genes)[mask[k]].tolist())
                for k in range(mask.shape[0])]


def cnmf_top50(scen):
    rundir = os.path.join(RUNS, SCENARIOS[scen])
    sets = []
    for fold in ("outer_0", "outer_1"):
        matches = glob.glob(os.path.join(
            rundir, fold, fold, f"{fold}.spectra.k_{K_TRUE}.dt_2_0.consensus.txt"))
        assert len(matches) == 1, (scen, fold, matches)
        df = pd.read_csv(matches[0], sep="\t", index_col=0)
        # Seurat rewrites gene_00001 -> gene-00001 on the R side; normalize the
        # cNMF side identically so the comparison is on names, not separators.
        labels = [c.replace("_", "-") for c in df.columns]
        sets.append((fold, top_genes(df.values, tuple(df.columns), n=TOP_GENES_N)))
    # Union per fold would double-count; score per fold and average (donors are
    # the unit, folds are not pooled — same rule as everywhere else).
    normed = []
    for fold, fold_sets in sets:
        normed.append((fold, [{g.replace("_", "-") for g in s} for s in fold_sets]))
    return normed


def genenmf_mps(scen):
    path = os.path.join(SCRATCH, f"genenmf_{scen}", "out", "mp_genes.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    out = []
    for r in rows:
        genes = [g for g in r["genes"].split(",") if g]
        out.append(frozenset(genes))
    return out


rows = [("scenario", "side", "fold", "score", "n_true", "n_fitted", "detail")]
for scen in SCENARIOS:
    truth = truth_markers(scen)
    mp_sets = genenmf_mps(scen)
    score, matching, matched = recovery_jaccard(truth, mp_sets)
    rows.append((scen, "genenmf", "pooled", f"{score:.4f}", str(len(truth)),
                 str(len(mp_sets)),
                 "matched=" + ",".join(f"{m:.3f}" for m in matched)))
    for fold, fold_sets in cnmf_top50(scen):
        score, matching, matched = recovery_jaccard(truth, fold_sets)
        rows.append((scen, "cnmf_top50_k7", fold, f"{score:.4f}", str(len(truth)),
                     str(len(fold_sets)),
                     "matched=" + ",".join(f"{m:.3f}" for m in matched)))

with open(OUT, "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t")
    w.writerows(rows)
print("wrote", OUT, len(rows) - 1, "comparisons")
