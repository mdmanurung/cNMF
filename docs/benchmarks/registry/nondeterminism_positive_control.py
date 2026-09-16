#!/usr/bin/env python
"""Positive control for nondeterminism_probe.py, v2.

v1 used a UNIFORM SCALAR perturbation of refit_usage output. That was a bad control:
consensus_usages / gene_spectra_tpm / starcat_spectra are scale-normalized downstream,
so a global (1+eps) factor cancels exactly, and consensus_spectra is computed BEFORE
the refit and cannot depend on it at all. v1's "BLIND" verdicts were an artifact of the
control, not evidence about the probe.

v2 separates the two questions that were conflated:

  TEST 1 - is the MEASURING CHAIN sensitive?
      Load each artifact the probe snapshotted, nudge ONE element by a relative 1e-9,
      write it back through cNMF's own save_df_to_npz, and run the probe's compare()
      on original vs nudged. This exercises exactly the load->diff->verdict path the
      probe relies on. Every artifact must come back non-identical. A failure here
      means the probe cannot see differences and its null result is worthless.

  TEST 2 - which artifacts actually DEPEND on the refit?
      Perturb refit_usage output NON-UNIFORMLY (first component only), so the change
      survives row normalization, and see which artifacts move. This measures the
      probe's causal reach: an artifact that cannot change when the refit changes was
      never evidence about refit determinism in the first place.
"""
import os
import sys
import shutil

import numpy as np

sys.path.insert(0, "/exports/para-lipg-hpc/mdmanurung/cNMF/docs/benchmarks/registry")
from nondeterminism_probe import compare, snapshot, ARTIFACTS, K, DENSITY_THRESHOLD  # noqa: E402

from cnmf import cNMF  # noqa: E402
import cnmf.cnmf as cnmf_mod  # noqa: E402
from cnmf.cnmf import load_df_from_npz, save_df_to_npz  # noqa: E402

# Session-scoped scratch workdir holding the factor bank the original probe prepared.
# It is NOT under version control and will not exist in a fresh session: rebuild it with
# nondeterminism_probe.build_fixed_factor_bank(workdir) and pass --workdir. Kept as a
# default only so the recorded log is reproducible within the session that produced it.
DEFAULT_WORKDIR = ("/tmp/claude-149488/-exports-para-lipg-hpc-mdmanurung-cNMF/"
                   "c8d456a3-e018-4f74-8bcf-b1c69f9a098d/scratchpad/nondet_work")
EPS = 1e-9


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default=DEFAULT_WORKDIR,
                    help="cNMF output_dir containing a prepared 'probe_cNMF' factor bank")
    args = ap.parse_args()
    global WORKDIR, PC_DIR
    WORKDIR = args.workdir
    PC_DIR = os.path.join(WORKDIR, "positive_control_v2")
    if not os.path.isdir(WORKDIR):
        sys.exit(f"workdir missing: {WORKDIR}\n"
                 "Rebuild it with nondeterminism_probe.build_fixed_factor_bank(workdir).")
    shutil.rmtree(PC_DIR, ignore_errors=True)
    obj = cNMF(output_dir=WORKDIR, name="probe_cNMF")
    original_refit = cnmf_mod.cNMF.refit_usage

    obj.consensus(k=K, density_threshold=DENSITY_THRESHOLD, show_clustering=False)
    clean = snapshot(obj, os.path.join(PC_DIR, "clean"))

    # ---------------- TEST 1: is the measuring chain sensitive? ----------------
    print("TEST 1 - measuring chain: nudge one element by rel 1e-9, does compare() see it?")
    print(f"  {'artifact':<22} {'rel_frobenius':<16} {'bitwise':<10} verdict")
    chain_failures = []
    nudge_dir = os.path.join(PC_DIR, "nudged")
    os.makedirs(nudge_dir, exist_ok=True)
    for name, _kind in ARTIFACTS:
        if name not in clean:
            print(f"  {name:<22} NOT SNAPSHOTTED -> probe skips it silently")
            chain_failures.append((name, "missing"))
            continue
        df = load_df_from_npz(clean[name])
        vals = df.values.astype(float)
        # nudge the largest-magnitude element so the change is representable
        idx = np.unravel_index(np.argmax(np.abs(vals)), vals.shape)
        df2 = df.copy()
        df2.iloc[idx] = vals[idx] * (1.0 + EPS)
        out = os.path.join(nudge_dir, os.path.basename(clean[name]))
        save_df_to_npz(df2, out)
        m = compare(clean[name], out)
        seen = not m["bitwise_identical"]
        if not seen:
            chain_failures.append((name, "blind"))
        print(f"  {name:<22} {m['rel_frobenius']:<16.3e} "
              f"{str(m['bitwise_identical']):<10} {'SENSITIVE' if seen else 'BLIND'}")

    # ---------------- TEST 2: which artifacts depend on the refit? ----------------
    def perturbed_refit(self, X, spectra):
        out = np.array(original_refit(self, X, spectra), copy=True)
        out[:, 0] = out[:, 0] * (1.0 + 1e-6)   # non-uniform: survives row normalization
        return out

    cnmf_mod.cNMF.refit_usage = perturbed_refit
    try:
        obj.consensus(k=K, density_threshold=DENSITY_THRESHOLD, show_clustering=False)
        perturbed = snapshot(obj, os.path.join(PC_DIR, "perturbed"))
    finally:
        cnmf_mod.cNMF.refit_usage = original_refit
    obj.consensus(k=K, density_threshold=DENSITY_THRESHOLD, show_clustering=False)  # restore

    print()
    print("TEST 2 - causal reach: perturb refit component 0 by rel 1e-6, what moves?")
    print(f"  {'artifact':<22} {'kind':<14} {'rel_frobenius':<16} depends on refit?")
    for name, kind in ARTIFACTS:
        if name not in clean or name not in perturbed:
            continue
        m = compare(clean[name], perturbed[name])
        moved = not m["bitwise_identical"]
        print(f"  {name:<22} {kind:<14} {m['rel_frobenius']:<16.3e} {'YES' if moved else 'NO'}")

    print()
    if chain_failures:
        print("VERDICT: measuring chain FAILED for", chain_failures)
        print("The probe's null result does not establish determinism for those artifacts.")
        return 1
    print("VERDICT: measuring chain is sensitive for all five artifacts (TEST 1 all SENSITIVE).")
    print("The probe's original null result therefore reflects the system, not a blind instrument.")
    print("TEST 2 shows which artifacts the probe could ever have spoken about.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
