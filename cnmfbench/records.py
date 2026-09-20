"""The two row schemas, their controlled vocabularies, provenance, and safe writing.

`RESULTS.tsv` and `EXPERIMENTS.tsv` shipped as header-only files with no code behind
them and no vocabulary for several load-bearing columns. What this module invents is
recorded in DECISIONS rather than added to `PROTOCOL.md`, whose bytes are hashed into
`ablation_plan.yaml` — editing it would create a new protocol version (§9).

Three conventions worth reading before use:

- **`NOT_COMPUTED`, never a blank**, where a value genuinely cannot be produced. An empty
  TSV cell is indistinguishable from a quoting bug, a legitimate null, and a forgotten
  column. A true null (`selected_rank` on a fixed-rank row, §5.3) *is* the empty string,
  and that distinction is the point.
- **`experiment_id` is deterministic**, derived from the inputs. A uuid or timestamp
  makes re-run duplication, partial-fold truncation and concurrent interleaving all
  undetectable — and `RESULTS.tsv` has no `dataset_manifest_hash` column, so
  `experiment_id` is its only join to provenance.
- **`n_eligible_units` / `n_failed_units` count the units aggregated into that row's own
  value** — cells for a per-donor row, donors for an aggregate row. §4.3 counts cells and
  §3.5 counts donors in the same column, and this is the only rule satisfying both.
  Aggregating without filtering on `evaluation_scope` double-counts cells against donors.
"""
import csv
import os
import platform
import subprocess
import sys

from . import METRIC_DEFINITION_VERSION, PROTOCOL_VERSION, UPSTREAM_CNMF_SHA
from .hashing import artifact_hash, parameter_hash

__all__ = [
    "RESULTS_COLUMNS",
    "EXPERIMENTS_COLUMNS",
    "METRIC_DIRECTION",
    "RESULT_STATUS",
    "EXPERIMENT_STATUS",
    "EVALUATION_SCOPE",
    "ARM",
    "NOT_COMPUTED",
    "make_experiment_id",
    "result_row",
    "experiment_row",
    "environment_hash",
    "preprocessing_hash",
    "protocol_hash",
    "contract_hash",
    "implementation_sha",
    "write_rows",
    "merge_into_tracked",
]

NOT_COMPUTED = "NOT_COMPUTED"

RESULTS_COLUMNS = (
    "experiment_id", "configuration", "arm", "dataset_id", "independent_unit_id",
    "independent_unit_type", "outer_split_id", "metric", "metric_definition_version",
    "value", "direction", "stratum", "evaluation_scope", "candidate_rank",
    "selected_rank", "n_eligible_units", "n_failed_units", "status", "artifact_path",
)

EXPERIMENTS_COLUMNS = (
    "experiment_id", "prototype", "feature_A", "feature_B", "feature_C", "arm", "status",
    "evidence_tier", "dataset_id", "dataset_manifest_hash", "simulation_replicate",
    "outer_split_id", "inner_split_id", "mask_id", "sampling_replicate", "optimizer_seed",
    "candidate_rank", "selected_rank", "protocol_hash", "contract_hash", "upstream_sha",
    "implementation_sha_or_patch_hash", "environment_hash", "preprocessing_hash",
    "discovery_cells_hash", "factor_bank_hash", "artifact_dir", "command", "started_utc",
    "finished_utc", "exit_code", "wall_seconds", "cpu_seconds", "peak_memory_mb",
    "memory_scope", "failure_reason", "notes",
)

# PROTOCOL §5.2, twelve names at metric_definition_version 2 (v1.2 adds the
# gene-set sibling for whole-workflow comparator rows; §5.1 still forbids names
# not on this list). The direction strings are §5.1's forms.
METRIC_DIRECTION = {
    "heldout_squared_prediction_error_v1": "lower_is_better",
    "heldout_squared_prediction_error_counts_v1": "lower_is_better",
    "null_squared_prediction_error_v1": "lower_is_better",
    "program_recovery_cosine_v1": "higher_is_better",
    "program_precision_v1": "higher_is_better",
    "program_recall_v1": "higher_is_better",
    "program_recovery_jaccard_v1": "higher_is_better",
    "usage_error_v1": "lower_is_better",
    "wall_seconds_v1": "lower_is_better",
    "cpu_seconds_v1": "lower_is_better",
    "peak_memory_mb_v1": "lower_is_better",
    "failed_fits_v1": "lower_is_better",
}

