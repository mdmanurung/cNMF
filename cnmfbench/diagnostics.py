"""Feasibility diagnostics for the simulator. **Not** the P0-04 metrics.

Everything here answers one question: *is this dataset capable of showing the effect the
benchmark is meant to measure?* A dataset that cannot is not a hard test, it is an
uninformative one, and the difference is invisible in the result — a flat comparison
looks the same whether the feature does nothing or the data could never have revealed it.

These are run **before** `delta` is set and before any comparator row is written.

The NMF/NNLS code below is deliberately throwaway. `program_recovery_cosine_v1`,
`usage_error_v1` and the real splitter are P0-04 and P0-05 deliverables; nothing here may
be mistaken for them, and nothing here writes a `RESULTS.tsv` row.
"""
import numpy as np
from sklearn.decomposition import non_negative_factorization

__all__ = [
    "training_gene_std",
    "scaled_space_cosine",
    "hvg_retention",
    "poisson_error_floor",
    "donor_blocking_gap",
]


def training_gene_std(counts):
    """Per-gene standard deviation, `ddof=1`, over the training cells (PROTOCOL §3.2).

    `ddof=1` is **measured, not assumed**: dividing the HVG-subset raw counts by
    `std(axis=0, ddof=1)` reproduces upstream's `norm_counts` to a relative Frobenius
    error of 1.7e-14, while `ddof=0` gives 2.0e-4 (PROTOCOL §3.2, SOURCE_AUDIT §1.2).

    Zero-variance genes are floored rather than dropped, because dropping is
    data-dependent and would change the gene panel between folds.
    """
    s = counts.std(axis=0, ddof=1)
    return np.where(s > 0, s, 1.0)


def scaled_space_cosine(true_spectra, counts):
    """Pairwise cosine between true programs **in the space the engine sees**.

    This is the number that decides whether feature A is testable at all. The engine
    divides by per-gene std, and because `s_g ~ mu_g` in this generative model, that
    division acts as a per-gene *mean* normalisation: it cancels the shared background
    and so **amplifies** it relative to the discriminative direction. Programs that look
    well separated in count space can be nearly collinear in scaled space.

    A count-space cosine is therefore not evidence about identifiability. Measured
    separation above ~0.8 here means no grid, fold count or panel fraction rescues
    feature A — record it and stop.
    """
    s = training_gene_std(np.asarray(counts, dtype=float))
    v = np.asarray(true_spectra, dtype=float) / s[None, :]
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    gram = v @ v.T
    k = gram.shape[0]
    off = gram[~np.eye(k, dtype=bool)]
    return {
        "median_pairwise_cosine": float(np.median(off)),
        "max_pairwise_cosine": float(off.max()),
        "count_space_median": _count_space_median(true_spectra),
    }


def _count_space_median(true_spectra):
    """Reported only as a contrast, to keep the gap between the two spaces visible."""
    v = np.asarray(true_spectra, dtype=float)
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    gram = v @ v.T
    k = gram.shape[0]
    return float(np.median(gram[~np.eye(k, dtype=bool)]))


def hvg_retention(dataset, gene_subset):
    """Fraction of each program's markers surviving into a gene panel.

    The failure this guards against is circular and silent: a program that is rare among
    the training donors has low-variance markers, so they are not selected as HVGs, so
    they are absent from the validation panel too — and the held-out donor's distinctive
    program becomes **invisible to the metric**. The benchmark then reports "no
    difference" because the signal was filtered out before scoring.

    Low retention is a reportable finding, not a fold failure. It bites hardest in
    exactly the scenarios feature A needs.
    """
    keep = np.zeros(dataset.adata.n_vars, dtype=bool)
    keep[np.asarray(gene_subset)] = True
    return [float(keep[m].mean()) for m in dataset.marker_sets]


def poisson_error_floor(expected_counts, gene_std, cells, genes):
    """The irreducible error floor, computable exactly because the model is Poisson with
    known `Lambda`: `sum_{g in G_val} Lambda_cg / s_g^2`.

    If observed error at `K_true` sits within a few percent of this **and stays there at
    `K_max`**, the K-curve is flat by arithmetic and no selector can work. That is a
    property of the dataset, not of the method.
    """
    lam = np.asarray(expected_counts)[np.ix_(cells, genes)]
    s = np.asarray(gene_std)[genes]
    return float((lam / s[None, :] ** 2).sum())


def _equal_donor_mean_sse(residual, donor_codes):
    """PROTOCOL §3.5: average within donor first, then unweighted across donors.

    Donors are the independent unit; a 500-cell donor must not outvote a 30-cell donor.
    Implemented as mean-per-cell within donor, then mean over donors.
    """
    per_cell = (residual**2).sum(axis=1)
    return float(np.mean([per_cell[donor_codes == d].mean() for d in np.unique(donor_codes)]))


