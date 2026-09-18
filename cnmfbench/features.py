"""Features B and C, as harness-side switches. `src/cnmf/**` is never modified.

The brief requires A, B and C to be independently switchable and forbids changing cNMF's
algorithm or public behaviour. So neither feature edits upstream: B changes **which cells are
handed to `prepare`**, and C changes **how the factor bank is aggregated after `combine`**.
Both leave the engine untouched.

**The load-bearing claim in this module is that C's OFF path reproduces upstream exactly.**
C is a modification of the consensus step, and the consensus step lives in `cnmf.py`, which
cannot be edited. The only way to intervene is to reimplement the aggregation harness-side —
and a reimplementation that silently differs from upstream would make every `000` vs `001`
comparison measure *my reimplementation* rather than feature C. `consensus_spectra_from_bank`
therefore takes a `one_per_run` switch, and `test_features.py` asserts that with the switch
OFF its output matches `cnmf.consensus`'s `median_spectra` to floating-point tolerance on a
real factor bank. If that test fails, C's measured effect is uninterpretable and must not be
reported.

Upstream's aggregation, reproduced here from `cnmf.py:879-916`:

1. `l2_spectra` = rows of `merged_spectra` scaled to unit L2 norm
2. local density filter at `n_neighbors = int(0.30 * n_iter * k / k) = int(0.30 * n_iter)`
3. `KMeans(n_clusters=k, n_init=10, random_state=1)` on the surviving rows
4. `median_spectra` = per-cluster **median**, then rows renormalised to sum to 1

Feature C inserts one step between 3 and 4, and changes nothing else.
"""
import numpy as np
import pandas as pd

from .provisional import provisional

__all__ = [
    "LOCAL_NEIGHBORHOOD_SIZE",
    "run_of",
    "local_density",
    "consensus_spectra_from_bank",
    "DiscoverySample",
    "discovery_sample",
]

# `cnmf.py:879` default. Named rather than inlined so the reproduction is auditable.
LOCAL_NEIGHBORHOOD_SIZE = 0.30


def run_of(labels):
    """Which optimizer run each spectrum came from.

    `merged_spectra` is indexed `iter{N}_topic{M}` (verified on a real bank), so the run is
    the part before the first underscore. Raises on an unrecognised label rather than
    guessing: if upstream ever changes this format, C would silently degrade to "one
    contribution per *something else*", which is the kind of failure that produces a
    plausible number and no error.
    """
    out = []
    for lab in labels:
        s = str(lab)
        if not s.startswith("iter") or "_" not in s:
            raise ValueError(
                f"spectrum label {s!r} is not of the form 'iter<N>_topic<M>'. Feature C "
                "identifies runs from this label; an unrecognised format would make "
                "'one contribution per run' silently mean something else."
            )
        out.append(s.split("_", 1)[0])
    return np.asarray(out)


def local_density(l2_values, n_neighbors):
    """Upstream's local density, reproduced from `cnmf.py:891-899`.

    Mean euclidean distance to the `n_neighbors` nearest other spectra. Note upstream
    partitions on `n_neighbors + 1` (so self, at distance 0, is included in the slice) and
    then divides by `n_neighbors` — that asymmetry is deliberate on upstream's part and is
    preserved exactly, not "corrected".
    """
    from sklearn.metrics.pairwise import euclidean_distances

    dist = euclidean_distances(l2_values)
    order = np.argpartition(dist, n_neighbors + 1)[:, : n_neighbors + 1]
    nearest = dist[np.arange(dist.shape[0])[:, None], order]
    return nearest.sum(1) / n_neighbors