# `ok_provisional` is what the fence writes; plain `ok` is reserved for rows produced by
# hardened components, so the two are distinguishable in the evidence itself.
RESULT_STATUS = ("ok", "ok_provisional", "fit_failed", "scoring_failed",
                 "selector_failed", "selector_refused")
EXPERIMENT_STATUS = ("completed", "failed")
EVALUATION_SCOPE = ("per_donor", "equal_donor_mean", "experiment")

# `full_training_pool`, not `matched_budget`: the skeleton uses every training-donor cell
# with no budget, which is `upstream_full_data`'s definition applied to a training fold.
# Calling it matched_budget would silently confound the future B comparison.
ARM = ("full_training_pool", "matched_budget", "upstream_full_data", "genenmf_native")


def make_experiment_id(configuration, arm, dataset_id, outer_split_id, candidate_rank, seeds,
                       variant=None, inner_split_id=None, selected_rank=None):
    """Readable and deterministic. Same inputs ⇒ same id ⇒ a re-run is detectable.

    The trailing 12 hex characters disambiguate runs that differ only in seeds. §7's
    no-truncation rule governs hash *columns*; this is an identifier that embeds one, and
    the full provenance hashes live in `EXPERIMENTS.tsv` beside it.

    **`variant` exists because the invariant above was violated.** The convergence diagnostic
    re-ran the DEVELOPMENT tier with `max_optimizer_iterations` 300 → 1000: same configuration,
    same arm, same dataset (`dataset_manifest_hash` identical — it genuinely is the same data),
    same seeds, **different numbers**. None of this function's other inputs moved, so both runs
    produced the same id, and `merge_into_tracked` correctly refused the second as a
    contradiction. `preprocessing_hash` did differ, so the rows were distinguishable by
    content but not by name.

    A run that changes a factorization parameter while reusing a tier's identity must say so.
    `variant` is that label, and it is folded into the digest **only when set**, so every id
    written before it existed stays valid and no evidence needs regenerating. `dataset_id`
    would have been the wrong place — the dataset is the same — and `arm` is a frozen protocol
    vocabulary, not a scratchpad for diagnostics.

    **`inner_split_id` exists for the same reason, pre-emptively (D020 sub-problem 8).**
    `_run_inner_fold` fits and scores per `(outer_split_id, inner_split_id, candidate_rank)`,
    but     none of those three vary across two inner folds of the same outer fold at the same
    rank without it — two such inner folds would collide on `experiment_id` today, exactly
    the way the `variant` docstring above describes for a different axis. Folded into the
    digest **only when set**, so every id written before it existed stays valid.
    """
    payload = {
        "configuration": configuration, "arm": arm, "dataset_id": dataset_id,
        "outer_split_id": outer_split_id,
        "candidate_rank": None if candidate_rank is None else int(candidate_rank),
        "seeds": {k: int(v) for k, v in sorted(seeds.items())},
        "protocol_version": PROTOCOL_VERSION,
    }
    if variant:
        payload["variant"] = str(variant)
    if inner_split_id:
        payload["inner_split_id"] = str(inner_split_id)
    if selected_rank not in (None, ""):
        # A selected-rank row evaluates the selected rank; a fixed-rank row with
        # the same candidate rank is a different experiment (D020's identity
        # invariant: same id ⇒ same experiment). Folded in only when set, so
        # every fixed-rank id written before P1-02 stays bit-identical.
        payload["selected_rank"] = int(selected_rank)
    digest = parameter_hash(payload)
    rank = "fit" if candidate_rank is None else f"k{int(candidate_rank)}"
    label = f"{dataset_id}-{variant}" if variant else dataset_id
    label = f"{label}-{inner_split_id}" if inner_split_id else label
    if selected_rank not in (None, ""):
        label = f"{label}-sel{int(selected_rank)}"
    return f"{configuration}-{arm}-{label}-{outer_split_id}-{rank}-{digest[:12]}"


