# Decision log

This is an append-only record of planned design decisions, later implementation decisions, deviations, and scientific adoption results. Do not overwrite older decisions after seeing new outcomes.

## D000 — First-cycle scope

Date: 2026-09-15  
Type: planning specification, not an empirical finding

Decision: use P0 for an unchanged cNMF baseline and shared benchmark infrastructure, then evaluate A (predictive rank selection), B (donor-balanced discovery), and C (run-aware consensus) as independent switches; test all eight combinations and retain a separate full-data legacy anchor.

Reason: limit confounding between simultaneous methodological changes and preserve the ability to identify standalone, incremental, and interaction effects.

Evidence: user-approved incremental design; no package implementation or benchmark execution has occurred in this bundle.

Scientific adoption: NOT_EVALUATED for all three features.

## D001 — Layout kept under `docs/`; executable trees go at repo root

Date/time: 2026-09-15, S0-01 session
Type: implementation
Related task, feature, gate: S0-01
Context: the brief's canonical layout puts `planning/`, `benchmarks/` at repo root. This checkout already has them pre-scaffolded under `docs/planning/`, `docs/benchmarks/`, and `docs/AGENTS.md` was already merged with pre-existing instructions there. `docs/AGENTS.md` line 7 refers to `planning/PROGRESS.md` as a bare path.
Options considered: (a) move `docs/planning/` and `docs/benchmarks/` to repo root to match the brief literally; (b) leave them under `docs/` since that is where the user/prior session placed them, and adapt only the not-yet-created executable trees (`workflow/`, `src/cnmf/experimental/`, `tests/` additions) to repo root as the brief specifies.
Decision: (b). Do not move existing tracked files in a clean tree without cause. `planning/`, `benchmarks/` stay under `docs/`. New executable trees (`workflow/Snakefile`, `workflow/rules/`, `workflow/scripts/`, `src/cnmf/experimental/`) go at repo root when created, matching the brief's command examples with a `docs/` prefix inserted for config/benchmark paths, e.g. `--configfile docs/benchmarks/configs/smoke.yaml` instead of the brief's literal `benchmarks/configs/smoke.yaml`.
Evidence paths and experiment IDs: docs/planning/, docs/benchmarks/ (pre-existing, unmodified by this decision).
Trade-offs and negative evidence: a reader following the brief's literal file paths verbatim will get `FileNotFoundError`; mitigated by this decision entry and by keeping `docs/AGENTS.md`'s resume instructions in sync going forward.
Consequences for the baseline and active feature set: none (organizational only).
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D002 — Upstream identity: local checkout HEAD equals resolved `dylkot/cNMF` HEAD

Date/time: 2026-09-15, S0-01 session
Type: implementation / protocol
Related task, feature, gate: S0-01, S0-02, P0-01
Context: `origin` for this checkout is `git@github.com:mdmanurung/cNMF.git`, not `dylkot/cNMF`, and the four most recent commits (`5dbc5ba`, `bc797f2`, `221a3c3`, `d5c7a45`) touch the preprocessing path that P0.4's transform contract depends on. `git log -4 --format='%H %an <%ae>'` confirms all four are authored by `Dylan Kotliar <dylkot@gmail.com>` — i.e. this is a synced fork with zero local modifications, not a fork carrying the checkout owner's own patches. The brief's "target: `dylkot/cNMF`" and "keep an isolated upstream invocation as the reference" language raised the question of whether P0.1 needs a second, separate `dylkot/cNMF` checkout to diff against.
Options considered: (a) treat `dylkot/cNMF` at a freshly resolved SHA as upstream and this checkout as a diverged fork requiring reconciliation; (b) resolve `dylkot/cNMF`'s actual current SHA via `git ls-remote` and compare directly against local HEAD before assuming divergence.
Decision: (b), executed. `git ls-remote https://github.com/dylkot/cNMF HEAD` returned `5dbc5baaa0b9079b55bce554d801caa235a50457`; `git rev-parse HEAD` on the local checkout returned the identical SHA, and all four recent commits are Dylan-Kotliar-authored. **There is no divergence.** This checkout's HEAD *is* the current `dylkot/cNMF` default-branch HEAD — it is a synced fork with zero local modifications, not a fork carrying the checkout owner's own patches on top of it. No second isolated upstream checkout is required for P0.1; this working tree serves as both the implementation base and the pinned upstream reference, pending only a reproducible environment (P0-01, currently BLOCKED — see SOURCE_AUDIT.md §1.4).
Evidence paths and experiment IDs: `git ls-remote https://github.com/dylkot/cNMF HEAD` output; `git rev-parse HEAD` output; both recorded in docs/planning/SOURCE_AUDIT.md §1.
Trade-offs and negative evidence: this is a point-in-time fact — if upstream `dylkot/cNMF` advances past this SHA in a later session, the identity no longer holds and this decision must be superseded, not silently reused.
Consequences for the baseline and active feature set: P0.1 step 5 ("keep an isolated upstream invocation as the reference") is satisfied trivially by this checkout at this commit; the full-data all-off reproducibility check compares this checkout's output against itself run twice (same-environment tolerance), not against a separately cloned repository.
Protocol/data versions superseded: none.
Independent confirmation needed: re-verify `git ls-remote` if this decision is relied upon in a future session more than a few weeks later, or before any confirmatory (sealed) run.