def donor_blocking_gap(
    dataset, inference_gene_fraction=0.5, seed=0, k_fit=None, n_repeats=5
):
    """**The load-bearing check.** Does donor blocking measurably change held-out error?

    If it does not, feature A has nothing to detect and the scenario parameters are
    wrong — a reportable finding, not something to paper over. The design review
    predicted the *first* draft of the generative model fails this, which is why
    `identity_eligibility` exists (see `simulate.py`).

    THE COMPARISON HAS TO BE PAIRED ON THE TEST CELLS. A first version of this function
    compared a donor-blocked split against a random-cell split and scored each on its own
    held-out cells. That measures how hard the two *test sets* happened to be, not what
    donor blocking does, and it returned a **negative** gap at the development tier — the
    blocked arm looked easier merely because its test set contained fewer donors. The
    corrected design holds the test cells fixed and varies only the training set:

    - `blocked`: train on every cell from the **other** donors
    - `leaky`:   train on a random sample of the same size drawn from a pool that
      **includes the test donors' remaining cells**

    The difference is then exactly the advantage that leakage buys, which is the quantity
    donor blocking exists to remove. A positive gap means donor structure is real and
    feature A has something to detect.

    Each repeat mirrors PROTOCOL §3.3-§3.5: fit on training cells scaled by the
    **training** per-gene std, freeze the dictionary, infer held-out usages by NNLS on the
    *inference* genes only, and score on the disjoint *validation* genes with
    `equal_donor_mean`. The disjoint gene panels are what make the score leakage-free: a
    cell is never scored on the genes used to place it.
    """
    rng = np.random.default_rng(seed)
    counts = np.asarray(dataset.adata.X, dtype=float)
    donors = dataset.adata.obs["donor_id"].to_numpy()
    uniq = np.unique(donors)
    k_fit = k_fit or dataset.true_spectra.shape[0]
    n_cells = len(donors)

    n_inf = int(round(inference_gene_fraction * counts.shape[1]))
    gene_order = rng.permutation(counts.shape[1])
    g_inf, g_val = np.sort(gene_order[:n_inf]), np.sort(gene_order[n_inf:])

    blocked_scores, leaky_scores = [], []
    for _ in range(n_repeats):
        held_donors = set(rng.permutation(uniq)[: len(uniq) // 2])
        from_held = np.array([d in held_donors for d in donors])

        # Only half of each held-out donor's cells are scored, so the other half remains
        # available to leak into the leaky arm's training set.
        held_idx = np.flatnonzero(from_held)
        test_idx = rng.choice(held_idx, size=len(held_idx) // 2, replace=False)
        is_test = np.zeros(n_cells, dtype=bool)
        is_test[test_idx] = True

        blocked_train = ~from_held
        pool = np.flatnonzero(~is_test)
        leaky_train = np.zeros(n_cells, dtype=bool)
        leaky_train[rng.choice(pool, size=int(blocked_train.sum()), replace=False)] = True

        for label, train_mask, store in (
            ("blocked", blocked_train, blocked_scores),
            ("leaky", leaky_train, leaky_scores),
        ):
            store.append(
                _score_split(counts, donors, train_mask, is_test, g_inf, g_val, k_fit, rng)
            )

    blocked = np.array(blocked_scores)
    leaky = np.array(leaky_scores)
    paired = blocked - leaky  # paired on the test cells, so most variance cancels
    return {
        "blocked_mean": float(blocked.mean()),
        "leaky_mean": float(leaky.mean()),
        "relative_gap": float(paired.mean() / leaky.mean()),
        "paired_se": float(paired.std(ddof=1) / np.sqrt(len(paired))) if len(paired) > 1 else float("nan"),
        "paired_t": float(paired.mean() / (paired.std(ddof=1) / np.sqrt(len(paired))))
        if len(paired) > 1 and paired.std(ddof=1) > 0
        else float("nan"),
        "n_repeats": n_repeats,
    }


def _score_split(counts, donors, train_mask, test_mask, g_inf, g_val, k_fit, rng):
    train, test = counts[train_mask], counts[test_mask]
    s = training_gene_std(train)  # training-fitted, never refitted on held-out cells

    x_train = train / s[None, :]
    w, h, _ = non_negative_factorization(
        x_train, n_components=k_fit, init="nndsvd", solver="cd", max_iter=400,
        random_state=int(rng.integers(1 << 31)),
    )

    # Freeze the dictionary; infer held-out usages from the inference genes only.
    x_test = test / s[None, :]
    u_test, _, _ = non_negative_factorization(
        x_test[:, g_inf], H=np.ascontiguousarray(h[:, g_inf]), n_components=k_fit,
        init="custom", update_H=False, solver="cd", max_iter=400,
    )

    residual = x_test[:, g_val] - u_test @ h[:, g_val]
    return _equal_donor_mean_sse(residual, donors[test_mask])
