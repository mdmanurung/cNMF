"""Reading the evidence back, with the one guard the schema cannot express.

`RESULTS.tsv` is tidy and invites `groupby(metric).mean()`. Across outer folds that
returns a meaningless number, because each fold refits its own gene panel and its own
per-gene scale: PROTOCOL §3.2 requires `G` to be "computed on training donors only,
frozen for the fold", so two folds are not measuring on a common axis.

Measured on the skeleton's SMOKE run: `Jaccard(G_0, G_1) = 0.639` — the folds shared 78
of 100 genes and had different `s_g`. Nothing in the 19 columns flags it.

The information needed to catch this is already recorded: `preprocessing_hash` includes
the hash of the fold's gene list, so it differs whenever the axes differ. What was missing
was anything that *used* it. That is all this module is.
"""
import csv

__all__ = ["PoolingError", "load_rows", "assert_poolable", "pooling_groups"]


class PoolingError(ValueError):
    """Rows that are not on a common measurement axis were about to be aggregated."""


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _preprocessing_by_experiment(experiments):
    return {e["experiment_id"]: e["preprocessing_hash"] for e in experiments}


def assert_poolable(rows, experiments):
    """Raise unless every row shares one `preprocessing_hash`.

    Call this before any aggregation that crosses rows. It is deliberately strict: a
    caller that genuinely wants a cross-fold summary should say so by aggregating the
    groups from `pooling_groups` separately and reporting them separately, not by
    silencing a check.
    """
    lookup = _preprocessing_by_experiment(experiments)
    missing = sorted({r["experiment_id"] for r in rows} - set(lookup))
    if missing:
        raise PoolingError(
            f"{len(missing)} row(s) reference an experiment_id absent from EXPERIMENTS.tsv, "
            f"first {missing[0]}. Provenance cannot be checked, so pooling is refused."
        )
    hashes = {lookup[r["experiment_id"]] for r in rows}
    if len(hashes) > 1:
        raise PoolingError(
            f"rows span {len(hashes)} distinct preprocessing_hash values, so they were "
            "fitted on different gene panels and per-gene scales and are not on a common "
            "axis. Averaging them produces a number that describes no measurement. "
            "Aggregate within each group instead — see pooling_groups()."
        )
    return True


def pooling_groups(rows, experiments):
    """Partition rows into groups that *are* on a common axis, keyed by
    `preprocessing_hash`. Aggregate within a group; report groups side by side."""
    lookup = _preprocessing_by_experiment(experiments)
    groups = {}
    for r in rows:
        groups.setdefault(lookup.get(r["experiment_id"], "UNKNOWN"), []).append(r)
    return groups