def _clean(value, column):
    """Render one cell. Rejects the strings that look like data but are accidents."""
    if value is None:
        return ""
    text = str(value)
    if text.strip().lower() in {"none", "nan", "null", "na", "<na>"}:
        raise ValueError(
            f"column {column!r} would be written as {text!r}. Use '' for a true null "
            f"(e.g. selected_rank on a fixed-rank row) or {NOT_COMPUTED!r} for a value "
            "that could not be produced."
        )
    if "\t" in text or "\n" in text:
        raise ValueError(f"column {column!r} contains a tab or newline: {text!r}")
    return text


def result_row(**kw):
    """Build and validate one `RESULTS.tsv` row."""
    metric = kw.get("metric")
    if metric not in METRIC_DIRECTION:
        raise ValueError(
            f"metric {metric!r} is not one of PROTOCOL §5.2's 11 names. §5.1 forbids "
            "writing a name not listed there."
        )
    kw.setdefault("direction", METRIC_DIRECTION[metric])
    if kw["direction"] != METRIC_DIRECTION[metric]:
        raise ValueError(
            f"direction {kw['direction']!r} contradicts §5.2 for {metric!r} "
            f"({METRIC_DIRECTION[metric]!r})"
        )
    if kw.get("status") not in RESULT_STATUS:
        raise ValueError(f"status {kw.get('status')!r} not in {RESULT_STATUS}")
    if kw.get("evaluation_scope") not in EVALUATION_SCOPE:
        raise ValueError(f"evaluation_scope {kw.get('evaluation_scope')!r} not in {EVALUATION_SCOPE}")
    if kw.get("arm") not in ARM:
        raise ValueError(f"arm {kw.get('arm')!r} not in {ARM}")

    # §5.3: fixed-rank arms leave selected_rank null with a success status. A
    # selected-rank row (P1-02: the rank the arm's assigned selector chose,
    # evaluated at exactly that rank) carries selected_rank == candidate_rank.
    # Anything else — a selected rank that was not the evaluated rank — is refused,
    # because it would describe an evaluation that never happened.
    selected = kw.get("selected_rank")
    if selected not in (None, ""):
        if str(selected) != str(kw.get("candidate_rank")):
            raise ValueError(
                f"selected_rank {selected!r} != candidate_rank "
                f"{kw.get('candidate_rank')!r}: a selected-rank row evaluates the "
                "selected rank, never another rank."
            )
    kw.setdefault("metric_definition_version", METRIC_DEFINITION_VERSION)
    kw.setdefault("stratum", "all")
    kw.setdefault("selected_rank", None)

    missing = set(RESULTS_COLUMNS) - set(kw)
    if missing:
        raise ValueError(f"missing RESULTS columns: {sorted(missing)}")
    extra = set(kw) - set(RESULTS_COLUMNS)
    if extra:
        raise ValueError(f"unknown RESULTS columns: {sorted(extra)}")
    return {c: _clean(kw[c], c) for c in RESULTS_COLUMNS}


def experiment_row(**kw):
    """Build and validate one `EXPERIMENTS.tsv` row."""
    if kw.get("status") not in EXPERIMENT_STATUS:
        raise ValueError(f"status {kw.get('status')!r} not in {EXPERIMENT_STATUS}")
    if kw.get("arm") not in ARM:
        raise ValueError(f"arm {kw.get('arm')!r} not in {ARM}")
    kw.setdefault("selected_rank", None)
    missing = set(EXPERIMENTS_COLUMNS) - set(kw)
    if missing:
        raise ValueError(f"missing EXPERIMENTS columns: {sorted(missing)}")
    extra = set(kw) - set(EXPERIMENTS_COLUMNS)
    if extra:
        raise ValueError(f"unknown EXPERIMENTS columns: {sorted(extra)}")
    return {c: _clean(kw[c], c) for c in EXPERIMENTS_COLUMNS}


