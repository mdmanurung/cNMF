"""Writing and reading a simulated dataset.

**The format is `.h5ad`, and that is not a preference.** cNMF's `.npz` and tab-delimited
readers rebuild `obs` and `var` as bare positional indices (`cnmf.py:396-402`), so
`obs['donor_id']` would silently vanish — the run would complete, produce plausible
numbers, and every donor-blocked split downstream would be a random split. Nothing in the
output would reveal it.

Donor labels survive into `norm_counts.h5ad` and `tpm.h5ad`, but **not** into the
consensus artifacts, which carry only `obs.index` (`cnmf.py:920, 975`). Donor labels must
therefore be re-joined on the cell index downstream; `load_dataset` returns them in an
order matching `adata.obs_names` so that join is a lookup, not a guess.

Ground truth is written to sibling files rather than into `adata`, so that handing the
counts to a fitting routine cannot hand it the answer as well (§6.3: ground truth is never
an input to any selector, transform or fit).
"""
import json
import os

import numpy as np

from .contract import check_dataset
from .hashing import artifact_hash

__all__ = ["write_dataset", "load_dataset", "dataset_paths"]

_COUNTS = "counts.h5ad"
_TRUTH = "truth.npz"
_MANIFEST = "manifest.json"


def dataset_paths(directory):
    return {
        "counts": os.path.join(directory, _COUNTS),
        "truth": os.path.join(directory, _TRUTH),
        "manifest": os.path.join(directory, _MANIFEST),
    }


def write_dataset(dataset, directory):
    """Write counts, truth and manifest. Returns the manifest that was written.

    The contract is re-checked here even though `simulate` already checked it, because
    this is also the entry point for a dataset assembled some other way, and a malformed
    dataset reaching disk is the failure that is hardest to trace later.

    `expected_counts` is saved although §6.3 requires only spectra and usages. It is
    derivable from them, so saving it is additive and does not amend the contract — and
    it makes the analytic Poisson error floor computable without regenerating data.
    """
    check_dataset(dataset.adata, dataset.true_spectra, dataset.true_usages)
    os.makedirs(directory, exist_ok=True)
    paths = dataset_paths(directory)

    dataset.adata.write_h5ad(paths["counts"])
    np.savez_compressed(
        paths["truth"],
        true_spectra=dataset.true_spectra,
        true_usages=dataset.true_usages,
        expected_counts=dataset.expected_counts,
        donor_eligibility=dataset.donor_eligibility,
        # Ragged marker sets cannot go in a plain array; store the membership mask.
        marker_mask=_marker_mask(dataset),
        cell_ids=np.array(list(dataset.adata.obs_names), dtype=object),
        gene_ids=np.array(list(dataset.adata.var_names), dtype=object),
        donor_ids=np.array(list(dataset.adata.obs["donor_id"]), dtype=object),
        allow_pickle=True,
    )

    manifest = dict(dataset.manifest)
    # Artifact hashes are over file bytes (§7), computed after writing, so the recorded
    # value describes what is actually on disk rather than what was intended.
    manifest["files"] = {
        name: artifact_hash(path) for name, path in paths.items() if name != "manifest"
    }
    with open(paths["manifest"], "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True, ensure_ascii=False)
    return manifest


def _marker_mask(dataset):
    mask = np.zeros((dataset.true_spectra.shape[0], dataset.adata.n_vars), dtype=bool)
    for k, markers in enumerate(dataset.marker_sets):
        mask[k, markers] = True
    return mask


def load_dataset(directory, verify=True):
    """Read a dataset back. `verify=True` re-checks the recorded artifact hashes.

    Verification is on by default because the cheapest way to produce an unreproducible
    result is to compare against truth that has been regenerated with different
    parameters since the counts were written.
    """
    import anndata as ad

    paths = dataset_paths(directory)
    with open(paths["manifest"], encoding="utf-8") as fh:
        manifest = json.load(fh)

    if verify:
        for name, recorded in manifest.get("files", {}).items():
            actual = artifact_hash(paths[name])
            if actual != recorded:
                raise ValueError(
                    f"{name} hash mismatch in {directory}: recorded {recorded}, found "
                    f"{actual}. The files on disk are not the dataset this manifest "
                    "describes."
                )

    adata = ad.read_h5ad(paths["counts"])
    truth = np.load(paths["truth"], allow_pickle=True)

    if list(adata.var_names) != list(truth["gene_ids"]):
        raise ValueError("gene order differs between counts and truth (§6.3)")
    if list(adata.obs_names) != list(truth["cell_ids"]):
        raise ValueError("cell order differs between counts and truth (§6.3)")

    return adata, {k: truth[k] for k in truth.files}, manifest