## D003 — P0-01 (environment) runs before S0-03 (PROTOCOL.md): deliberate dependency inversion

Date/time: 2026-09-15, S0/P0 planning session
Type: protocol / deviation
Related task, feature, gate: S0-03, P0-01
Context: the task ledger in PROGRESS.md declares `P0-01 depends on S0-03`, i.e. freeze the benchmark protocol before building the runnable environment. Two facts argue against executing in that order. First, no claim in PROTOCOL.md can be validated — or even executed once — without a Python environment, so freezing it first means freezing untested assertions. Second, `SOURCE_AUDIT.md` §1.2 was written entirely from reading source; running the upstream test suite is the cheapest available empirical check on those claims, and two specific risks (upstream reference artifacts generated at cNMF 1.6.0 versus this checkout's 1.7.1; consensus artifacts derived from an unseeded NNLS refit) can only be characterised by execution.
Options considered: (a) follow the declared order — write and freeze PROTOCOL.md from the source audit alone, then build the environment; (b) invert — build the environment, reproduce upstream, measure the two risks, then write PROTOCOL.md grounded in observed artifacts.
Decision: (b), with the user's explicit approval. P0-01 executes first. S0-03 follows in the next session.
**Guard clause:** environment and tooling findings may inform *feasibility and numerical tolerances* only. They must not be used to select scientific endpoints, decision margins, the baseline rank-selection surrogate, or any comparison that a feature will later be judged against. If an environment finding appears to bear on a scientific choice, it is recorded here as a separate decision rather than folded silently into PROTOCOL.md.
Evidence paths and experiment IDs: none yet — this decision authorises the work, it does not report it. Evidence will land in `docs/benchmarks/registry/` and PROGRESS.md §9.
Trade-offs and negative evidence: the stated risk of the declared order is that tooling drives science. The guard clause above is the mitigation. The residual risk is that having seen upstream's actual numerical behaviour, the protocol author is no longer blind to it when choosing tolerances — this is accepted deliberately, because a tolerance chosen without observing machine behaviour is not meaningful.
Consequences for the baseline and active feature set: none — P0 changes no algorithm. Ledger dependency `P0-01 depends on S0-03` is superseded by this entry; PROGRESS.md §4 should be read with this decision in hand.
Protocol/data versions superseded: none (no protocol exists yet).
Independent confirmation needed: no.

## D004 — Reproducibility comparisons use relative Frobenius error (1e-5), not upstream's absolute SSE budget

Date/time: 2026-09-15, P0-01 session
Type: protocol
Related task, feature, gate: P0-01, P0-04, gate P0
Context: `tests/test_reproducibility.py` compares artifacts with `TOLERANCE = 1e-4` applied to `((test - ref)**2).sum().sum()` — an **absolute** sum of squared error over the whole matrix (the variable is named `rms` but has neither a square root nor a division by N). This budget is scale- and size-blind. Measured consequence at the pinned SHA (SOURCE_AUDIT §1.5.2): `gene_spectra_tpm` on the simulated dataset agrees with the reference to a **relative** Frobenius error of 1.4e-6 — scientifically exact — yet fails, because TPM-unit entries reach 6.3e4 so the absolute SSE is 0.0718. Meanwhile `norm_counts` (the actual solver input) and `consensus_spectra` are bitwise identical, and all exact-equality artifacts match.
Options considered: (a) adopt upstream's absolute SSE budget for our harness, for consistency with upstream; (b) loosen the absolute budget until the failing case passes; (c) compare on relative Frobenius error with an explicit threshold, and report bitwise identity separately where it holds.
Decision: (c). Our harness compares artifacts by **relative Frobenius error with a threshold of 1e-5**, applied per artifact, and additionally reports bitwise identity where achieved. We do **not** reuse upstream's `TOLERANCE = 1e-4` as a correctness criterion, and we do not modify upstream's test.
Reason: (a) would make correctness depend on the physical units of an artifact — a TPM-scale matrix and a sum-to-1 matrix would face effectively different standards for the same relative accuracy. (b) is tuning a threshold to make a specific failure disappear, which is exactly the practice the brief forbids.
Evidence paths and experiment IDs: `docs/benchmarks/registry/p0-01_pytest_run1.log`; comparison table in `docs/planning/SOURCE_AUDIT.md` §1.5.2; determinism evidence in `docs/benchmarks/registry/nondeterminism_probe.tsv`.
Trade-offs and negative evidence: relative error is undefined/unstable for artifacts that are all-zero or near-zero, so an absolute floor may need to be added for such cases — not required by any artifact observed so far, and to be added as a superseding decision if one appears. The 1e-5 threshold is itself a judgement: it sits ~7× above the largest relative discrepancy observed (1.4e-6) and ~1000× below a level that would mask a structural difference. It is a **same-environment** tolerance; no bitwise-identity claim is made across BLAS implementations, library versions, thread counts or platforms.
Consequences for the baseline and active feature set: none algorithmic. Governs how P0-04 regression/corruption tests and the P0 gate's compatibility check are evaluated.
Protocol/data versions superseded: none (PROTOCOL.md not yet written; this decision is an input to it).
Independent confirmation needed: re-measure before relying on it for the `kullback-leibler`/`mu` solver path — all evidence so far is from `frobenius`/`cd`.

## D005 — Upstream test failure at the pinned SHA is recorded as an upstream finding, not worked around

Date/time: 2026-09-15, P0-01 session
Type: implementation / deviation
Related task, feature, gate: P0-01, gate P0
Context: at the pinned SHA, `pytest -vs tests` gives 1 failed / 37 passed. The failure is `test_cnmf_end_to_end[dataset_config0]` (simulated dataset), artifact `gene_spectra_tpm`. Diagnosis in SOURCE_AUDIT §1.5.2 attributes it to the scale-blind absolute tolerance (D004) combined with a ~1e-6 relative difference specific to the simulated dataset's `.txt` input path, against reference artifacts generated at cNMF 1.6.0 (per both `Extras/prepare_unittest_*.ipynb` headers) while the code is 1.7.1. The PBMC dataset reproduces bitwise, including its own `gene_spectra_tpm`.
Options considered: (a) regenerate the reference artifacts locally at 1.7.1 so the suite goes green; (b) modify or skip upstream's test; (c) leave upstream's test and references untouched, record the failure and its diagnosis as evidence, and carry it into the P0 gate.
Decision: (c). No upstream test, tolerance or reference artifact is modified. The failure stands, documented, with its cause identified and the environment demonstrated correct by the exact-equality and bitwise artifacts.
Reason: the brief requires distinguishing unavailable test data from a failing algorithm, and forbids loosening thresholds to manufacture a pass. A red test with a written, evidence-backed diagnosis is more honest than a green one obtained by regenerating the thing being tested against. Option (a) remains available later if a genuine need arises, but would have to be labelled as locally regenerated at 1.7.1 and stored separately from the downloaded 1.6.0 set.
Evidence paths and experiment IDs: `docs/benchmarks/registry/p0-01_pytest_run1.log` (exit recorded, 1 failed / 37 passed, 20.11 s); `docs/benchmarks/registry/pytest_data_manifest.tsv` (sha256 of all 148 downloaded reference files, so any future drift is detectable).
Trade-offs and negative evidence: the suite cannot be used as a simple green/red gate while this stands; the P0 gate must state the expected failure explicitly so a future session does not read it as a new regression. The diagnosis rests on the simulated/PBMC asymmetry and on relative-vs-absolute error; it has not been traced to a specific line in `sc.pp.normalize_total`, and that remains an open question rather than a closed root cause.
Consequences for the baseline and active feature set: none algorithmic.
Protocol/data versions superseded: none.
Independent confirmation needed: worth reporting upstream eventually; not required for this cycle.

## Entry template

### D<id> — <title>

Date/time:
Type: implementation / protocol / deviation / scientific adoption
Related task, feature, gate:
Context:
Options considered:
Decision:
Evidence paths and experiment IDs:
Trade-offs and negative evidence:
Consequences for the baseline and active feature set:
Protocol/data versions superseded:
Independent confirmation needed:
