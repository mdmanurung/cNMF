#!/usr/bin/env python
"""P0-01 Risk 2 probe: is cNMF's consensus() output reproducible?

Background: cnmf.py get_nmf_iter_params() builds _nmf_kwargs with no `random_state`
and init='random'. refit_usage() reuses those kwargs with update_H=False, so the
usage matrix W initialises from numpy's GLOBAL RNG. consensus_usages,
gene_spectra_score and gene_spectra_tpm all derive from that refit.

Design: hold the factor bank FIXED (reuse upstream's reference merged_spectra, exactly
as tests/test_reproducibility.py does), then call consensus() N times under two
conditions:
  free   - no seeding between calls
  seeded - np.random.seed(SEED_BEFORE_CONSENSUS) immediately before each call

consensus_spectra comes from KMeans(random_state=1) UPSTREAM of the refit, so it is
expected stable in both conditions. If the refit-derived artifacts are unstable under
'free' but stable under 'seeded', global-RNG control is both the cause and the
harness-side remedy. Runs 0 vs 1 of 'free' being identical would instead indicate the
variation is not RNG-driven at all.

Writes a tidy TSV. Does not modify the cNMF package.

REVIEW FINDINGS (2026-09-16) — read before trusting or reusing this script
-------------------------------------------------------------------------
This file is kept byte-stable in BEHAVIOUR because `nondeterminism_probe.tsv` was
produced by it and is cited as evidence; the notes below are annotations, not fixes.
Any successor (P0-04 will need a similar harness) must fix 1 and 2 rather than copy them.

1. SILENT SKIP (snapshot(), ~line 95; comparison loop, ~line 147). If consensus() fails
   to write an artifact, snapshot() omits it with no warning and the comparison loop
   `continue`s past it. A partially failed run is indistinguishable from a clean one, and
   main() returns None so the exit code is 0 regardless. For the recorded run this did not
   bite: the TSV has 90 rows = 2 conditions x 9 comparisons x 5 artifacts, so every
   artifact was present every time. Verified, not assumed.

2. NO POSITIVE CONTROL. As written this script can only report a null, and a null from an
   instrument never shown to be sensitive is not evidence. Remedied separately rather than
   by editing this file: see `nondeterminism_positive_control.py` and its `.log`, which
   reuse this module's own compare() and snapshot() and establish that the chain detects a
   single-element relative perturbation of 1e-9 in all five artifacts.

3. "bitwise_identical" IS A LOOSE NAME (compare(), ~line 100). It is exact numeric equality
   of float64 arrays after load_df_from_npz + astype(float), not identity of the file bytes.
   For float64 npz round-trips with no NaN the two coincide, but text elsewhere should say
   "exactly equal" rather than "bitwise identical" where precision matters.

4. SCOPE. The reps run in ONE process, so this exercises global-RNG variation between calls
   (the actual Risk-2 mechanism) but not cross-process effects. Also, per the positive
   control's TEST 2, `consensus_spectra` is computed UPSTREAM of the refit and cannot move
   when the refit moves — its stability is evidence about KMeans(random_state=1), not about
   the unseeded refit. Only the four refit-derived artifacts bear on Risk 2.
"""
import argparse
import os
import shutil
import sys

import numpy as np
import pandas as pd

from cnmf import cNMF
from cnmf.cnmf import load_df_from_npz

# Hardcoded absolute path: this is a one-off P0-01 probe, kept in the registry as
# evidence rather than as a maintained tool. It will break if moved. When the
# harness gains workflow/scripts/ at P0-07, re-derive REPO from __file__ or take
# it as a CLI argument rather than copying this line.
REPO = "/exports/para-lipg-hpc/mdmanurung/cNMF"
REF_DIR = os.path.join(REPO, "tests/test_data/simulated_example_data")
COUNTS = os.path.join(REF_DIR, "filtered_counts.txt")
REF_NAME = "example_cNMF"