@provisional("features.consensus_c")
def consensus_spectra_from_bank(merged_spectra, k, density_threshold, n_iter,
                                one_per_run=False):
    """Aggregate a factor bank into `median_spectra`. `one_per_run` is feature C.

    Returns `(median_spectra, info)`. With `one_per_run=False` this is upstream's
    computation; a test pins that against `cnmf.consensus` on a real bank.

    **What C does and why.** Upstream takes the median over every spectrum in a cluster. If
    a single optimizer run split one true program into two near-identical factors, both land
    in the same cluster and that run votes **twice**, while a run that found the program once
    votes once. The consensus is then pulled toward whatever the splitting runs produced.
    C gives each run one vote per cluster.

    **Which spectrum survives, a choice the ablation plan does not specify.** The plan says
    only `one_per_run_per_upstream_cluster`. This implementation keeps the member **closest
    to its cluster's centroid** — the run's own best representative of that cluster. The
    alternatives considered were "first by index", which is arbitrary and depends on
    iteration order, and "lowest local density", which would entangle C with the density
    filter it is supposed to be independent of. Recorded in DECISIONS as D015 because it is a
    choice, not a reading of the spec.
    """
    from sklearn.cluster import KMeans

    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    labels = list(merged_spectra.index)
    values = merged_spectra.values.astype(np.float64)
    norms = np.sqrt((values ** 2).sum(axis=1))
    if np.any(norms == 0):
        raise ValueError("a spectrum has zero L2 norm; upstream would divide by zero here")
    l2 = pd.DataFrame(values / norms[:, None], index=labels, columns=merged_spectra.columns)

    n_neighbors = int(LOCAL_NEIGHBORHOOD_SIZE * merged_spectra.shape[0] / k)
    if n_neighbors < 1:
        raise ValueError(
            f"n_neighbors = int(0.30 * {n_iter}) = {n_neighbors} < 1, so upstream's density "
            "estimate divides by zero. Raise optimizer_starts."
        )
    dens = local_density(l2.values, n_neighbors)
    keep = dens < density_threshold
    if keep.sum() == 0:
        raise RuntimeError("Zero components remain after density filtering")
    l2f = l2.loc[keep, :]

    km = KMeans(n_clusters=k, n_init=10, random_state=1).fit(l2f)
    cluster = pd.Series(km.labels_ + 1, index=l2f.index)

    info = {"n_bank": int(merged_spectra.shape[0]), "n_after_density": int(keep.sum()),
            "n_neighbors": n_neighbors, "one_per_run": bool(one_per_run)}

    if one_per_run:
        runs = run_of(l2f.index)
        centroids = km.cluster_centers_
        selected = []
        dropped = 0
        arr = l2f.values
        for c in np.unique(cluster.values):
            idx = np.flatnonzero(cluster.values == c)
            d = np.linalg.norm(arr[idx] - centroids[c - 1], axis=1)
            best = {}
            for pos, dist in zip(idx, d):
                r = runs[pos]
                if r not in best or dist < best[r][1]:
                    best[r] = (pos, dist)
            chosen = sorted(p for p, _ in best.values())
            dropped += len(idx) - len(chosen)
            selected.extend(chosen)
        selected = np.sort(np.asarray(selected))
        l2f = l2f.iloc[selected]
        cluster = cluster.iloc[selected]
        info["n_dropped_duplicate_contributions"] = int(dropped)
        info["n_after_dedup"] = int(len(selected))

    median_spectra = l2f.groupby(cluster).median()
    median_spectra = (median_spectra.T / median_spectra.sum(1)).T
    return median_spectra, info


# ------------------------------------------------------------------ feature B


class DiscoverySample:
    """The cells handed to `prepare`, and the record of how they were chosen."""

    def __init__(self, cell_ids, mode, budget, per_donor):
        self.cell_ids = list(cell_ids)
        self.mode = mode
        self.budget = int(budget)
        self.per_donor = dict(per_donor)

    def __len__(self):
        return len(self.cell_ids)


@provisional("features.discovery_sample_b")
def discovery_sample(cell_ids, donor_ids, budget, equal_per_donor, seed):
    """Choose the discovery cells. `equal_per_donor` is feature B.

    Both arms draw **the same number of cells**, because the ablation plan puts B in the
    `matched_budget` arm: a B that simply used more cells would be measuring sample size.

    - B OFF, `proportional_without_replacement`: each donor contributes in proportion to how
      many cells it has, which is what using the training pool as-is already does.
    - B ON, `equal_per_donor_without_replacement`: every donor contributes the same number,
      so a donor with 10x the cells no longer has 10x the influence on which programs are
      discovered.

    A donor holding fewer cells than its equal share contributes all of them, and the
    shortfall is redistributed over the donors that still have spare cells. Without that,
    `equal_per_donor` would silently shrink the budget whenever donors are uneven and the two
    arms would no longer be matched — which is the comparison's whole premise.

    The draw is seeded and independent of rank and optimizer seed, satisfying the plan's
    `hold_discovery_cells_constant_across_rank_and_optimizer_seeds`.
    """
    cell_ids = np.asarray([str(c) for c in cell_ids])
    donor_ids = np.asarray([str(d) for d in donor_ids])
    if cell_ids.shape != donor_ids.shape:
        raise ValueError(f"{cell_ids.size} cells but {donor_ids.size} donor labels")
    budget = int(budget)
    if not 0 < budget <= cell_ids.size:
        raise ValueError(f"budget {budget} outside 1..{cell_ids.size}")

    rng = np.random.default_rng(seed)
    donors = sorted(set(donor_ids.tolist()))
    pools = {d: np.sort(np.flatnonzero(donor_ids == d)) for d in donors}

    if not equal_per_donor:
        # Proportional: a uniform draw from the pooled cells IS proportional sampling, and
        # saying so is clearer than computing per-donor quotas that only reproduce it.
        take = rng.choice(cell_ids.size, size=budget, replace=False)
        chosen = np.sort(take)
    else:
        remaining = {d: pools[d].size for d in donors}
        quota = {d: 0 for d in donors}
        left, active = budget, [d for d in donors if remaining[d] > 0]
        while left > 0 and active:
            share = max(1, left // len(active))
            for d in list(active):
                if left <= 0:
                    break
                give = min(share, remaining[d], left)
                quota[d] += give
                remaining[d] -= give
                left -= give
                if remaining[d] == 0:
                    active.remove(d)
        picked = []
        for d in donors:
            if quota[d]:
                picked.append(rng.choice(pools[d], size=quota[d], replace=False))
        chosen = np.sort(np.concatenate(picked)) if picked else np.array([], dtype=int)

    if chosen.size != budget:
        raise AssertionError(
            f"drew {chosen.size} cells against a budget of {budget}; the arms would not be "
            "matched and the comparison would confound B with sample size"
        )
    ids = cell_ids[chosen]
    per_donor = {d: int((donor_ids[chosen] == d).sum()) for d in donors}
    mode = ("equal_per_donor_without_replacement" if equal_per_donor
            else "proportional_without_replacement")
    return DiscoverySample(ids, mode, budget, per_donor)
