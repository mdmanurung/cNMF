"""Donor folds and frozen gene panels (PROTOCOL §4.1).

Two rules here are easy to violate silently and both were violated by the reference
implementation this module replaces:

1. **The panel seed is independent of the sampling and optimizer seeds** (§4.1). The
   throwaway `diagnostics.donor_blocking_gap` draws the gene panel from the *same* `rng`
   as the donor permutation (`diagnostics.py:163-173`), which couples panel variation to
   split variation so neither can be attributed. The tracker tells the next session to
   read that function first, so the trap is worth naming where the correct version lives.
2. **`mask_id` hashes the realised panel, not the seed.** A seed only identifies a panel
   if every implementation derives the panel from it identically. Hashing the gene names
   makes §4.1's "identical panels across all candidate ranks and configurations" a string
   comparison instead of a promise.

Donors, never cells, are the unit of the outer split — cells from one donor must stay
together (`ablation_plan.yaml: keep_repeated_measurements_together`).
"""
from collections import namedtuple

import numpy as np

from . import PROTOCOL_VERSION
from .hashing import cell_set_hash, parameter_hash
from .provisional import provisional

__all__ = ["DonorFold", "Panel", "outer_donor_folds", "gene_panel"]

DonorFold = namedtuple("DonorFold", "outer_split_id train_donors test_donors")
Panel = namedtuple("Panel", "mask_id inference_genes validation_genes")


@provisional("splits.outer_donor_folds")
def outer_donor_folds(donor_ids, n_folds, seed):
    """Partition unique donors into `n_folds` blocks; each donor is a test donor once.

    Deterministic from `sorted(set(donor_ids))` and `seed`, using `default_rng` rather
    than the legacy global RNG — `cnmf.prepare` calls `np.random.seed()` internally
    (`cnmf.py:601`), so anything reading global NumPy state would shift depending on
    whether a fit had already run.

    **The split must never be rerolled to balance program carriers across folds.** Doing
    so uses ground truth to choose a split, which §6.3 forbids; an unlucky split is a
    recorded property of the run, not something to fix.
    """
    donors = sorted(set(str(d) for d in donor_ids))
    if n_folds < 2 or n_folds > len(donors):
        raise ValueError(f"n_folds={n_folds} is not usable with {len(donors)} donors")

    order = np.random.default_rng(seed).permutation(len(donors))
    shuffled = [donors[i] for i in order]
    blocks = [sorted(shuffled[i::n_folds]) for i in range(n_folds)]

    folds = []
    for i, test in enumerate(blocks):
        train = sorted(d for d in donors if d not in set(test))
        if not train or not test:
            raise ValueError(f"fold {i} is degenerate: {len(train)} train, {len(test)} test")
        folds.append(DonorFold(f"outer_{i}", tuple(train), tuple(test)))
    return folds


@provisional("splits.gene_panel")
def gene_panel(gene_labels, inference_gene_fraction, panel_seed, repetition=0):
    """Split `G` into `G_inf ⊔ G_val` (§4.1).

    `gene_labels` is `G` in cNMF's `nmf_genes_list` order. The permutation is taken over
    a lexicographically sorted copy so the panel is a pure function of
    `(set(G), panel_seed, repetition)` rather than of cNMF's Fano ranking — otherwise the
    "same" seed yields different panels whenever the ranking shifts, and `mask_id` stops
    meaning anything. This is a reproducibility argument, not a bias argument.

    Panels are **not** conditioned on expression level: §4.2 forbids it, because a
    panel chosen by expression would put zeros and nonzeros in different panels and an
    observed zero is data, not a missing value.
    """
    labels = [str(g) for g in gene_labels]
    if len(set(labels)) != len(labels):
        raise ValueError("duplicate gene labels in G")
    if not 0.0 < inference_gene_fraction < 1.0:
        raise ValueError("inference_gene_fraction must lie strictly in (0, 1)")

    ordered = sorted(labels)
    rng = np.random.default_rng(np.random.SeedSequence([int(panel_seed), int(repetition)]))
    permuted = [ordered[i] for i in rng.permutation(len(ordered))]

    n_inf = int(round(inference_gene_fraction * len(ordered)))
    if n_inf == 0 or n_inf == len(ordered):
        raise ValueError(
            f"inference_gene_fraction={inference_gene_fraction} leaves an empty panel "
            f"at |G|={len(ordered)}"
        )
    inference = tuple(sorted(permuted[:n_inf]))
    validation = tuple(sorted(permuted[n_inf:]))

    mask_id = parameter_hash(
        {
            # The realised panel, not the seed that produced it.
            "inference_genes": cell_set_hash(inference),
            "validation_genes": cell_set_hash(validation),
            "inference_gene_fraction": float(inference_gene_fraction),
            "panel_seed": int(panel_seed),
            "repetition": int(repetition),
            "protocol_version": PROTOCOL_VERSION,
        }
    )
    return Panel(mask_id=mask_id, inference_genes=inference, validation_genes=validation)
