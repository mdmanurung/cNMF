"""Round-trip, and the four cNMF API traps that would silently corrupt a run.

Each trap here was verified against `src/cnmf/cnmf.py` at the pinned revision. They share
a property that makes them worth a test apiece: **none of them raises**. A run hits one,
completes, and produces plausible numbers that mean something other than what the report
will claim.
"""
import numpy as np
import pytest

from cnmfbench.io import load_dataset, write_dataset
from cnmfbench.scenarios import build_params
from cnmfbench.simulate import simulate

pytestmark = pytest.mark.filterwarnings("ignore")

# `n_neighbors = int(local_neighborhood_size * merged_spectra.shape[0] / k)` with
# `merged_spectra.shape[0] == n_iter * k`, so it reduces to `int(0.30 * n_iter)` and is
# independent of k. At n_iter <= 3 it is **zero**. See the test below.
MIN_SAFE_N_ITER = 4


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    params = build_params("base_identifiable", "SMOKE")
    ds = simulate(params, "base_identifiable", "SMOKE", seed=2024)
    directory = tmp_path_factory.mktemp("dataset")
    manifest = write_dataset(ds, str(directory))
    return ds, str(directory), manifest


def test_round_trip_preserves_counts_and_truth(written):
    ds, directory, _ = written
    adata, truth, _manifest = load_dataset(directory)
    np.testing.assert_array_equal(np.asarray(adata.X), np.asarray(ds.adata.X))
    np.testing.assert_allclose(truth["true_spectra"], ds.true_spectra)
    np.testing.assert_allclose(truth["true_usages"], ds.true_usages)


def test_round_trip_preserves_donor_labels(written):
    ds, directory, _ = written
    adata, _truth, _manifest = load_dataset(directory)
    assert list(adata.obs["donor_id"]) == list(ds.adata.obs["donor_id"])


def test_manifest_records_artifact_hashes_over_file_bytes(written):
    _ds, _directory, manifest = written
    assert set(manifest["files"]) == {"counts", "truth"}
    assert all(len(h) == 64 for h in manifest["files"].values())


def test_load_detects_a_tampered_counts_file(written):
    """Verification is on by default because the cheapest way to produce an
    unreproducible result is to compare against truth regenerated since the counts were
    written."""
    import shutil

    _ds, directory, _manifest = written
    copy = directory + "_tampered"
    shutil.copytree(directory, copy)
    with open(f"{copy}/counts.h5ad", "r+b") as fh:
        fh.seek(-1, 2)
        last = fh.read(1)
        fh.seek(-1, 2)
        fh.write(bytes([last[0] ^ 0xFF]))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_dataset(copy)


# --------------------------------------------------------------------- cNMF API traps


def test_h5ad_input_preserves_donor_id_through_prepare(written, tmp_path):
    """TRAP 1, the most consequential. `.npz` and tab-delimited inputs rebuild `obs` and
    `var` as bare indices (`cnmf.py:396-402`), discarding `donor_id`. With `.h5ad` it
    survives into `norm_counts.h5ad`.

    This is an integration test against the real pinned cNMF, not a mock: the claim being
    checked is about upstream's behaviour, and a mock would only check my reading of it.
    """
    import anndata as ad
    from cnmf import cNMF

    ds, directory, _ = written
    obj = cNMF(output_dir=str(tmp_path), name="interop")
    obj.prepare(
        counts_fn=f"{directory}/counts.h5ad",
        components=[2, 3],
        n_iter=2,
        # SMOKE has 180 genes; `num_highvar_genes` defaults to 2000 and must be
        # configured below the gene count or HVG selection is a no-op.
        num_highvar_genes=100,
        seed=1,
    )
    norm = ad.read_h5ad(obj.paths["normalized_counts"])
    assert "donor_id" in norm.obs.columns
    assert list(norm.obs["donor_id"]) == list(ds.adata.obs["donor_id"])


