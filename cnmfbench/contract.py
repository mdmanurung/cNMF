"""PROTOCOL §6 data-contract conformance checks.

Deliberately minimal: P0-02 implements the full schema/provenance layer and **may not
redefine §6** (DECISIONS.md D006 guard clause). What lives here is the subset the
simulator must satisfy to be usable at all, asserted at generation time so that a
malformed dataset never reaches disk.

Every check raises `ContractViolation` with a message naming the clause it enforces, so
a failure points at the rule rather than at a traceback.
"""
import numpy as np

__all__ = ["ContractViolation", "check_counts", "check_truth", "check_dataset"]


class ContractViolation(AssertionError):
    """A PROTOCOL §6 clause is violated. Subclasses AssertionError so `pytest.raises`
    over either type behaves the way a reader expects."""


def _require(condition, clause, message):
    if not condition:
        raise ContractViolation(f"PROTOCOL {clause}: {message}")


def check_counts(adata):
    """§6.1 orientation/dtype/identifiers, §6.3 donor label, plus the two emptiness
    conditions that make cNMF raise or produce NaN.

    The emptiness checks belong here rather than in the simulator because they are a
    property of *any* dataset entering the engine, not of how this one was generated:

    - a cell with zero counts over the HVG subset makes `get_norm_counts` raise
      (`cnmf.py:551-554`)
    - an all-zero gene gives `gene_fano = gene_var / gene_mean = 0/0 = NaN`
      (`cnmf.py:144`), which propagates silently into HVG selection

    They are checked on the full gene set here, which is necessary but not sufficient:
    the HVG-subset condition can only be checked once a panel is chosen. The splitter
    re-checks it per fold.
    """
    X = adata.X
    dense = np.asarray(X.todense()) if hasattr(X, "todense") else np.asarray(X)

    _require(dense.ndim == 2, "§6.1", f"counts must be 2-D, got {dense.ndim}-D")
    _require(
        dense.shape == (adata.n_obs, adata.n_vars),
        "§6.1",
        f"counts must be cells x genes; X is {dense.shape} but "
        f"(n_obs, n_vars) is {(adata.n_obs, adata.n_vars)}",
    )

    # "stored as integers" — accept an integer dtype, or a float array holding exact
    # integers, which is what a round-trip through some HDF5 writers produces.
    is_int_dtype = np.issubdtype(dense.dtype, np.integer)
    _require(
        is_int_dtype or np.all(dense == np.floor(dense)),
        "§6.1",
        f"raw counts must be integers, got dtype {dense.dtype} with non-integral values",
    )
    _require(np.all(dense >= 0), "§6.1", "counts must be non-negative")
    _require(np.all(np.isfinite(dense)), "§6.1", "counts contain NaN or inf")

    for axis_name, index in (("obs", adata.obs_names), ("var", adata.var_names)):
        ids = list(index)
        _require(
            all(isinstance(i, str) for i in ids),
            "§6.1",
            f"{axis_name} identifiers must be strings, not positional integers",
        )
        _require(len(set(ids)) == len(ids), "§6.1", f"{axis_name} identifiers must be unique")

    _require("donor_id" in adata.obs.columns, "§6.3", "obs['donor_id'] is required")
    _require(
        all(isinstance(d, str) for d in adata.obs["donor_id"]),
        "§6.3",
        "obs['donor_id'] must be a string column",
    )

    empty_cells = int((dense.sum(axis=1) == 0).sum())
    _require(
        empty_cells == 0,
        "§6.1",
        f"{empty_cells} cells have zero total counts; get_norm_counts raises on these "
        "(cnmf.py:551-554)",
    )
    empty_genes = int((dense.sum(axis=0) == 0).sum())
    _require(
        empty_genes == 0,
        "§6.1",
        f"{empty_genes} genes are all-zero; gene_fano becomes NaN on these (cnmf.py:144)",
    )


def check_truth(adata, spectra, usages):
    """§6.3: true spectra `K_true x n_genes` in `var.index` order, true usages
    `n_cells x K_true` in `obs.index` order.

    Order-matching cannot be verified from shapes alone — it is a promise the generator
    makes and this function can only check the half that is checkable. The generator
    therefore builds both from the same index objects rather than reindexing later.
    """
    spectra = np.asarray(spectra)
    usages = np.asarray(usages)

    _require(spectra.ndim == 2, "§6.3", f"true spectra must be 2-D, got {spectra.ndim}-D")
    _require(usages.ndim == 2, "§6.3", f"true usages must be 2-D, got {usages.ndim}-D")

    k_true = spectra.shape[0]
    _require(
        spectra.shape[1] == adata.n_vars,
        "§6.3",
        f"true spectra must be K_true x n_genes; got {spectra.shape} for "
        f"n_genes={adata.n_vars}",
    )
    _require(
        usages.shape == (adata.n_obs, k_true),
        "§6.3",
        f"true usages must be n_cells x K_true; got {usages.shape}, expected "
        f"{(adata.n_obs, k_true)}",
    )
    _require(np.all(spectra >= 0), "§6.3", "true spectra must be non-negative")
    _require(np.all(usages >= 0), "§6.3", "true usages must be non-negative")

    # §6.2: "V = median_spectra — rows sum to 1 over the full G". The simulator's true
    # spectra are stored in the same units so that recovery is a like-for-like
    # comparison rather than one mediated by an undocumented rescaling.
    row_sums = spectra.sum(axis=1)
    _require(
        np.allclose(row_sums, 1.0, atol=1e-10),
        "§6.2",
        f"true spectra rows must sum to 1; max deviation {np.abs(row_sums - 1).max():.3e}",
    )


def check_dataset(adata, spectra, usages):
    """Both halves of the contract. What the simulator calls before writing."""
    check_counts(adata)
    check_truth(adata, spectra, usages)