# --------------------------------------------------------------------------- provenance

def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def protocol_hash():
    """§7 'this file': sha256 over `PROTOCOL.md`'s bytes, as an artifact hash.

    §7's table is internally inconsistent — row 1 lists `protocol_hash` as
    parameter-like, row 4 gives the file itself the artifact rule. File-bytes is chosen
    because it is the only version `sha256sum docs/planning/PROTOCOL.md` can verify, which
    is what the tracker's own resume instruction tells a reader to run. Recorded as a
    convention in DECISIONS; `PROTOCOL.md` is not edited.
    """
    return artifact_hash(os.path.join(_repo_root(), "docs/planning/PROTOCOL.md"))


def contract_hash(ablation_plan):
    """Parameter hash over the frozen validation and gate blocks of `ablation_plan.yaml`."""
    return parameter_hash(
        {
            "validation": ablation_plan.get("validation", {}),
            "scientific_gates": ablation_plan.get("scientific_gates", {}),
            "feature_contracts_present": [],  # contracts/{A,B,C}.md do not exist yet
        }
    )


def environment_hash():
    """Parameter hash over the interpreter, the libraries that affect numerics, and the
    BLAS thread pinning — which belongs here because it changes `cpu_seconds_v1`."""
    import anndata, numpy, pandas, scipy, sklearn  # noqa: E401

    return parameter_hash(
        {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
            "pandas": pandas.__version__,
            "anndata": anndata.__version__,
            "upstream_cnmf_sha": UPSTREAM_CNMF_SHA,
            "threads": {
                v: os.environ.get(v, "")
                for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
            },
        }
    )


def preprocessing_hash(spec):
    """Parameter hash over everything that determines `G`, `s_g` and the panels.

    This is the object that later answers "were the panels identical across arms?", so it
    must include the gene list itself and not merely the parameters that produced it.
    """
    return parameter_hash(spec)


def implementation_sha():
    """`git rev-parse HEAD`, marked dirty with a hash of the diff if the tree is not clean."""
    root = _repo_root()
    head = subprocess.run(
        ["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    porcelain = subprocess.run(
        ["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout
    if not porcelain.strip():
        return head
    diff = subprocess.run(
        ["git", "-C", root, "diff", "HEAD"], capture_output=True, text=True, check=True
    ).stdout
    return f"{head}-dirty-{parameter_hash({'diff': diff})[:16]}"


# ------------------------------------------------------------------------------ writing

def write_rows(path, rows, columns):
    """Write a per-run shard atomically, header included."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns), delimiter="\t",
                                lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def merge_into_tracked(tracked_path, rows, columns):
    """Append shard rows into a tracked TSV, atomically and without duplicates.

    Deliberately a separate, explicit step rather than something a run does as it goes:
    a crashed run must leave version-controlled evidence untouched, and appending from
    two processes at once must be a detectable contradiction rather than a silent second
    opinion. Refuses on a duplicate `experiment_id` + `metric` pair rather than
    overwriting, because the same id with a different value is exactly the case worth
    stopping for.
    """
    with open(tracked_path, newline="", encoding="utf-8") as fh:
        existing = list(csv.DictReader(fh, delimiter="\t"))
        header_ok = list(csv.reader(open(tracked_path, encoding="utf-8"), delimiter="\t"))[0]
    if tuple(header_ok) != tuple(columns):
        raise ValueError(f"{tracked_path} header does not match the expected schema")

    def key(r):
        return (r["experiment_id"], r.get("metric", ""), r.get("independent_unit_id", ""))

    seen = {key(r) for r in existing}
    clashes = sorted({key(r) for r in rows} & seen)
    if clashes:
        raise ValueError(
            f"{len(clashes)} row(s) already present in {tracked_path}, first {clashes[0]}. "
            "Refusing to append: a repeated id with a possibly different value is a "
            "contradiction to resolve, not a duplicate to tolerate."
        )

    tmp = f"{tracked_path}.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns), delimiter="\t",
                                lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(existing)
        writer.writerows(rows)
    os.replace(tmp, tracked_path)
    return len(rows)