K_VALUES = [5, 6, 7]
N_ITER = 15
NHVG = 1000
PREPARE_SEED = 14
K = 7
DENSITY_THRESHOLD = 0.1
SEED_BEFORE_CONSENSUS = 12345

# consensus_spectra is pre-refit (KMeans random_state=1); the other three are refit-derived.
ARTIFACTS = [
    ("consensus_spectra", "pre_refit"),
    ("consensus_usages", "refit_derived"),
    ("gene_spectra_tpm", "refit_derived"),
    ("gene_spectra_score", "refit_derived"),
    ("starcat_spectra", "refit_derived"),
]


def build_fixed_factor_bank(workdir):
    """prepare() once, then copy in upstream's reference merged_spectra."""
    obj = cNMF(output_dir=workdir, name="probe_cNMF")
    obj.prepare(
        counts_fn=COUNTS,
        components=K_VALUES,
        n_iter=N_ITER,
        num_highvar_genes=NHVG,
        seed=PREPARE_SEED,
    )
    for k in K_VALUES:
        dest = obj.paths["merged_spectra"] % k
        src = dest.replace(workdir, REF_DIR).replace("probe_cNMF", REF_NAME)
        shutil.copy(src, dest)
    return obj


def snapshot(obj, dest_dir):
    """Copy this run's consensus artifacts out before the next call overwrites them."""
    os.makedirs(dest_dir, exist_ok=True)
    dt = str(DENSITY_THRESHOLD).replace(".", "_")
    out = {}
    for name, _ in ARTIFACTS:
        src = obj.paths[name] % (K, dt)
        if os.path.exists(src):
            dst = os.path.join(dest_dir, os.path.basename(src))
            shutil.copy(src, dst)
            out[name] = dst
    return out


def compare(path_a, path_b):
    a = load_df_from_npz(path_a)
    b = load_df_from_npz(path_b)
    if a.shape != b.shape:
        return {"max_abs_diff": float("nan"), "rel_frobenius": float("nan"),
                "bitwise_identical": False, "note": f"shape {a.shape} vs {b.shape}"}
    av, bv = a.values.astype(float), b.values.astype(float)
    diff = np.abs(av - bv)
    denom = np.sqrt((av ** 2).sum())
    return {
        "max_abs_diff": float(diff.max()),
        "rel_frobenius": float(np.sqrt((diff ** 2).sum()) / denom) if denom > 0 else float("nan"),
        "bitwise_identical": bool(np.array_equal(av, bv)),
        "note": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.workdir, exist_ok=True)
    obj = build_fixed_factor_bank(args.workdir)

    snaps = {"free": [], "seeded": []}
    for condition in ("free", "seeded"):
        for rep in range(args.reps):
            if condition == "seeded":
                np.random.seed(SEED_BEFORE_CONSENSUS)
            obj.consensus(k=K, density_threshold=DENSITY_THRESHOLD, show_clustering=False)
            snaps[condition].append(
                snapshot(obj, os.path.join(args.workdir, "snapshots", condition, f"rep{rep}"))
            )
            print(f"[{condition}] rep {rep} done", flush=True)

    rows = []
    for condition in ("free", "seeded"):
        base = snaps[condition][0]
        for rep in range(1, args.reps):
            cur = snaps[condition][rep]
            for name, kind in ARTIFACTS:
                if name not in base or name not in cur:
                    continue
                m = compare(base[name], cur[name])
                rows.append({
                    "condition": condition, "artifact": name, "artifact_kind": kind,
                    "rep_vs_rep0": rep, "k": K, "density_threshold": DENSITY_THRESHOLD,
                    **m,
                })

    df = pd.DataFrame(rows)
    df.to_csv(args.out, sep="\t", index=False)

    print("\n=== SUMMARY: max over reps, per condition x artifact ===")
    summary = df.groupby(["condition", "artifact_kind", "artifact"]).agg(
        max_abs_diff=("max_abs_diff", "max"),
        max_rel_frobenius=("rel_frobenius", "max"),
        all_bitwise_identical=("bitwise_identical", "all"),
    )
    print(summary.to_string())
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
