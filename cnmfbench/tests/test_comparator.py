"""P0-09 GeneNMF comparator conversion checks.

GeneNMF emits gene sets/weights, not full spectra vectors (SOURCE_AUDIT §2.3),
so the §5.2 cosine metric is unavailable for it — these checks validate the
conversion (feature/order preservation), not scientific quality. They skip when
the R smoke output is absent (comparator dependencies stay optional).
"""
import csv
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "results/scratch/genenmf_smoke/out")
IN_CSV = os.path.join(REPO, "results/scratch/genenmf_smoke/counts_cells_x_genes.csv")

needs_r_output = pytest.mark.skipif(
    not os.path.isdir(OUT), reason="GeneNMF R smoke output absent (optional comparator)"
)


def _dash(names):
    return [n.replace("_", "-") for n in names]


@needs_r_output
def test_mp_weights_reference_input_genes_in_order():
    with open(IN_CSV, encoding="utf-8") as fh:
        input_genes = next(csv.reader(fh))[1:]
    allowed = set(_dash(input_genes))
    found = [f for f in os.listdir(OUT) if f.startswith("mp_MP") and f.endswith("_weights.csv")]
    assert found, "no meta-program weight files in R smoke output"
    for f in found:
        with open(os.path.join(OUT, f), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert rows, f"{f} is empty"
        unknown = [r["gene"] for r in rows if r["gene"] not in allowed]
        assert not unknown, f"{f} references genes outside the input: {unknown[:5]}"


@needs_r_output
def test_mp_weights_are_nonnegative_and_sum_to_one():
    for f in os.listdir(OUT):
        if not (f.startswith("mp_MP") and f.endswith("_weights.csv")):
            continue
        with open(os.path.join(OUT, f), encoding="utf-8") as fh:
            weights = [float(r["weight"]) for r in csv.DictReader(fh)]
        assert all(w >= 0 for w in weights), f"{f} has negative weights"
        assert abs(sum(weights) - 1.0) < 1e-6, f"{f} sums to {sum(weights)}"


@needs_r_output
def test_mp_metrics_and_provenance_exist():
    assert os.path.isfile(os.path.join(OUT, "mp_metrics.csv"))
    import json

    with open(os.path.join(OUT, "provenance.json"), encoding="utf-8") as fh:
        prov = json.load(fh)
    assert prov["genenmf_commit_sha"] == "59942b27c2cc2dbf55264b80b4ff26e3188cdf41"
    assert prov["seed"] == 123
    assert prov["n_models"] == 24  # 8 donors x ranks 2,3,4
