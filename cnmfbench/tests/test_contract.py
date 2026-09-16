"""PROTOCOL §6 conformance checks, tested by violating each clause.

A check that has never been shown to fire is not evidence — that lesson is recorded in
SOURCE_AUDIT §1.5.1, where a positive control that could not detect its own perturbation
briefly produced four false "BLIND" verdicts. So every clause here gets a case that
breaks it.
"""
import anndata as ad
import numpy as np
import pandas as pd
import pytest

from cnmfbench.contract import ContractViolation, check_counts, check_truth

N_CELLS, N_GENES, K_TRUE = 6, 5, 2


def make_adata(counts=None, obs=None, var=None):
    counts = np.arange(1, N_CELLS * N_GENES + 1, dtype=np.int32).reshape(N_CELLS, N_GENES) if counts is None else counts
    obs = pd.DataFrame(
        {"donor_id": [f"donor_{i % 2}" for i in range(counts.shape[0])]},
        index=[f"cell_{i}" for i in range(counts.shape[0])],
    ) if obs is None else obs
    var = pd.DataFrame(index=[f"gene_{j}" for j in range(counts.shape[1])]) if var is None else var
    return ad.AnnData(X=counts, obs=obs, var=var)


def make_truth(n_genes=N_GENES, k=K_TRUE, n_cells=N_CELLS):
    spectra = np.full((k, n_genes), 1.0 / n_genes)
    usages = np.ones((n_cells, k))
    return spectra, usages


def test_a_valid_dataset_passes():
    adata = make_adata()
    spectra, usages = make_truth()
    check_counts(adata)
    check_truth(adata, spectra, usages)


def test_rejects_non_integer_counts():
    counts = np.full((N_CELLS, N_GENES), 1.5)
    with pytest.raises(ContractViolation, match="integers"):
        check_counts(make_adata(counts))


def test_accepts_float_array_holding_exact_integers():
    # An HDF5 round-trip can hand back float64 that is integral. That is still integer
    # counts and must not be rejected.
    counts = np.ones((N_CELLS, N_GENES), dtype=np.float64)
    check_counts(make_adata(counts))


def test_rejects_negative_counts():
    counts = np.ones((N_CELLS, N_GENES), dtype=np.int32)
    counts[0, 0] = -1
    with pytest.raises(ContractViolation, match="non-negative"):
        check_counts(make_adata(counts))


class _StubAnnData:
    """Minimal stand-in, because AnnData silently coerces an integer index to strings
    (`ImplicitModificationWarning: Transforming to str index`) and so cannot be used to
    exercise the §6.1 identifier clause at all."""

    def __init__(self, X, obs, var_names):
        self.X, self.obs = X, obs
        self.obs_names, self.var_names = obs.index, pd.Index(var_names)
        self.n_obs, self.n_vars = X.shape


def test_anndata_coerces_integer_identifiers_so_the_clause_guards_the_direct_path():
    """§6.1 forbids positional integer identifiers. The measured behaviour is that
    AnnData converts them to strings on construction, so a dataset built through AnnData
    cannot violate the clause — the check guards callers that build the object some other
    way.

    Recorded rather than deleted because the underlying hazard is real and is **not**
    dtype: cNMF's `.npz` and tab-delimited readers rebuild `obs`/`var` as bare indices
    (`cnmf.py:396-402`), which discards `donor_id` entirely. That is why the harness must
    use `.h5ad`, and it is caught by the donor-column clause, not this one.
    """
    counts = np.ones((N_CELLS, N_GENES), dtype=np.int32)
    obs = pd.DataFrame({"donor_id": ["d"] * N_CELLS}, index=range(N_CELLS))
    adata = make_adata(counts, obs=obs)
    assert all(isinstance(i, str) for i in adata.obs_names)  # coerced, not rejected

    stub = _StubAnnData(counts, obs, [f"g{j}" for j in range(N_GENES)])
    with pytest.raises(ContractViolation, match="strings"):
        check_counts(stub)


def test_npz_style_input_loses_the_donor_column():
    """The trap that motivates the `.h5ad` requirement, reproduced at contract level: an
    object rebuilt with bare indices and no `obs` columns fails the §6.3 clause loudly
    rather than running with donor structure silently erased."""
    counts = np.ones((N_CELLS, N_GENES), dtype=np.int32)
    bare = pd.DataFrame(index=[f"cell_{i}" for i in range(N_CELLS)])
    stub = _StubAnnData(counts, bare, [f"g{j}" for j in range(N_GENES)])
    with pytest.raises(ContractViolation, match="donor_id"):
        check_counts(stub)


def test_rejects_duplicate_gene_identifiers():
    counts = np.ones((N_CELLS, 3), dtype=np.int32)
    var = pd.DataFrame(index=["g0", "g0", "g1"])
    with pytest.raises(ContractViolation, match="unique"):
        check_counts(make_adata(counts, var=var))


def test_rejects_missing_donor_column():
    counts = np.ones((N_CELLS, N_GENES), dtype=np.int32)
    obs = pd.DataFrame(index=[f"cell_{i}" for i in range(N_CELLS)])
    with pytest.raises(ContractViolation, match="donor_id"):
        check_counts(make_adata(counts, obs=obs))


def test_rejects_non_string_donor_column():
    counts = np.ones((N_CELLS, N_GENES), dtype=np.int32)
    obs = pd.DataFrame(
        {"donor_id": list(range(N_CELLS))}, index=[f"cell_{i}" for i in range(N_CELLS)]
    )
    with pytest.raises(ContractViolation, match="donor_id"):
        check_counts(make_adata(counts, obs=obs))


def test_rejects_an_all_zero_cell():
    # get_norm_counts raises on these (cnmf.py:551-554).
    counts = np.ones((N_CELLS, N_GENES), dtype=np.int32)
    counts[2, :] = 0
    with pytest.raises(ContractViolation, match="zero total counts"):
        check_counts(make_adata(counts))


def test_rejects_an_all_zero_gene():
    # gene_fano = gene_var/gene_mean becomes NaN on these (cnmf.py:144) and the NaN
    # propagates silently into HVG selection.
    counts = np.ones((N_CELLS, N_GENES), dtype=np.int32)
    counts[:, 1] = 0
    with pytest.raises(ContractViolation, match="all-zero"):
        check_counts(make_adata(counts))


def test_rejects_transposed_truth():
    adata = make_adata()
    spectra, usages = make_truth()
    with pytest.raises(ContractViolation, match="K_true x n_genes"):
        check_truth(adata, spectra.T, usages)


def test_rejects_usages_with_the_wrong_cell_count():
    adata = make_adata()
    spectra, usages = make_truth()
    with pytest.raises(ContractViolation, match="n_cells x K_true"):
        check_truth(adata, spectra, usages[:-1])


def test_rejects_spectra_rows_that_do_not_sum_to_one():
    # §6.2 fixes V's units. Storing truth in different units from the recovered
    # dictionary would make every recovery comparison pass through an undocumented
    # rescaling.
    adata = make_adata()
    spectra, usages = make_truth()
    with pytest.raises(ContractViolation, match="sum to 1"):
        check_truth(adata, spectra * 2.0, usages)


def test_rejects_negative_truth():
    adata = make_adata()
    spectra, usages = make_truth()
    usages = usages.copy()
    usages[0, 0] = -1.0
    with pytest.raises(ContractViolation, match="non-negative"):
        check_truth(adata, spectra, usages)
