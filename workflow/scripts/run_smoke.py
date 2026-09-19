#!/usr/bin/env python3
"""P0-07 smoke entry point: generated data → metric table → brief report.

Runs without Snakemake so the smoke step is testable with plain pytest and
python. The Snakefile invokes this script; it holds no scientific rules.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from cnmfbench import cache
from cnmfbench.skeleton import run


def main():
    ap = argparse.ArgumentParser(description="P0-07 smoke workflow step")
    ap.add_argument("--config", default="docs/benchmarks/configs/smoke_000m.yaml")
    ap.add_argument("--out-root", default="results/scratch")
    ap.add_argument("--run-id", default="smoke")
    args = ap.parse_args()

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"

    summary = run(args.config, args.out_root, args.run_id)
    run_dir = summary["run_dir"]
    key = cache.cache_key({"config": args.config, "run_id": args.run_id})
    cache.mark_success(run_dir, key, extra={
        "n_results": summary["n_results"],
        "n_experiments": summary["n_experiments"],
    })
    report = {
        "run_id": summary["run_id"],
        "run_dir": run_dir,
        "n_results": summary["n_results"],
        "n_experiments": summary["n_experiments"],
        "provisional_components": list(summary["provisional_components"]),
        "sentinel": os.path.join(run_dir, cache.SUCCESS_FILENAME),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