def test_consensus_artifacts_carry_only_the_cell_index(written, tmp_path):
    """TRAP 1b. Donor labels survive into `norm_counts.h5ad` but **not** into the
    consensus artifacts, which carry only `obs.index` (`cnmf.py:920, 975`). Downstream
    code must re-join on the cell index. Asserted so that a future change upstream which
    starts propagating `obs` does not go unnoticed."""
    import pandas as pd
    from cnmf import cNMF

    ds, directory, _ = written
    obj = cNMF(output_dir=str(tmp_path), name="interop_consensus")
    obj.prepare(
        counts_fn=f"{directory}/counts.h5ad",
        components=[3],
        n_iter=MIN_SAFE_N_ITER,  # see test_small_n_iter_breaks_density_filtering
        num_highvar_genes=100,
        seed=1,
    )
    obj.factorize(worker_i=0, total_workers=1)
    obj.combine()
    # TRAP 3: both default to True (cnmf.py:823), contradicting the docstring, and would
    # render plots and build a starCAT reference in a headless run.
    obj.consensus(k=3, density_threshold=2.0, show_clustering=False, build_ref=False)

    from cnmf.cnmf import load_df_from_npz

    usages = load_df_from_npz(obj.paths["consensus_usages"] % (3, "2_0"))
    assert isinstance(usages, pd.DataFrame)
    # The index is the cell id and nothing else — the donor label is gone.
    assert set(usages.index) == set(ds.adata.obs_names)


def test_reusing_a_run_name_warns_at_prepare_time(written, tmp_path):
    """TRAP 2, **narrowed by measurement**.

    The plan recorded this as "a reused name silently skips factorization". Measured, the
    behaviour is more specific, and the correction matters because it changes what the
    harness has to guard:

    - the `completed=True` marking and its `UserWarning` happen inside
      `get_nmf_iter_params`, which `prepare()` calls — so the warning fires at **prepare**
      time, not at factorize time
    - `factorize` defaults to `skip_completed_runs=False` (`cnmf.py:692`), so with the
      default it **re-runs** every replicate regardless of the marking

    So the silent-skip hazard needs `skip_completed_runs=True`. The live hazard with
    default arguments is the opposite one: a reused directory silently *overwrites* the
    previous run's factors while the warning scrolls past. A fresh name per run is still
    required; the reason is overwriting, not skipping.
    """
    from cnmf import cNMF

    _ds, directory, _ = written
    kwargs = dict(counts_fn=f"{directory}/counts.h5ad", components=[2],
                  n_iter=MIN_SAFE_N_ITER, num_highvar_genes=100, seed=1)

    obj = cNMF(output_dir=str(tmp_path), name="reused")
    obj.prepare(**kwargs)
    obj.factorize(worker_i=0, total_workers=1)

    again = cNMF(output_dir=str(tmp_path), name="reused")
    with pytest.warns(UserWarning, match="already appear completed"):
        again.prepare(**kwargs)

    params = np.load(again.paths["nmf_replicate_parameters"], allow_pickle=True)
    assert params["data"].any(), "pre-existing replicates were not marked completed"


def test_small_n_iter_breaks_density_filtering(written, tmp_path):
    """A **fifth** API trap, not in the plan's list, found by running the code.

    `n_neighbors = int(local_neighborhood_size * merged_spectra.shape[0] / k)` and
    `merged_spectra` has `n_iter * k` rows, so this reduces to `int(0.30 * n_iter)`,
    independent of k. At `n_iter <= 3` it is **zero**, `local_density` is a sum divided by
    zero, every comparison against the threshold is False, and `consensus` dies with
    `"Zero components remain after density filtering. Consider increasing density
    threshold"` — a message that points at the threshold, which is not the problem.
    Raising the threshold cannot fix it.

    This bites `smoke.yaml` directly: `optimizer_starts: 3`. The smoke tier must use at
    least 4, or every consensus call fails for a reason the error text misdescribes.
    """
    from cnmf import cNMF

    _ds, directory, _ = written
    obj = cNMF(output_dir=str(tmp_path), name="tiny_n_iter")
    obj.prepare(counts_fn=f"{directory}/counts.h5ad", components=[3], n_iter=3,
                num_highvar_genes=100, seed=1)
    obj.factorize(worker_i=0, total_workers=1)
    obj.combine()
    with pytest.raises(RuntimeError, match="Zero components remain"):
        obj.consensus(k=3, density_threshold=2.0, show_clustering=False, build_ref=False)


@pytest.mark.parametrize("n_iter,expected", [(2, 0), (3, 0), (4, 1), (10, 3), (20, 6)])
def test_n_neighbors_formula_is_independent_of_k(n_iter, expected):
    for k in (3, 7, 12):
        assert int(0.30 * (n_iter * k) / k) == expected


def test_density_threshold_string_must_match_between_calls(written, tmp_path):
    """TRAP 4b. `str(density_threshold).replace('.','_')` builds the filename
    (`cnmf.py:878`), so `consensus` and `load_results` must be handed the *identical*
    Python value. `2.0` and `2` produce different paths for the same intent."""
    assert str(2.0).replace(".", "_") == "2_0"
    assert str(2).replace(".", "_") == "2"
