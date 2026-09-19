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
Status: ~~**PROVISIONAL.**~~ → **CONFIRMED at P0-04, 2026-09-17.** The 1e-5 value is calibrated on a single observation (one artifact, one dataset, one solver). It becomes settled only when P0-04's corruption and invariance tests confirm it separates "numerically identical" from "structurally different" — those tests are precisely where a too-loose tolerance shows up, as an injected corruption that fails to trip the check. Two things must therefore be resolved at P0-04, not after: (i) confirm or revise the 1e-5 value against corruption sensitivity, and (ii) set the absolute floor for all-zero/near-zero artifacts noted in the trade-offs above **before** the first such artifact appears, since choosing it afterwards would be choosing it against a known case.

**Both obligations are now discharged; `cnmfbench/compare.py` and `cnmfbench/tests/test_compare.py`.**

(i) **CONFIRMED, not revised.** Measured separation on a 7 × 1200 spectra artifact:

| probe | relative Frobenius | vs 1e-5 |
|---|---|---|
| float32 round-trip (harsher than same-environment BLAS variation) | 2.49e-08 | 400× below |
| uniform relative shift of 1e-06 | 1.00e-06 | **missed**, by design |
| uniform relative shift of 1e-05 | 1.00e-05 | caught, exactly at the edge |
| one gene +50% in one program | 3.60e-03 | 360× above |
| swapping two programs | 5.74e-01 | 57,000× above |

The tolerance sits ~400× above numerical noise and ~360× below the mildest *structural* corruption tried, so the band it has to discriminate is about five orders of magnitude wide and 1e-5 sits near its middle. The value is confirmed on evidence rather than carried forward on assumption — and confirming is as much a result as revising would have been.

(ii) **Absolute floor set: `1e-12` on the Frobenius norm**, chosen while **no** near-zero artifact has yet appeared, which is the only condition under which choosing it is honest. Below the floor the comparison switches from relative to absolute Frobenius error against the same floor, because a relative error is undefined there and "undefined" must not read as "passed" — the failure mode being prevented is a division by zero making the near-zero case the *easiest* to pass. The value sits ~1e4 above float64 epsilon (2.2e-16), far enough to absorb accumulation, and far below any quantity this pipeline produces (spectra rows sum to 1, usages are O(1), counts are O(1e3)).

Unchanged: this remains a **same-environment** tolerance. No bitwise claim is made across BLAS implementations, library versions, thread counts or platforms, and the `kullback-leibler`/`mu` solver path is still unmeasured — the re-measurement named above is still owed.

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

## D006 — P0-03 (simulator) is built before P0-02 (schemas), against a data contract frozen in PROTOCOL.md

Date/time: 2026-09-15, S0-03 session
Type: implementation / deviation
Related task, feature, gate: P0-02, P0-03, gate P0
Context: the ledger orders `P0-02 → P0-03`, so the schema and provenance layer would normally precede the simulator. The user selected a "walking skeleton, simulator first" execution order: build the simulator to full spec, then a deliberately thin split/scorer/runner to close the end-to-end loop early, then harden P0-02/P0-04/P0-05. The reason for exempting the simulator from thinness is that every later metric is scored against its ground truth — a thin simulator with the wrong donor structure would silently invalidate `program_recovery_cosine_v1`, `usage_error_v1` and the leakage tests built on top of it, and the invalidation would not be visible in any of them.
Options considered: (a) keep ledger order, accept that no end-to-end number exists until six tasks are complete, and discover interface mistakes late; (b) build the simulator thin alongside everything else and harden it later with the rest; (c) invert P0-02 and P0-03, build the simulator to spec, and write its output contract into PROTOCOL.md *before* the simulator exists so P0-02 later formalises validation of a frozen statement rather than retrofitting one.
Decision: (c). PROTOCOL.md §6 states the data contract normatively — orientation, dtype, units at each stage, donor-label column, ground-truth storage, data tiers, and the `dataset_manifest_hash` input list. P0-03 implements against §6. P0-02 implements *validation of* §6.
Reason: the ordering risk in (a) is that an interface mistake made early is found only at the end; the risk in (b) is a wrong ground truth that no downstream test can detect. (c) removes the retrofit hazard that motivates the ledger's original order, because the contract is fixed in writing before either task starts.
Guard clause: **P0-02 may not redefine PROTOCOL.md §6.** If P0-02 finds §6 inadequate, that is a protocol amendment under PROTOCOL.md §9 — a new protocol version with a new hash and its own decision entry — not a schema-layer choice. Equally, convenience discovered while writing the simulator may inform *how* §6 is validated but must not alter *what* §6 requires.
Evidence paths and experiment IDs: `docs/planning/PROTOCOL.md` §6; approved plan at `/home/mdmanurung/.claude/plans/plan-the-next-steps-warm-tome.md`.
Trade-offs and negative evidence: the thin split/scorer/runner written in the skeleton session is throwaway-grade by construction, and the standing risk is that it becomes load-bearing and is never hardened. Mitigation: every row it emits carries `evidence_tier: SMOKE`, and both `smoke_can_promote_feature: false` (`ablation_plan.yaml`) and `allow_scientific_promotion: false` (`smoke.yaml`) make such rows unusable for any adoption decision. The P0 gate cannot close while the thin components stand.
Consequences for the baseline and active feature set: none algorithmic. No `src/cnmf/**` change. Affects task order only.
Protocol/data versions superseded: none. PROTOCOL.md v1 is the first version.
Independent confirmation needed: none. This is an execution-order decision, not a scientific one.

## D007 — PROTOCOL.md §1.1 corrected to v1.0.1: descriptive correction, no rule changed

Date/time: 2026-09-16, P0-03 session
Type: protocol (descriptive correction)
Related task, feature, gate: P0-06, S0-03, gate P0
Context: PROTOCOL.md §1.1 listed the `k_selection_stats` columns as `k`, `silhouette`, `prediction_error`. The file `cnmf.py` writes **four** columns (`cnmf.py:932-934`); `local_density_threshold` was omitted. The three columns that were named are described correctly, and the baseline selector (§1.3) reads only `k` and `silhouette`. The defect is that the list was presented as exhaustive and was not.
Options considered: (a) leave it, since no rule depends on the missing column; (b) correct it silently as a typo; (c) correct it, bump the version, and record explicitly that no rule moved.
Decision: (c). §1.1 now names all four columns and states that `local_density_threshold` records the argument *as passed*, not what happened — `consensus` overrides `density_threshold_str = '2'` in this branch (`cnmf.py:876-877`) and applies no density filtering. Version `1.0.1`, sha256 `715639895663bc74e7b864bc1cfae60c2fcd05b013e25f23016d45e86f4f9ca5`, recorded in `ablation_plan.yaml`.
Reason: (a) leaves a known falsehood in a document whose authority rests on being checkable. (b) would break the hash recorded in `ablation_plan.yaml` with no trace of why.
**§9's confirmation-invalidation clause is not triggered.** That clause applies to changes to a frozen *rule*. No rule changed: the selector's inputs, equation, edge cases and refuse-to-run behaviour are untouched, and no confirmation exists to invalidate (`confirmation_unlocked: false`, latest evidence tier NONE). The patch-level version signals exactly this — a `1.x` bump would claim a rule changed.
Evidence paths and experiment IDs: `docs/planning/PROTOCOL.md` §1.1; `docs/benchmarks/configs/ablation_plan.yaml`; `src/cnmf/cnmf.py:932-934, 876-877`.
Trade-offs and negative evidence: the correction was specified in the approved P0-03 plan §0 and then not carried out for a full session; nothing cross-checked plan items against tracker state and nothing caught it. The same lapse dropped the `inference_gene_fraction` change in `smoke.yaml` (0.7 → 0.5, also now done). Both are recorded here rather than fixed quietly, because the process gap is the more durable finding.
Consequences for the baseline and active feature set: none. No `src/cnmf/**` change. The selector is unchanged and still refuses to run while `delta` is null.
Protocol/data versions superseded: v1 → v1.0.1. Nothing was produced under v1, so nothing is superseded in substance.
Independent confirmation needed: none.

## D008 — DEVELOPMENT-tier donor eligibility calibrated on measurement; sealed tier left alone

Date/time: 2026-09-16, P0-03 session
Type: implementation
Related task, feature, gate: P0-03, feature A, gate P0
Context: the simulator's `identity_eligibility` (`q_k`) controls how many donors carry each identity program. P0-03's acceptance condition is that donor-blocked validation measurably differs from random-cell validation on the generated data — otherwise feature A has nothing to detect and every later A-row is uninformative. The first-drafted development value `(1.0, 1.0, 0.5, 0.5, 0.15)` was chosen a priori. Measured over 48 repeats it gives a blocked-vs-random gap of **+1.07%, t = 1.97** — short of the `t > 3` the approved plan requires.
Options considered: (a) keep the a priori value and accept a development tier on which feature A cannot be shown to do anything; (b) calibrate `q_k` on the development tier, which §6.4 explicitly permits; (c) calibrate on the sealed tier, which would destroy it.
Decision: (b). DEVELOPMENT `identity_eligibility` is now `(1.0, 0.5, 0.35, 0.25, 0.15)`, measured at **+2.92%, t = 3.11** over 48 repeats. `SEALED_CONFIRMATION` keeps the original a priori values.
Reason: PROTOCOL §6.4 names DEVELOPMENT as "the only tier that may" inform design, and this is exactly that use — setting a generative constant so the benchmark is capable of resolving the effect it exists to measure. Doing it now, before any comparator row exists and before `delta` is set, is the only point at which it can be done honestly.
**Why the sealed tier is not re-tuned:** it is sealed so that it is not tuned. Carrying a development-calibrated constant into it would make it a second development set wearing a confirmation label, and the difference would be invisible in the result. The consequence is accepted deliberately: sealed confirmation runs on the harder, lower-signal parameterisation, so a confirmation there is conservative rather than flattering.
Evidence paths and experiment IDs: `docs/benchmarks/registry/p0-03_donor_eligibility_sweep.tsv` (4 configs × 10 repeats, then 3 configs × 48 repeats, plus the three-arm decomposition).
Trade-offs and negative evidence: **the between-config comparison is confounded.** Each config was generated from a single dataset realisation, so a difference between configs mixes the coverage setting with the dataset draw. `D vs A` reaches only t = 2.41 and `C vs D` only t = 0.53, so no coverage *effect* is claimed — what is claimed is narrower and sufficient: configuration C reaches `t > 3` on its own paired within-config contrast and the original did not. Establishing a coverage effect would need several `simulation_replicate` values per config and has not been done.
Consequences for the baseline and active feature set: none algorithmic; no `src/cnmf/**` change. Changes which synthetic data the development tier generates, and therefore invalidates nothing, because no result has been produced on the old values beyond the sweep recorded above.
Protocol/data versions superseded: none. `q_k` is a simulator parameter, not a PROTOCOL rule; PROTOCOL v1.0.1 is unaffected. Datasets generated before this change have different `dataset_manifest_hash` values by construction (§6.6 hashes all generative parameters), so old and new data cannot be confused.
Independent confirmation needed: yes, in the ordinary course — the sealed tier is untouched and still gates any adoption claim.

## D009 — Schema vocabularies invented in the harness, not by editing the frozen protocol

Date/time: 2026-09-17, skeleton session
Type: implementation
Related task, feature, gate: P0-02, P0-03, gate P0
Context: `RESULTS.tsv` and `EXPERIMENTS.tsv` shipped as header-only files. **Six columns that must be filled had no defined vocabulary anywhere in the repository**, and two of them — `stratum` and `evaluation_scope` — have no mention in *any* markdown file in `docs/`: they are not merely undefined, they are undescribed. `status` is the load-bearing case, because PROTOCOL §1.4 and §5.3 both rely on it to separate "this arm did not select a rank" from "the selector failed", and neither section says what it may contain.
Options considered: (a) write rows with blanks or invented values and move on; (b) amend PROTOCOL.md to define them; (c) define minimum vocabularies in `cnmfbench/records.py`, validated at write time, recorded here, and batched into the eventual v1.1 amendment.
Decision: (c). `RESULT_STATUS`, `EXPERIMENT_STATUS`, `EVALUATION_SCOPE` and `ARM` are enumerated in `records.py`; `result_row`/`experiment_row` raise on anything outside them. Minimum, not exhaustive — they cover what this session writes and nothing more.
Reason: (b) would create a new protocol version. PROTOCOL.md's bytes are hashed into `ablation_plan.yaml` and §9 makes any edit a versioned amendment, so filling a gap in a *schema* would drag the frozen *rules* along with it. (a) is what D006's mitigation exists to prevent. Batching the vocabularies into v1.1 alongside `delta` and the precision/recall threshold costs one amendment instead of three.
**Three conventions decided here, each of which could reasonably have gone the other way:**
1. **`protocol_hash` is the file-bytes artifact hash.** §7's table is internally inconsistent — row 1 lists it as parameter-like, row 4 gives this file the artifact rule. File-bytes is chosen because it is the only version `sha256sum docs/planning/PROTOCOL.md` can verify, which is what the tracker's own resume instruction tells a reader to run. Verified equal to the recorded value by a test.
2. **`n_eligible_units`/`n_failed_units` count the units aggregated into that row's own value** — cells on a per-donor row, donors on an aggregate row. §4.3 counts cells and §3.5 counts donors in the same column, and this is the only rule satisfying both. **`evaluation_scope` is therefore a required filter on any aggregation**; ignoring it double-counts cells against donors.
3. **A blank cell means a true null; `NOT_COMPUTED` means a value that could not be produced.** The writer rejects the strings `None`, `nan`, `null`, `NA`. An empty cell is otherwise indistinguishable from a quoting bug, a legitimate null and a forgotten column.
Evidence paths and experiment IDs: `cnmfbench/records.py`; `cnmfbench/tests/test_records_and_fence.py`; the 114 + 6 rows in `docs/benchmarks/{RESULTS,EXPERIMENTS}.tsv`.
Trade-offs and negative evidence: a vocabulary invented by the first code to write a column is a vocabulary the next reader may misinterpret, and that risk is highest for `stratum` and `evaluation_scope` precisely because no prose anywhere says what they were for. Recorded rather than hidden.
Consequences for the baseline and active feature set: none algorithmic. No `src/cnmf/**` change.
Protocol/data versions superseded: none. PROTOCOL.md is untouched and still v1.0.1, hash `715639895663bc74e7b864bc1cfae60c2fcd05b013e25f23016d45e86f4f9ca5`.
Independent confirmation needed: no.

## D010 — `arm` is `full_training_pool`, not `matched_budget`

Date/time: 2026-09-17, skeleton session
Type: implementation
Related task, feature, gate: P0-03, feature B, gate P2
Context: the skeleton runs `configuration: '000'` — all three feature switches off. The obvious label for its `arm` is `matched_budget`, the A/B/C factorial arm. But the skeleton trains on **every cell of every training donor with no cell budget**, and `ablation_plan.yaml` defines the matched-budget arm's B-inactive sampling as `proportional_without_replacement` at a fixed total. What the skeleton actually does is `upstream_full_data`'s definition applied to a training fold.
Options considered: (a) label it `matched_budget` since the configuration string is `000`; (b) label it `full_training_pool` and record that these rows are not the matched-budget arm.
Decision: (b). `ARM` in `records.py` includes `full_training_pool`; every row carries it, and `EXPERIMENTS.notes` says `arm=full_training_pool_no_cell_budget`.
Reason: **(a) would create a silent, uncorrectable confound in the B comparison two stages from now.** A future `010` run under a cell budget compared against these `000` rows would attribute the budget difference to feature B. The configuration string and the arm are different facts and this session is the only point at which the distinction is free to record.
Evidence paths and experiment IDs: `docs/benchmarks/RESULTS.tsv`, `docs/benchmarks/EXPERIMENTS.tsv`, all rows this session.
Trade-offs and negative evidence: **these rows are therefore not comparable to a future `010` without re-running `000` under a cell budget.** That re-run is a cost this decision creates and P2-01 must plan for; the alternative was a comparison that looked valid and was not.
Consequences for the baseline and active feature set: none algorithmic. Constrains what the skeleton's rows may later be compared against.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D011 — The thin-component fence is code, not prose

Date/time: 2026-09-17, skeleton session
Type: implementation
Related task, feature, gate: P0-02, P0-04, P0-05, P0-07, gate P0
Context: D006 chose to build the splitter and scorer thin and harden them later, and recorded its own standing risk: "the thin split/scorer/runner written in the skeleton session is throwaway-grade by construction, and the standing risk is that it becomes load-bearing and is never hardened." Prose has not prevented that failure before — three items specified in the approved P0-03 plan were approved and then silently dropped, and nothing caught it because nothing cross-checked plan text against state.
Options considered: (a) rely on D006's prose plus `evidence_tier: SMOKE`; (b) a machine-detectable registry the P0 gate check must read.
Decision: (b). `cnmfbench/provisional.py` holds a registry of five components with their owning ledger task and what hardening requires. A decorator marks each and records, **at call time**, that it ran. Every row from a run with a non-empty touched-set carries `status = ok_provisional` and names the components in `notes`.
**Two gate checks, deliberately separate.** `registry_is_empty()` is the code-level check that blocks the P0 gate; it is false while any decorator remains, and closing it means deleting decorators and registry entries together. `cited_rows_are_not_provisional()` is data-level and **scoped to the experiment ids a gate actually cites** — never a whole-file scan, because provisional rows stay in `RESULTS.tsv` permanently and correctly, and a whole-file scan would block the gate forever no matter how much hardening happened afterwards.
Reason: the difference between (a) and (b) is whether forgetting is possible. A registry a gate reads cannot be forgotten; a paragraph in a decision entry demonstrably can.
Evidence paths and experiment IDs: `cnmfbench/provisional.py`; `cnmfbench/tests/test_records_and_fence.py`, which asserts the registry and the decorators agree **in both directions** — a stale entry un-fences a component silently, a decorator without an entry cannot be read by the gate — and that no module outside `diagnostics.py` references the throwaway `_score_split`, which is D006's named hazard.
Trade-offs and negative evidence: the fence costs a decorator on five hot-path functions and one extra status string. It does not make the thin components correct; it only makes their thinness impossible to lose track of.
Consequences for the baseline and active feature set: the P0 gate cannot close until P0-04, P0-05 and P0-07 empty the registry.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D012 — The DEVELOPMENT feasibility verdict is NO-GO, and the criterion that produced it is mis-specified

Date/time: 2026-09-17, feasibility session
Type: scientific adoption
Related task, feature, gate: P0-03, P0-04, feature A, gate P0
Context: the criteria were pre-registered and committed at `f1e86fa` before the run was launched. The run (`p0-03-dev-feasibility`, 610 RESULTS / 16 EXPERIMENTS rows) returned criterion 1 PASS (paired t = 26.8 over 24 donors), criterion 3 PASS (silhouette ranges 0.282, 0.301), criterion 2 FAIL in `outer_1` (1.0101 and 1.0142 against a 1.02 threshold). Under the pre-registered rule "NO-GO if any fails", the verdict is NO-GO.
The curve nevertheless minimises at `K_true = 7` in **both** folds, descends monotonically from K=4 (ratio 1.137, 1.166) to K=7 and rises monotonically to K=10; the silhouette holds ~0.996 through K=7 and drops sharply at K=8 in both folds. Two independent signals place the elbow at `K_true`.
Options considered: (a) override the verdict on the strength of that curve; (b) record NO-GO and treat the curve as an observation; (c) amend criterion 2 in place and recompute.
Decision: **(b).** The verdict recorded in `p0-03_development_feasibility.tsv` is NO-GO and is not revised. Separately, and recorded as an argument rather than as a result: criterion 2 inspects only `K_true` and `K_max`, both of which lie on the *overfit* side of the minimum where the curve is nearly flat by construction. Its stated rationale — "no signal left to select on" — is falsified by this run's own data, since the grid spans 1.137 → 1.016. It passed at SMOKE only because that grid's `K_max = 4` sat on the *underfit* side of a `K_true = 3` curve, so the same rule tested a different quantity at the two tiers.
Reason: (a) and (c) are the same act with different labels. A criterion rewritten by whoever has just watched it fail carries no evidential weight however sound the argument, and the programme's entire discipline is that constants precede data. The mis-specification is real and is worth recording precisely *because* recording it costs the convenient outcome.
**The remediation menu was itself under-specified.** The pre-registration offered four permitted responses to NO-GO. Options 1–3 (raise separation, add depth or donors, narrow the grid) all strengthen a benchmark that is already resolving rank correctly, and option 4 ("report that the frozen §6.3 contract cannot support predictive rank selection at achievable scale") would be a **false report** given this curve. None of the four is correct here. The lesson for the v1.1 amendment is that a remediation menu written before the data cannot anticipate a failure of the instrument rather than of the subject, and should carry an explicit "the criterion was wrong" branch requiring fresh pre-registration.
Evidence paths and experiment IDs: `docs/benchmarks/registry/p0-03_development_feasibility.tsv`; pre-registration at `f1e86fa`, amendment at `3ed5bae`, verdict at `48718d7`; run `results/exploratory/p0-03-dev-feasibility` (gitignored), `dataset_manifest_hash 31b4cf0b…`. Cost agreement verified on this run: 0 disagreements across all 16 experiments.
Trade-offs and negative evidence: the NO-GO blocks the claim that feature A's premise is established, which is the honest position — see D013, since criterion 1's `t = 26.8` is itself exposed to an under-convergence confound that the diagnostic run tests. Incidental negative evidence recorded in the same file: `n_training_carriers_per_identity_program = [12, 3, 3, 4, 1]` in `outer_0`, i.e. one identity program is carried by a **single** training donor.
Consequences for the baseline and active feature set: nothing is promoted; `allow_scientific_promotion` is false at this tier and `scientific_adoption` is INCONCLUSIVE. P0-04 is unblocked regardless, because recovery metrics measure whether the right programs were found, which is independent of whether rank can be selected.
Protocol/data versions superseded: none.
Independent confirmation needed: yes — any replacement criterion must be pre-registered afresh, with its seed committed in advance, and evaluated on a run at a different seed. A criterion tested on the data that motivated it has no evidential force.

## D013 — Spectra carry their unit system as data, because the alternative inverts the result

Date/time: 2026-09-17, P0-04 session
Type: implementation
Related task, feature, gate: P0-04, gate P0
Context: `program_recovery_cosine_v1` compares true spectra against cNMF's `median_spectra`. The truth is generated in count space; `median_spectra` lives in the engine's scaled space, where every gene has been divided by its training standard deviation `s_g` (PROTOCOL §3.2, `cnmf.py:542`). Cosine is invariant to scaling a *vector* but not to scaling each *coordinate* by a different `s_g` — that is a shear, and it rotates the vectors.
Measured on the skeleton's SMOKE run at `K_true = 3`: **unaligned, the matched null beats the fitted solution at every rank in both folds** (fit 0.703 vs null 0.819 at `K_true`) — the metric would report that cNMF recovers programs *worse than a trivial average of the truth*. Aligned, the fit wins everywhere and peaks exactly at `K_true` (0.988 vs 0.850). Both routes to common units agree (0.9881 pushing truth into scaled space, 0.9888 pulling the dictionary into count space).
Options considered: (a) document the required alignment in a docstring and align at each call site; (b) make units a property of the data, so that an unaligned comparison raises.
Decision: **(b).** `cnmfbench/recovery.py` defines `Spectra(matrix, space, gene_labels)` with `space ∈ {"count", "scaled"}`; `recovery_cosine` raises `UnitMismatch` on a space or gene-axis mismatch rather than returning a number. `matched_null_spectra` inherits `truth.space`, so a null built from aligned truth cannot drift out of units.
Reason: since the two routes agree, *which* alignment is used is free — **failing to choose is what breaks the metric**, and it breaks it silently, by returning a plausible number that reverses the finding. A docstring cannot fail a test run; a type that refuses can. This is the same argument D011 made for the provisional fence: the difference between the options is whether forgetting is possible.
Evidence paths and experiment IDs: `cnmfbench/recovery.py`; `cnmfbench/tests/test_recovery.py`, 22 tests, including the full pre-registered corruption battery — label permutation, gene reordering and factor rescaling asserted **invariant to 1e-12**, and duplication, deletion, usage shuffling and noise replacement asserted to penalise. `usage_error` takes the `Alignment` as an argument and refuses one computed on a different fit, since re-deriving a matching from usages would choose the permutation that makes usages agree best and could disagree with the permutation the recovery score was computed on.
Trade-offs and negative evidence: every call site must now name a space, which is friction at the boundary where raw arrays enter. The noise-replacement corruption lands *near* the matched null rather than near zero, because nonnegative random vectors are not orthogonal to anything — the test asserts that band rather than pretending the floor is 0.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` is untouched. `program_recovery_cosine_v1` and `usage_error_v1` are implemented but not yet wired into the runner.
Protocol/data versions superseded: none.
Independent confirmation needed: no — the two alignment routes confirming each other is the check, and it is asserted in the suite.

## D014 — `experiment_id` gains an optional `variant`, because the "same id ⇒ same experiment" invariant was violated in practice

Date/time: 2026-09-17/18, feasibility session
Type: implementation
Related task, feature, gate: P0-03, P0-04, P0-07, gate P0
Context: the convergence diagnostic re-ran the DEVELOPMENT tier with `max_optimizer_iterations` 300 → 1000. Same `configuration`, same `arm`, same `dataset_id`, same `dataset_manifest_hash` (the dataset genuinely *is* the same), same seeds — **different numbers**. `make_experiment_id` reads exactly those inputs, so both runs produced identical ids, and `merge_into_tracked` refused the second with "a repeated id with a possibly different value is a contradiction to resolve, not a duplicate to tolerate."
The guard was right, and this is the second time this session that a check written earlier caught a defect that prose would have missed (the first being the fold-identity collision in the fit-cost test). `preprocessing_hash` **did** differ between the runs (`e61b9c7f…` vs `d1da4eee…`), so the rows were distinguishable by *content* but not by *name*.
Options considered: (a) fold the factorization hyperparameters into the id digest; (b) put a distinguishing suffix on `dataset_id`; (c) add an optional `variant` label, folded into the digest only when set.
Decision: **(c).** `make_experiment_id(..., variant=None)`; when set, the label enters both the digest and the readable prefix. `development_conv1000.yaml` carries `variant: conv1000`.
Reason: (a) is correct in principle but changes **all 733 existing ids**, forcing a three-run replay to repair an identifier — a large self-inflicted regeneration whose benefit is captured more cheaply. (b) is wrong on the facts: `dataset_id` names the dataset, and the dataset is identical; so is `arm`, which is a frozen protocol vocabulary and not a scratchpad for diagnostics. (c) restores the invariant going forward at zero cost to existing evidence, because a payload key that is absent when unset leaves every previously computed digest bit-identical. The thing that was actually wrong is that a config changed a factorization parameter while reusing a tier's identity silently; `variant` makes it say so.
Evidence paths and experiment IDs: `cnmfbench/records.py` (`make_experiment_id`); `cnmfbench/skeleton.py`, all four call sites; `docs/benchmarks/configs/development_conv1000.yaml`; two tests in `test_records_and_fence.py` pinning both halves — that a variant changes the id, and that its absence leaves ids untouched. 178 tests pass.
Trade-offs and negative evidence: **an `EXPERIMENTS.tsv` row does not carry enough to reconstruct its own `experiment_id`** — there is no `configuration` column, no `seeds` and no `variant`, so the id's inputs are only partly recoverable from the record and no test can verify that existing ids are unchanged; `test_every_tracked_id_is_shaped_like_its_own_columns` checks the readable prefix only and its docstring says so, after an earlier version of it overclaimed. Adding those columns is a header change and belongs to P0-07. Second, `variant` is free text, so it can be forgotten. Nothing forces a config that changes a factorization parameter to set it, and the failure mode if it is forgotten is the same collision — caught at merge time by the same guard, which is a detection rather than a prevention. A general fix (a) remains available and becomes cheap at the next occasion that regenerates evidence anyway; recorded here as the deferred stronger option rather than closed off.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` untouched. The diagnostic's 610 rows were **not** merged under colliding ids; the run is being repeated with the label set, and its scientific content was already committed at `b8ba39d` independently of the tracked TSVs.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D015 — Feature C keeps each run's centroid-nearest contribution, a choice the ablation plan does not make

Date/time: 2026-09-18, features B/C session
Type: implementation
Related task, feature, gate: P3-01, feature C, gate P0
Context: `ablation_plan.yaml` specifies C's active consensus as `one_per_run_per_upstream_cluster` and nothing further. When one optimizer run contributes two spectra to the same consensus cluster — which is exactly the situation C exists to correct — something must decide *which* of them survives to the median. The plan does not say, so the implementation had to choose, and the choice is not observable from the plan text.
Options considered: (a) **nearest the cluster centroid** — the run's own best representative of that cluster; (b) first by index — arbitrary, and dependent on the order `merged_spectra` happens to be assembled in, so a harmless upstream reordering would silently change C's output; (c) lowest local density — entangles C with the density filter that runs immediately before it, so a C effect could not be separated from a density-filter effect.
Decision: **(a).** `features.consensus_spectra_from_bank(..., one_per_run=True)` keeps, per (run, cluster) pair, the member with the smallest L2 distance to its cluster's centroid.
Reason: (a) is the only option that is a property of the *data* rather than of iteration order or of a neighbouring step. It also matches what C claims to be doing: giving each run one vote, cast for that run's best estimate of the program, rather than for whichever of its two estimates was written first.
Evidence paths and experiment IDs: `cnmfbench/features.py`; `cnmfbench/tests/test_features.py` — `test_c_off_reproduces_upstream_consensus_on_a_real_factor_bank` pins the OFF path against `cnmf.consensus` on the real Kang banks at k=6,8,10,12,14 at relative Frobenius **0.000e+00**, and the runner recomputes the same equivalence at run time and refuses above 1e-8, measured 0.0 in all twelve SMOKE cases. `docs/benchmarks/registry/p0-04_features_bc_smoke.tsv`.
Trade-offs and negative evidence: **the tie-break has never been varied, so its effect on C is unmeasured.** It could matter: the surviving spectrum enters a median, and at small cluster sizes one member's identity moves that median. SMOKE cannot test this at all — C fired in 1 of 12 cases there, which is why `features.consensus_c` remains fenced and its `hardening_requires` names this rule explicitly. A defensible alternative reading of the plan is that the *mean* of a run's contributions should be its single vote; that was not implemented and is not ruled out by anything measured.
Consequences for the baseline and active feature set: none to the baseline; `src/cnmf/**` untouched and C is a harness-side switch that is off in every `000`/`010` row. Feature C's scientific_adoption is INCONCLUSIVE.
Protocol/data versions superseded: none.
Independent confirmation needed: yes — either the ablation plan fixes the rule, or C's effect is shown not to move when the rule changes. Until then no C result may be quoted without this entry.

## D016 — `hold_preprocessing_constant_across_B` is satisfiable for `G` and not for `s_g`, so cross-arm B endpoints are read in count units

Date/time: 2026-09-18, features B/C session
Type: protocol
Related task, feature, gate: P2-01, feature B, P0-04, gate P0
Context: `ablation_plan.yaml:32` requires `hold_preprocessing_constant_across_B: true`. PROTOCOL §3.2's preprocessing is the pair `{G, s_g}`. `G` is held: it is selected once on the full training pool and frozen into both arms via `prepare(genes_file=...)`, **verified byte-identical** between the arms. `s_g` is not held and **cannot be**: feature B changes which cells reach `cnmf.prepare`, and `prepare` computes the scale internally from exactly the cells it receives (`cnmf.py:542`, `norm_counts.X /= norm_counts.X.std(axis=0, ddof=1)`). Measured drift, B-ON vs B-OFF at `outer_0`, |G|=100: median ratio 1.043, p05–p95 0.935–1.161, max 1.238, mean |log2 ratio| 0.091.
A per-coordinate drift is a **shear**, the same class of error D013 records, and it moves every endpoint: the **sign of the B effect on held-out predictive error flips in 4 of 6 (fold × rank) cells** between the engine's scaled space and count space; `program_recovery_cosine_v1` changes magnitude by up to 3.5× without flipping sign; the Hungarian **alignment itself** differs at k=4 `outer_0`, moving B-OFF's `usage_error_v1` from 0.7246 to 0.9846.
Options considered: (a) fit `s_g` on the full training pool and use it for scoring — **impossible**, the dictionary still lives in the sample's scale, so `verify_transform_matches_cnmf` would fail, correctly; (b) make `prepare` accept an externally supplied scale — requires editing `src/cnmf/**`, forbidden; (c) accept that `s_g` cannot be held, and express every cross-arm quantity in the units the two arms share; (d) keep reporting scaled-space numbers with a caveat.
Decision: **(c).** Any quantity compared across B arms is expressed in **count units**. `heldout_squared_prediction_error_counts_v1` is B's primary endpoint; `program_recovery_cosine_v1` and `usage_error_v1` are scored with the fitted dictionary pulled into count space via `Spectra.to_count(s_g)`, never with truth pushed into an arm's own scaled space. `heldout_squared_prediction_error_v1` is **not** withdrawn — it remains a valid within-arm diagnostic. Pre-registered in `docs/planning/contracts/B.md`.
Reason: count space is the only reference frame the two arms share, and it is the space the truth is generated in, so it exists independently of any arm's fitting choices. (d) was rejected because the caveat does not survive being read: the scaled-space number *was* already published in the SMOKE registry, and it was the wrong sign in 4 of 6 cells. **The convention does not flatter B** — in count units B's predictive error is worse in 4 of 6 cells where the scaled reading had it improving in 3, while the count-route alignment makes B's usage-error advantage larger at k=4 `outer_0`. It moves the result in both directions, which is what makes it a units choice rather than a result choice. No new metric name was invented: `heldout_squared_prediction_error_counts_v1` was already emitted, so PROTOCOL §5.2's eleven names are untouched (§5.1).
Evidence paths and experiment IDs: `docs/planning/contracts/B.md`; `docs/benchmarks/registry/p0-04_features_bc_smoke.tsv`, B-UNITS section, which preserves the falsified claim verbatim beside its correction; runs `p04-feat-000m`, `p04-feat-001`, `p04-feat-010`, `p04-feat-011`.
Trade-offs and negative evidence: **count-unit reporting removes the artifact from the comparison but does not make the two arms the same estimator.** The inference NNLS still solves in each arm's own `1/s_g` weighting, so two arms with identical programs return slightly different usages. That residual is arguably part of what B does in deployment — a practitioner running donor-balanced discovery gets the donor-balanced scale too — but it is a property of the intervention, not something the comparison controls for, and no B result may be reported as if it had been. Second, **a guard that should have caught this did not**: `analysis.assert_poolable` refuses rows spanning more than one `preprocessing_hash` and its docstring claims such rows differ in "gene panels and per-gene scales", but the hash carries `s_g_ddof` and not `s_g` — all four configurations share `c9ba55b825846b53205c1816` at `outer_0`, so the guard would have permitted the pooling its docstring promises to refuse. **Fixed, and not the way it was first planned.** The obvious repair — add `s_g` to `preprocessing_hash`, quantized to fixed significant digits so a replay does not trip on BLAS noise — was rejected on reflection: only 8 of ~48 runs were being regenerated, so a formula change would leave older rows hashed one way and newer rows another, versioning the guard instead of keying it on content. Instead `assert_poolable` and `pooling_groups` now key on the **pair** `(preprocessing_hash, discovery_cells_hash)`. `discovery_cells_hash` was already a column, already differs exactly when the arms differ, and is *upstream* of `s_g` — the same cells deterministically give the same scale — so it is a stricter key than `s_g` would be and needs no quantization. Pinned by `test_pooling_across_the_two_B_arms_is_refused_although_their_gene_panel_is_identical`, which asserts the two arms share a `preprocessing_hash` before asserting that pooling them raises. Third, this supersedes the `hardening_requires` text on `features.discovery_sample_b`, which asks for an audit asserting `s_g` identical across arms — that assertion cannot be met as written and is replaced by *reporting* the drift.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` untouched and verified byte-identical. Feature B's scientific_adoption remains **INCONCLUSIVE** — the correction does not change the verdict, because every difference measured is smaller than the scale drift the arms already differ by, at n=2 folds with a single draw per arm.
Protocol/data versions superseded: none. The ablation plan's `hold_preprocessing_constant_across_B: true` is not edited; this entry records that it is met for `G` and unmeetable for `s_g`, which is a finding about the constraint set, not a change to the plan.
Independent confirmation needed: yes — sampling replicates, so the draw's own variance is reported rather than assumed negligible. Until then no B number may inform an adoption decision.

## D017 — `scoring.equal_donor_mean` leaves the fence, because P0-04 could not be DONE while owning a fenced component

Date/time: 2026-09-18, features B/C session
Type: implementation
Related task, feature, gate: P0-04, gate P0
Context: P0-04 was marked DONE with a ledger row claiming "Full corruption battery: three invariances asserted to 1e-12, four penalties asserted." `cnmfbench/provisional.py` simultaneously carried `scoring.equal_donor_mean` with `owner_task="P0-04"` and `reason="No corruption or invariance tests."` **Both statements were committed in the same change and they contradict each other.** They are about different things — the battery that exists is in `test_recovery.py` and covers `program_recovery_cosine_v1` / `usage_error_v1`; the fence entry is about the §3.5 aggregator, which had three tests and no battery. Sharper still, every row cited as P0-04's acceptance evidence carries `status: ok_provisional` naming `scoring.equal_donor_mean` among the components that produced it: the evidence declared itself the output of throwaway code owned by the task being marked DONE.
`test_every_provisional_component_names_a_real_ledger_task` did not catch this because it checks that the owner task *exists*, not that it is not already DONE.
Options considered: (a) revert P0-04 to IN_PROGRESS; (b) write the aggregator's battery and un-fence it, per D011's rule that an entry leaves only with its decorator and a decision entry; (c) reword the ledger row to exclude the aggregator.
Decision: **(b).** Seven tests added in `cnmfbench/tests/test_splits_and_scoring.py`; the `@provisional` decorator and the registry entry are deleted together. `PROVISIONAL` now holds six components, so `registry_is_empty()` stays False and the **P0 gate remains open**.
Reason: (c) is bookkeeping that leaves the real gap open — the aggregator sits under every `equal_donor_mean` row in `RESULTS.tsv` and is the single most-used untested component in the harness. (a) is honest but wastes the fact that the missing work is small and well specified. The battery is the aggregator's OWN invariances, which no test of the metric being aggregated can reach: invariance to cell order, to donor relabelling, to **replicating a donor's cells** (the property §3.5 exists for — a pooled cell mean fails this and the test asserts it fails), positive homogeneity (which D016 relies on when it reads B in count units), the penalty that damaging one of n donors moves the aggregate by exactly `delta/n` rather than by that donor's cell share, and the two refusals.
Evidence paths and experiment IDs: `cnmfbench/scoring.py`; `cnmfbench/provisional.py`; `cnmfbench/tests/test_splits_and_scoring.py`, 28 tests in the file, 199 in the suite, exit 0.
Trade-offs and negative evidence: **rows already written still name `scoring.equal_donor_mean` in their `notes`**, a component no longer in the registry. They are not regenerated and should not be: they were produced before the hardening, and their `ok_provisional` status remains correct regardless, since six components — including `scoring.nnls_usages` and `skeleton.run`, which every row touches — are still fenced. Second, the check that missed this contradiction is **still** only checking that an owner task exists; a check that an owner task is not DONE would have caught it and is not written. Recorded as the open gap rather than fixed here, because it wants the ledger parser to understand task states and that is P0-07's business.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` untouched. P0-04 stays DONE, now without the contradiction.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D018 — Two dependency-order deviations are recorded after the fact, because the ledger was contradicting itself

Date/time: 2026-09-18, P0-05 planning
Type: deviation
Related task, feature, gate: P0-02, P0-06, P0-08, gate P0
Context: the ledger declares dependencies and two of them have been violated without an entry. **P0-06 is IN_PROGRESS while its declared dependency P0-05 is TODO** (`PROGRESS.md:68` vs `:67`) — its specification half was written at S0-03, long before P0-05 existed as a question. **P0-08 work proceeded while its declared dependency P0-02 is TODO** (`:70` vs `:64`) — four datasets were downloaded, hashed and assessed, and a diagnostic cNMF run was made on Kang. The P0-02/P0-03 inversion got D006; these two got nothing, so the ledger states dependencies it does not keep and a reader cannot tell deliberate sequencing from drift.
Options considered: (a) record both deviations and leave the order as it is; (b) revert — un-start P0-06's specification and discard the P0-08 assessment; (c) rewrite the declared dependencies to match what happened.
Decision: **(a).** Both deviations stand and are recorded here. Neither task is marked DONE, and P0-08's ledger row was deliberately **not** advanced despite five commits of work, because license verification is an explicit acceptance requirement and is satisfied for exactly one of the four datasets (Heart Cell Atlas, CC BY 4.0).
Reason: (b) destroys work that is correct and useful for a bookkeeping reason. (c) is the dangerous option — editing a dependency to match what was already done makes the ledger unfalsifiable, and the dependency graph is one of the few things that can catch work being built on an absent foundation. Recording the deviation keeps the graph honest *and* the work. The two deviations are also different in kind and should not be read as one: P0-06's is **specification without implementation**, which is safe because a frozen spec constrains later code rather than depending on it; P0-08's is **assessment without acceptance**, which is safe because no row it produced entered the evidence system — the Kang run wrote no `RESULTS.tsv` or `EXPERIMENTS.tsv` rows at all and is labelled a diagnostic.
Evidence paths and experiment IDs: `docs/planning/PROGRESS.md` ledger rows P0-02, P0-05, P0-06, P0-08; `docs/benchmarks/registry/p0-08_real_data_candidates.tsv`; commits `7725827`, `d9c28da`, `3c10c12`, `069994c`, `707df29`, `28818f5`.
Trade-offs and negative evidence: **this entry is written after the fact, which is exactly the failure mode it documents.** A deviation recorded at the time is a decision; one recorded three sessions later is an archaeology. The gap was found by a planning-time audit, not by any check — nothing in the harness reads the dependency column, so a third deviation would be equally invisible. A ledger-consistency check (no task IN_PROGRESS or DONE whose dependency is TODO, unless a decision entry names the pair) is not written and belongs with the ledger parser at P0-07. Second, P0-02 remains TODO and is now a declared dependency of **P0-05**, the next task — so the same question arises immediately, and the answer chosen there should be recorded at the time rather than later.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` untouched.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D019 — The inner validation loop runs only when feature A is on, reversing §6.2 of the approved P0-05 plan

Date/time: 2026-09-18, P0-05 implementation
Type: implementation
Related task, feature, gate: P0-05, P1-01 (feature A)
Context: the plan approved before implementation stated (§6.2) that "every configuration runs the inner loop; A-OFF configurations compute the inner scores and do not select on them," citing `IMPLEMENTATION_PROMPT.md:158` ("A changes whether inner validation selects rank; it does not give A a different outer evaluator"). A design review challenged this before `_run_inner_fold` was wired into any caller, citing `PROTOCOL.md:48` (§1.1): "Both inputs already exist on disk after a rank sweep; the selector computes nothing new." `k_selection_plot` computes `silhouette` and `prediction_error` via `consensus(skip_density_and_return_after_stats=True)` **on the training fit itself** — the A-OFF baseline selector never reads an inner validation fold at all. Read directly, `PROTOCOL.md:45-60` confirmed this. The cited `IMPLEMENTATION_PROMPT.md:158` clause constrains the *outer* evaluator, not whether the inner loop runs; it does not settle §6.2 the way the plan assumed.
Options considered: (a) keep §6.2 as approved — every configuration runs the inner loop; (b) run the inner loop only when A is on.
Decision: **(b).** `_run_inner_fold` (`cnmfbench/skeleton.py`) exists as a callable helper but is invoked by no production path yet — `check_preconditions` refuses feature A while `delta` is null (§2), so today it is exercised only by `cnmfbench/tests/test_inner_folds.py`, which calls it directly. When P0-06 wires A in, the call is gated on `(cfg.get("features") or {}).get("A")`.
Reason: running the inner loop unconditionally would (1) compute work that the A-OFF baseline's selector never consumes, since PROTOCOL §1.1 shows that selector's inputs come from the training fit, not an inner fold; and (2) move A's selection cost onto the A-OFF baseline's side of the `000`-vs-`100` comparison. `IMPLEMENTATION_PROMPT.md` P0.3(4) forbids making an expensive algorithm appear free, and `skeleton.py`'s own `_cost` docstring already records this programme doing exactly that once before (the B/C session's cost-window bug understated feature A). Charging A-OFF for A's inner fits would repeat that mistake by construction rather than by accident.
Evidence paths and experiment IDs: `cnmfbench/skeleton.py` (`_run_inner_fold`, `_consensus_dictionary`); `cnmfbench/tests/test_inner_folds.py`, 8 tests; `PROTOCOL.md:45-60` (§1.1), `PROTOCOL.md:125-179` (§2); commit `7312dd2`.
Trade-offs and negative evidence: the approved plan is not amended retroactively — this entry is the correction, made before any A-ON run existed to be confounded by it. The plan's §6.2 reasoning was not baseless (`IMPLEMENTATION_PROMPT.md:158` is a real clause), it was read as settling a question it does not reach; both citations are recorded here so a future reader can see why the same clause supports different conclusions depending on which PROTOCOL section is read alongside it.
Consequences for the baseline and active feature set: none today, since A cannot run. Binding once P0-06 sets `delta`: A-ON configurations (`100/101/110/111`) will show additional wall/cpu cost against their A-OFF counterparts that is genuinely attributable to inner-fold fitting, not folded into the shared outer fit's cost row.
Protocol/data versions superseded: none — PROTOCOL states no rule about the inner loop's caller condition; this is an implementation decision, not a protocol amendment.
Independent confirmation needed: no.

## D020 — Inner fits under `arm: matched_budget` are deferred to P0-06; the design is specified, not yet built

Date/time: 2026-09-18, P0-05 implementation
Type: deviation
Related task, feature, gate: P0-05, P0-06, P1-01 (feature A), P2-01 (feature B)
Context: `_run_inner_fold` fits on the full inner-training pool regardless of `cfg["discovery"]["arm"]`. Under `arm: matched_budget` — which `smoke_000m.yaml` and `development_000m.yaml` both declare — the declared `cell_budget` exceeds the cells available to an inner fit at both tiers (SMOKE: 2 inner-training donors, 60 cells, against `cell_budget: 72`; DEVELOPMENT: 6 donors, 1200 cells, against 1440), so applying `discovery_sample` to an inner fit as written would raise `ValueError` (`features.py:204-205`). A design review, run specifically to stress-test the fix the user had already chosen (scale the budget to the inner fraction), found the fix's *execution* has more moving parts than its statement: (1) the sample must be drawn whenever `arm == "matched_budget"`, not gated on feature B's bit, mirroring `skeleton.py`'s outer-fold branch, or the A×B cells would differ from A×not-B cells in inner sample size for a reason that is not B; (2) `s_g` must be computed on the SAMPLED rows, not all inner-training rows, or a gene with zero variance across the sample but not the full pool passes `training_gene_scale`'s guard and cNMF silently emits NaN with only a printed warning; (3) inner B-ON and B-OFF need their own shared inner `G` via a `_panelref` fit, mirroring the outer fold's `hold_preprocessing_constant_across_B` mechanism, or the two arms select ranks under different gene universes; (4) the ratio must be over CELLS, not donors, because the simulator's `cells_per_donor_cv` and real donor data both violate equal-cells-per-donor, and cell-based scaling is self-guaranteeing (`round(x) <= n` for `x <= n`) where donor-based scaling requires a feasibility check that can genuinely fail; (5) the inner sampling seed must be derived per `(outer_index, inner_index)` via `SeedSequence`, mirroring `inner_donor_folds`, or every inner fold of a given outer fold draws the identical positional subset; (6) `check_preconditions` needs a budget-fits-the-smallest-fold check that does not exist today, closed-form for `cells_per_donor_cv == 0` and requiring an exact post-`simulate` check otherwise; (7) inner-fold cost must be timed outside the outer fit's cost window, for the same reason as D019; (8) `make_experiment_id` has no `inner_split_id` slot, so two inner folds of one outer fold at one rank collide on `experiment_id` today, and a `variant`-style "fold into the payload only when set" resolution needs choosing before any inner row can be written.
Options considered: (a) implement the full design now, inside P0-05; (b) implement only the config-time refusal (block a matched_budget + A configuration whose budget cannot fit the smallest inner fold) and defer the sampling machinery; (c) defer the whole thing to P0-06, recording the design findings as the specification for that work.
Decision: **(c).** No config for `100/101/110/111` exists yet (`docs/benchmarks/configs/` holds only the four A-OFF cells), `check_preconditions` refuses feature A unconditionally until `delta` is set, and D019 confirms `_run_inner_fold` has no production caller today. The eight sub-problems above are individually well specified but their interactions (particularly 2+3: the panelref and the `s_g` fix are one package, not two independent changes) make this a piece of work with its own verification burden, not an extension of the panel-repetition/leakage-audit work this session actually finished.
Reason: (a) risks landing exactly the silent bug the review exists to prevent (2, above) under time pressure, with no A-ON run to catch it since none can execute until P0-06 regardless. (b) buys little: a config-time refusal for a configuration that cannot be constructed yet protects nothing today and would need re-deriving once the configs exist. Recording the design now, while the reasoning is fresh and reviewed, is worth more than a partial implementation that P0-06 would need to re-audit.
Evidence paths and experiment IDs: `cnmfbench/skeleton.py` (`_run_inner_fold`, `_run_fold`'s `matched_budget` branch at the `_arm(cfg) == "matched_budget"` guard); `cnmfbench/features.py:178-246` (`discovery_sample`); `cnmfbench/splits.py:119-123` (`inner_donor_folds`'s `SeedSequence` precedent); `cnmfbench/records.py:102-136` (`make_experiment_id`, the `variant` precedent for optional payload fields); `cnmfbench/simulate.py:123` (`cells_per_donor_cv`); design review transcript, 2026-09-18.
Trade-offs and negative evidence: this leaves `_run_inner_fold` inconsistent with the `arm: matched_budget` declared in the very SMOKE config `test_inner_folds.py` exercises — the inner fit silently ignores the budget rather than honouring or refusing it. That inconsistency has zero effect on any tracked row today (A cannot run, so no matched-budget inner fit has ever executed outside the test suite), but it is a real gap and is named here rather than left implicit. `_run_inner_fold`'s docstring should be read alongside this entry until P0-06 closes it.
Consequences for the baseline and active feature set: none today. P0-06 must resolve sub-problem 8 (the `experiment_id` collision) before any A-ON matched_budget row can be written at all, independent of the sampling logic — this is a harder blocker than it first appears, since it affects the schema-level identity invariant `same id => same experiment`, not just the sampling arithmetic.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D021 — `splits.gene_panel` and `scoring.nnls_usages` leave the fence; `splits.outer_donor_folds` is reassigned to P0-06 rather than un-fenced with them

Date/time: 2026-09-18, P0-05 implementation
Type: implementation
Related task, feature, gate: P0-05, P0-06, gate P0
Context: P0-05 owned three fenced components. Two have met their `hardening_requires` exactly: `scoring.nnls_usages` required "the §3.2 leakage tests," which `test_leakage.py` provides (9 tests, perturbing held-out values before `prepare` and asserting bitwise invariance of `G`, `s_g`, the dictionary, cache identities, the stability curve and inference-panel usages, plus a positive control and a same-input gate). `splits.gene_panel` required "panel repetitions with the variance reported, and a cross-arm panel-identity audit," which this session's panel-repetition block (`skeleton.py`, `panel_variance_by_k` in diagnostics) and `analysis.assert_panels_identical` provide. The third, `splits.outer_donor_folds`, required "nested outer/inner donor folds," which now exist (`inner_donor_folds`) and are tested against real cNMF fits (`test_inner_folds.py`) — but D019 establishes that no production run calls the inner path, because `check_preconditions` refuses feature A while `delta` is null.
Options considered: (a) un-fence all three, since the literal `hardening_requires` text for `splits.outer_donor_folds` is satisfied by the code existing and being tested; (b) un-fence the two with a production-independent hardening claim, and reassign `splits.outer_donor_folds` to P0-06 with its `hardening_requires` restated to require a production caller.
Decision: **(b).** Fence goes from six to four.
Reason: (a) would repeat D017's exact lesson — a component declared hardened while the path that would exercise it in production does not run. D017's fix was to write the missing tests; here the tests already exist (`test_inner_folds.py`, 8 tests against real fits), but the thing D017 actually cared about was evidence that throwaway-grade code has become load-bearing in the pipeline that produces tracked rows, and `splits.outer_donor_folds`'s nested-fold half is not yet load-bearing anywhere `RESULTS.tsv` is written. Restating its `hardening_requires` as "delta set and feature A runnable" ties its release to the event that actually exercises it, rather than to the event of writing its own tests.
Evidence paths and experiment IDs: `cnmfbench/scoring.py` (`nnls_usages`, decorator removed); `cnmfbench/splits.py` (`gene_panel`, decorator removed); `cnmfbench/provisional.py` (three entries reduced to one, `splits.outer_donor_folds` reassigned `P0-05` → `P0-06`); `cnmfbench/tests/test_leakage.py`; `cnmfbench/analysis.py` (`assert_panels_identical`); `cnmfbench/tests/test_records_and_fence.py` (4 new tests for the panel audit, 1 test updated to use a still-fenced component); `docs/planning/PROGRESS.md` fence table. `python -m pytest cnmfbench -q` → 229 passed, exit 0. `git diff 5dbc5ba..HEAD --stat -- src/ tests/ setup.py pyproject.toml` → empty.
Trade-offs and negative evidence: `registry_is_empty()` stays False regardless of this decision, so it changes no gate outcome today — its value is in the fence table accurately describing which components are load-bearing-but-unhardened versus load-bearing-and-hardened. The two post-P0 entries (`features.consensus_c`, P3-01; `features.discovery_sample_b`, P2-01) remain the structural problem named at D011/D017 and not solved here. This also creates a **third** dependency-order deviation of the kind D018 records: P0-05 is marked DONE (its stated acceptance evidence — nested split proof, masked projection tests, normalization leakage tests — is now complete) while its declared dependency P0-02 remains TODO. Following D018's precedent, this is recorded rather than reverted: P0-05's evidence does not depend on P0-02's schema work, the same way P0-06's specification did not depend on P0-05's implementation.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` untouched. Existing tracked rows unchanged — verified by rerunning SMOKE `000m` after every code change in this batch and diffing all 102 non-cost rows against `RESULTS.tsv` (0 differing, 0 new) both before and after the panel-repetition change.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D022 — The `splits.gene_panel` fence entry's "measured to exceed the rank signal" claim had no artifact behind it

Date/time: 2026-09-18, P0-05 implementation
Type: implementation
Related task, feature, gate: P0-05
Context: `cnmfbench/provisional.py`'s `splits.gene_panel` entry stated panel variance "was measured to exceed the rank signal," dating to the first skeleton commit (`58249e2`), whose own commit message does not mention it. Every config file has always carried `panel_repetitions: 1`; nothing in the codebase read that key before this session (`PROGRESS.md` recorded the gap: "the config surface already exists and is ignored"); and `diagnostics.donor_blocking_gap` — the module that does vary a panel — draws its single gene split outside its repeat loop, so it could not have produced a between-panel variance either. No artifact, run, or test result backs the claim.
Options considered: (a) leave the claim as written, treating it as a plausible prior; (b) remove the claim and state plainly that panel variance was unmeasured, since `docs/AGENTS.md:36` requires not fabricating test outputs or results and this line functions as an unfounded result; (c) remove the claim and replace it with the number this session's panel-repetition work actually measures.
Decision: **(c).** The entry now says panel variance was unmeasured before this session, states that the earlier claim had no artifact behind it, and the panel-repetition block measures it directly: at SMOKE `000m`, between-repetition sd is 13-19% of the mean `heldout_squared_prediction_error_counts_v1` across `k=2,3,4` and both outer folds (repetition sd/mean at `outer_0`: k=2 19.1%, k=3 13.0%, k=4 12.6%; `outer_1`: k=2 19.5%, k=3 18.0%, k=4 17.1%) — non-trivial relative to the loss scale itself, though this is a SMOKE-tier measurement, not yet a DEVELOPMENT-tier one, and not compared here against the between-rank signal PROTOCOL's own rank-selection rule reads.
Reason: (a) is exactly the thing `docs/AGENTS.md:36` forbids — a load-bearing scientific claim standing on nothing. (b) is honest but throws away work already done in the same session that answers the question the claim was gesturing at.
Evidence paths and experiment IDs: `cnmfbench/provisional.py`; `cnmfbench/skeleton.py` (`panels`, `_score_with_panel`, `panel_variance_by_k`); measured via `python -m cnmfbench.skeleton --config docs/benchmarks/configs/smoke_000m.yaml` with `panel_repetitions: 5`, read from `diagnostics.json`, not merged into `RESULTS.tsv` (repetition 0 only emits rows, per §4.1/§5.1 — see the comment above `panels = [...]` in `skeleton.py`).
Trade-offs and negative evidence: the SMOKE number is not yet compared against the rank-selection signal it was originally invoked to bound, so this entry corrects a fabrication without yet resolving the scientific question it stood in for. That comparison is DEVELOPMENT-tier work, appropriately deferred rather than rushed to produce a replacement headline number under the same time pressure that produced the original unsourced one.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` untouched.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D023 — The P0-06 baseline selector is implemented; `delta` stays null and PROTOCOL.md is untouched this session

Date/time: 2026-09-19, P0-06 implementation
Type: implementation
Related task, feature, gate: P0-06, gate P0
Context: `PROTOCOL.md` §1/§1.4 freeze the selector's equation, sensitivity heuristic and four edge cases; §2 freezes `delta`'s calibration procedure and the normative check order (null-`delta` refusal evaluated first, before any §1.4 edge case, so a flat curve cannot be used to obtain a rank while `delta` is still null). `PROGRESS.md:458` states `delta` is one of seven items batched into a single v1.1 protocol amendment ("do not version PROTOCOL twice"); three places (`PROTOCOL.md` §2, `PROGRESS.md:437`, `skeleton.py:192-197`) say that amendment fires at the start of P1 (P1-01). The user was asked explicitly which to do this session and chose: calibrate and record `delta`'s value and evidence, but do not amend PROTOCOL now.
Options considered: (a) implement the selector and also amend PROTOCOL.md to v1.1 with all seven batched items, unlocking feature A; (b) implement the selector only, defer all calibration to a later session; (c) implement the selector, run the §2 calibration procedure and record the resulting curves/dispersion/value in this file, but leave `PROTOCOL.md` byte-identical at v1.0.1 with `delta: null` and defer the amendment (which needs all seven items, not one) to P1-01.
Decision: **(c)**, per explicit user direction.
Reason: (a) would rush six items that were deliberately batched for reasons recorded elsewhere in this file (D009's vocabulary batching cites the same logic — one amendment, not several), under the time pressure of a single session, and would unlock feature A before D020's inner-budget sampling design (specified, not built) is ready. (b) throws away calibration work this session can safely do, since §2 step 4 ("record the curves, the dispersion estimate and the chosen value in DECISIONS.md") does not require the protocol file to change — DECISIONS.md is exactly where that record belongs before the amendment event.
Evidence paths and experiment IDs: `cnmfbench/selector.py` (**new**, `select_rank`/`SelectionResult`), `cnmfbench/tests/test_selector.py` (**new**, 12 tests — one per §1.4 branch, plus the load-bearing ordering test `test_flat_curve_still_refuses_while_delta_is_null`). `python -m pytest cnmfbench -q` → 241 passed (229 + 12), exit 0. `sha256sum docs/planning/PROTOCOL.md` unchanged: `715639895663bc74e7b864bc1cfae60c2fcd05b013e25f23016d45e86f4f9ca5`.
Trade-offs and negative evidence: **P0-06's ledger row (`PROGRESS.md:68`) is not DONE after this session.** It requires both (a) `delta` set in the frozen protocol and (b) code implementing the selector; only (b) closes here. `records.py:176-183`'s `selected_rank must be null this session` refusal is left in place — with `delta` null, nothing selects, so it remains a correct free consistency check, not a stale guard. `splits.outer_donor_folds` stays fenced (D021's reassignment to P0-06 required `delta` set **and** feature A runnable in production; neither happens this session).
Consequences for the baseline and active feature set: none algorithmic; no `RESULTS.tsv`/`EXPERIMENTS.tsv` row changes meaning. `src/cnmf/**` untouched.
Protocol/data versions superseded: none. `PROTOCOL.md` remains v1.0.1.
Independent confirmation needed: no.

## D024 — The silhouette sweep's cost is folded into the shared fit-scope row, because it previously cost nothing on any tracked row

Date/time: 2026-09-19, P0-06 implementation
Type: implementation
Related task, feature, gate: P0-06, P1-01 (feature A), the `000`-vs-`100` comparison
Context: `_fold_diagnostics` (`skeleton.py`) runs one `consensus(skip_density_and_return_after_stats=True)` call per candidate rank — the silhouette sweep the A-OFF baseline selector reads (`PROTOCOL.md:48`, §1.1: "both inputs already exist on disk after a rank sweep; the selector computes nothing new"). Before this session, the call sat between the fit-timing window (closed at `fit_wall`/`fit_cpu`, immediately after `obj.combine()`) and the per-rank timing window (opened fresh per rank, later in the same function), so its wall/cpu landed on **no** `RESULTS.tsv` row. The A-OFF baseline's entire selector input therefore cost nothing, while D019 establishes that A-ON's inner-fold fits will be timed once A runs. `AGENTS.md:30` names "total compute/failure costs" as a required endpoint of exactly the `000`-vs-`100` comparison this whole programme targets, and `skeleton.py`'s own `_cost` docstring already records this class of mistake happening once before (D010/the B-C session's cost-window bug, which understated feature A by a factor of ~2.2 until fixed).
Options considered: (a) leave it unattributed until feature A actually runs, since no tracked comparison reads A-OFF vs A-ON cost today; (b) attribute it now, folded into the existing fit-scope row, since that row already exists specifically to hold shared per-fold cost that no single candidate rank owns; (c) give the sweep its own cost row.
Decision: **(b).** The sweep, like the fit itself, serves every candidate rank in the fold and has no single rank to attribute to — exactly the fit-scope row's existing purpose (`skeleton.py:717-723`'s own comment: "One `prepare` per fold serves every candidate rank... Its cost therefore belongs to no single rank").
Reason: (a) would let the exact bias this entry describes persist into the first `000`-vs-`100` comparison, discovered only after A-ON rows exist to reveal it by contrast — worse than fixing it while the fix's effect is small and can be verified in isolation. (c) invents a twelfth cost-bearing row shape where the existing fit-scope shape already fits.
Evidence paths and experiment IDs: `cnmfbench/skeleton.py` (the `diag_t0, diag_c0` / `fit_wall +=` / `fit_cpu +=` block, immediately preceding `results, experiments = [], []`). Verification: `smoke_000m.yaml` rerun (`p06_cost_check`, deleted after comparison, not committed) against `RESULTS.tsv` — **0 non-cost rows differing** (134/134 non-cost values identical), cost rows moved as expected: the `outer_0` fit-scope row's `wall_seconds_v1` moved 0.615s → 0.844s (+0.229s, attributable to a 3-rank silhouette sweep at SMOKE scale, ≈0.076s/rank) and `cpu_seconds_v1` 0.368s → 0.598s. Per-rank (`k2`/`k3`/`k4`) rows also moved by comparable relative amounts (+30-40%) despite being untouched by this change — ordinary wall-clock run-to-run noise (this cluster's timing is not deterministic across runs, unlike the bitwise-checked content columns), not evidence of a second defect.
Trade-offs and negative evidence: this makes every existing tracked cost row for a fit-scope experiment_id **historically an undercount** relative to what this fix now measures — not regenerated in this session (regenerating `RESULTS.tsv`'s existing cost rows is a larger undertaking than this fix and belongs with whichever session next needs bitwise-comparable cost totals; flagged here rather than silently left). No SMOKE/DEVELOPMENT run in this session was merged into tracked `RESULTS.tsv`/`EXPERIMENTS.tsv`, so no tracked row is stale as of this entry — the undercount applies only if a future session compares a new cost-inclusive run against an old cost-exclusive one without reading this entry first.
Consequences for the baseline and active feature set: fit-scope wall/cpu costs will read slightly higher from this session onward for every configuration (A-OFF and, once A runs, A-ON alike) — the sweep runs regardless of A's bit, so this is not itself an A-vs-baseline asymmetry, only the removal of a A-OFF-specific free lunch relative to A's inner-fold cost once that exists.
Protocol/data versions superseded: none — PROTOCOL.md does not specify where the sweep's cost is attributed, only that "total compute/failure costs" (`AGENTS.md:30`) is a required endpoint.
Independent confirmation needed: no.

## D025 — `make_experiment_id` gains an optional `inner_split_id`, pre-emptively, because two inner folds of one outer fold collide on `experiment_id` today

Date/time: 2026-09-19, P0-06 implementation
Type: implementation
Related task, feature, gate: P0-06, P1-01 (feature A), D020
Context: D020 named this the "most load-bearing" of the eight sub-problems in its inner-budget sampling design ("`make_experiment_id` has no `inner_split_id` slot, so two inner folds of one outer fold at one rank collide on `experiment_id` today, and that collision must be resolved before any inner row can be written, independent of the sampling arithmetic"). `_run_inner_fold` (`skeleton.py`) already produces per-inner-fold, per-rank score dicts keyed by `inner.inner_split_id`, but nothing calls `make_experiment_id` for them yet — no production caller exists (D019), so the collision has never been observed, only predicted.
Options considered: (a) leave it for whichever future session first writes an inner-fold row, since nothing calls it today; (b) resolve it now, following the `variant` precedent already established for exactly this kind of schema gap (`records.py:110-122`).
Decision: **(b)**.
Reason: the fix is small, isolated to `make_experiment_id`, and D020 already did the design work of identifying it as a precondition independent of the sampling arithmetic (sub-problems 1-7, which are NOT resolved here — feature A cannot run regardless, so implementing the budget-scaling machinery now would have no caller to exercise it and no way to verify it beyond unit tests, which is exactly the risk D020 declined). Resolving the identifier gap now, while D020's reasoning is on hand, means whichever session eventually implements the sampling machinery starts with one fewer precondition to rediscover.
Evidence paths and experiment IDs: `cnmfbench/records.py` (`make_experiment_id`, new optional `inner_split_id` parameter, folded into the digest and the label only when truthy — the exact `variant` pattern). Pinning test: every existing call site (`skeleton.py:343, 375, 734, 833`, none of which pass `inner_split_id`) produces byte-identical ids to before this change, since the parameter defaults to `None` and is a no-op unless set. `python -m pytest cnmfbench -q` → 241 passed, exit 0 (see D023's evidence for the same run).
Trade-offs and negative evidence: this resolves only sub-problem 8 of D020's eight. Sub-problems 1-7 (arm-based branching, `s_g` on sampled rows, the inner `_panelref`, cells-not-donors budget scaling, per-fold seed derivation via `SeedSequence`, two new `check_preconditions` checks, cost-window separation for inner fits) remain deferred to whichever session first makes an A-ON `matched_budget` configuration runnable, exactly as D020 specified. No inner-fold row has been written by this session — the fix has no caller yet, by design (D019).
Consequences for the baseline and active feature set: none today; no tracked row's id or content changes. Removes one of D020's eight preconditions for any future A-ON matched_budget run.
Protocol/data versions superseded: none.
Independent confirmation needed: no.

## D026 — `delta` calibration evidence recorded; the fourth dependency-order deviation

Date/time: 2026-09-19, P0-06 implementation
Type: scientific finding + deviation
Related task, feature, gate: P0-06, P1-01
Context: PROTOCOL.md §2's calibration procedure requires computing silhouette curves across the candidate grid on `base_identifiable` and `A_weak` at DEVELOPMENT tier, choosing `delta` from the **within-scenario dispersion of silhouette across optimizer seeds**, and recording the curves, dispersion estimate and value here **before** checking which K the value selects (step 4, then step 5). This entry is that record. As at D023, the value here is calibration evidence, not a protocol amendment — `PROTOCOL.md` stays at v1.0.1 with `delta: null` in the file itself.

**Runs.** Four seeds per scenario, varying `cfg["seed"]` only (`panel_seed: 20260918`, `sampling_seed: 424242` fixed throughout, so this isolates optimizer-seed noise from the panel-repetition variance D022 measured separately): `base_identifiable` seeds `{90210, 90211, 90212, 90213}` — 90210 reuses the existing `p04-dev-000m` run rather than regenerating it (same config, same seed, already on disk); `A_weak` seeds `{90210, 90211, 90212, 90213}`, all newly run (`A_weak` had never been run at any tier before this session — confirmed to execute cleanly at SMOKE first, per plan step 5). Configs: `docs/benchmarks/configs/development_{000m,a_weak_000m}_seed{90210..90213}.yaml`. Run directories: `results/exploratory/p04-dev-000m` (seed 90210, base_identifiable, pre-existing) and `results/exploratory/p06-delta-{000m,aweak}-seed{90211,90212,90213,90210}` (six new runs). Kept under `results/exploratory/` only, **not** merged into tracked `RESULTS.tsv`/`EXPERIMENTS.tsv` — these are calibration inputs to a protocol constant, not benchmark rows, and PROTOCOL §5.1/§5.2 do not name a silhouette-dispersion metric for `RESULTS.tsv` to carry.

**Per-`(outer_split_id, K)` standard deviation of silhouette across the four seeds** (full table in the run transcript; `k` in each scenario's candidate grid `{4..10}`):

| scenario | outer fold | k range with sd < 0.001 | k range with sd 0.01-0.05 | max sd (k) |
|---|---|---|---|---|
| `base_identifiable` | `outer_0` | k=4-7 (0.0002-0.0005) | k=8 (0.0481), k=9 (0.0201), k=10 (0.0137) | **0.04812** (k=8) |
| `base_identifiable` | `outer_1` | k=4-7 (0.0003-0.0007) | k=8 (0.0216), k=9 (0.0150), k=10 (0.0058) | 0.02155 (k=8) |
| `A_weak` | `outer_0` | k=4,5 (0.0023, 0.0023) | k=6-10 (0.0273-0.0437) | 0.04361 (k=10) |
| `A_weak` | `outer_1` | k=5 (0.0021) | k=4,6-10 (0.0094-0.0447) | **0.04469** (k=8) |

The dispersion is **not uniform across K within a scenario**: both scenarios show a low-noise plateau at small K (silhouette near 1.0, sd ≲ 0.001) and a high-noise region above it, where the curve is also descending fastest. `A_weak`'s low-noise plateau is shorter (k=4-5 vs k=4-7) and its transition noisier, consistent with the scenario's own stated rationale ("rank selection should find it harder, not impossible").

**Decision: `delta` = 0.04812** — the maximum per-`(outer_split_id, K)` standard deviation observed across *both* required scenarios and all four outer folds (`base_identifiable outer_0, k=8`).
Reason: §2 step 3 calls `delta` a "practically indistinguishable stability" band that "must be on the scale of the noise in that measurement, not on the scale of the between-K differences it will adjudicate." Taking the single largest measured noise value, rather than a mean or a region-restricted statistic, means no `(fold, K)` pair anywhere in the calibration data has noise exceeding `delta` — the alternative (e.g., a mean of ≈0.009-0.023) would let the selector treat some of this session's own measured noise as signal at exactly the K values (8-10) where the curve is steepest and a false "improvement" would be easiest to manufacture. This choice was made and written down (this paragraph) **before** running `select_rank` on any curve, per the step-4-before-5 ordering §2 requires.
**What it selects (checked only after the above was recorded, never used to revise it):** on `base_identifiable`, `K* = 7 = K_true` in **both** outer folds (sensitivity heuristic `K*_sens` = 4 and 5 respectively — a real divergence between the two rules, reported rather than reconciled, as §1.3 requires). This falls inside the pre-registered window `PROGRESS.md:451` states from the single-seed `p04-dev-000m` run alone (`delta` in `[0.0011, 0.0714)` selects `K*=7=K_true`), so the four-seed calibration **confirms** a prediction made before this session's runs existed, rather than producing a new claim. On `A_weak`, `K* = 6` in both outer folds — **below** `K_true = 7`, with `K*_sens = 5` in both. Neither boundary flag nor degenerate flag fires anywhere.
**A_weak's under-selection is itself a stated finding, not noise to explain away**: `A_weak`'s own design rationale (`scenarios.py:136-142`) is "rank selection should find it harder, not impossible... this is where a selector that merely tracks in-sample error is expected to fail" — the A-OFF baseline under-selecting by exactly one rank on the scenario built to stress it is the predicted headroom for feature A, not a defect in this calibration.
**A fourth dependency-order deviation, following D018/D021's precedent:** P0-06 proceeds (selector implemented, calibration run) while its declared dependency P0-02 (data/artifact schemas) remains TODO, the same pattern D018 recorded for P0-06's specification half and D021 recorded for P0-05's completion. Recorded rather than reverted, for the same reason as both prior instances: P0-06's evidence (the selector's correctness, the calibration measurement) does not depend on P0-02's schema work.
Trade-offs and negative evidence: four seeds is a thin basis for a standard deviation — the calibrated `delta` carries visible sampling uncertainty of its own, which `PROGRESS.md:44` already anticipated generally for DEVELOPMENT-tier constants ("`delta` calibrated there will carry visible uncertainty, and that uncertainty must be reported with it"). The max-of-observed-noise choice is conservative in one direction (it cannot mistake noise for signal at any measured point) but is not itself immune to a fifth seed producing a larger outlier sd — recalibrating `delta` on a later, larger seed set before the v1.1 amendment commits it would not be "adjusting using outer-test or true-rank information" (forbidden by §2 step 5) and remains open. The `A_weak` under-selection was read only after `delta` was fixed, exactly as ordered, but a reader should not mistake "this matches the scenario's design rationale" for independent confirmation — it is one calibration run's outcome on one scenario, not a P1-03 result.
Consequences for the baseline and active feature set: none until P1-01 amends PROTOCOL to v1.1 and un-refuses feature A. This value is not usable by `select_rank` in production until that amendment — calling it with this recorded `delta` before the amendment would itself violate §2's null-until-amended intent, since the frozen file still says `delta: null`. When P1-01 does set it, this entry's evidence is the record §2 step 4 requires; no additional calibration run is implied unless the amendment's own review asks for more seeds given the trade-off noted above.
Protocol/data versions superseded: none — this entry does not change `PROTOCOL.md`.
Independent confirmation needed: no (this is development-tier calibration evidence, not a confirmation-tier result).

## D027 — P0-07 un-fences `skeleton.run`: cache, restart, smoke workflow, SLURM status

Date/time: 2026-09-19, P0-07 session
Type: implementation
Related task, feature, gate: P0-07, gate P0
Context: `provisional.py` fenced `skeleton.run` as a "linear in-process driver" with
"no cache, no restart, no CI, no SLURM", requiring "the P0-07 workflow with restart
and cache-invalidation tests" before un-fencing. P0-07 built exactly that:
`cnmfbench/cache.py` (content-keyed `cache_key`, atomic `SUCCESS.json` sentinel via
tmp + `os.replace`, `needs_recompute` covering changed inputs, changed options,
changed code and interrupted outputs), `cnmfbench/tests/test_cache.py` (6 tests),
`workflow/Snakefile` (`smoke`, `clean_smoke`), `workflow/scripts/run_smoke.py`
(runnable without a Snakemake binary, which is not installed on this host),
`workflow/profiles/local/config.yaml` and `workflow/profiles/slurm/config.yaml`.
Options considered: (a) keep the fence while adding more orchestration (CI workflow,
full Snakemake rule set for all 11 pipeline stages); (b) un-fence now on the
evidence that the named hardening requirement is met.
Decision: **(b).** The `@provisional("skeleton.run")` decorator and its registry
entry are deleted together, in this commit with this entry — per the fence's own
rule that closing means deleting both, not forgetting to look.
Evidence paths and experiment IDs: `python -m pytest cnmfbench/tests/test_cache.py -q`
→ 6 passed; `python -m pytest cnmfbench -q` → 247 passed;
`python workflow/scripts/run_smoke.py --config docs/benchmarks/configs/smoke_000m.yaml --out-root results/scratch --run-id smoke`
→ exit 0, 134 results / 8 experiments, `results/scratch/smoke/SUCCESS.json` written
(gitignored scratch, not tracked evidence). `sbatch` exists on this host but no
benchmark job has been submitted through the SLURM profile: status
**NOT_RUN_ON_SLURM**, recorded in the profile itself.
Trade-offs and negative evidence: no CI workflow (`.github/`) was added — there is
no remote to run it against yet (branch is local-only, 51 ahead of origin/main) and
adding CI YAML untested by any runner would be the kind of unverified syntax
IMPLEMENTATION_PROMPT §11 forbids. The Snakefile covers smoke only, not the full
11-stage rule set; extending it is future P0-07-adjacent work, not a gate blocker.
The full test suite still reports `test_the_gate_is_blocked_while_components_are_provisional`
passing because three fenced components remain (`splits.outer_donor_folds`,
`features.consensus_c`, `features.discovery_sample_b`) — the P0 gate stays blocked,
correctly.
Consequences for the baseline and active feature set: fence four → three. No
`src/cnmf/**` change. No tracked `RESULTS.tsv`/`EXPERIMENTS.tsv` change.
Protocol/data versions superseded: none. PROTOCOL.md stays v1.0.1.
Independent confirmation needed: no.

## D028 — P0-02 closes the D006 guard: validation only, no redefinition

Date/time: 2026-09-19, P0-02 session
Type: implementation
Related task, feature, gate: P0-02, gate P0
Context: D006 inverted P0-02/P0-03 and forbade P0-02 from redefining PROTOCOL §6 —
any inadequacy found would be a versioned amendment, not a schema-layer choice.
P0-03 then built the simulator against §6, and `contract.py`/`io.py` grew the
subset of checks the simulator needed to be usable at all. The ledger row stayed
TODO because three items were still missing: schema tests, manifest examples
and explicit expression units.
Options considered: (a) rework `contract.py`/`io.py` into a unified schema
framework; (b) add only the missing layer — unit tagging (§6.2), manifest-key
validation with a committed example (§6.6), rank-grid validation (§1.1/§1.4) —
leaving existing modules and their tests untouched.
Decision: **(b).** `cnmfbench/schemas.py` adds `ExpressionMatrix` (unit system
as data, `UnitMismatch` refusal, mirroring D013's `Spectra`), `DATASET_MANIFEST_KEYS`
+ `validate_dataset_manifest`, and `validate_rank_grid`. No existing module was
edited; §6 was read, not rewritten.
Evidence paths and experiment IDs: `cnmfbench/schemas.py`;
`cnmfbench/tests/test_schemas.py` (14 tests — every refusal exercised, plus a
real `simulate()` manifest and the committed
`docs/benchmarks/registry/dataset_manifest_example.json` both satisfying the
schema); `python -m pytest cnmfbench -q` → 261 passed, exit 0.
Trade-offs and negative evidence: the new validators are not yet wired into
`skeleton.py` call sites — they are available checks, not enforced gates. Wiring
them into the runner (e.g. validating the candidate grid in `check_preconditions`,
tagging `X` at the transform boundary) is a follow-up decision with its own
blast radius, not smuggled into this commit. `validate_mapping_keys` is a
two-line helper with no direct test; it is exercised only if a caller adopts it.
Consequences for the baseline and active feature set: none algorithmic; no
`src/cnmf/**` change; no tracked-row change. Unblocks P0-08/P0-09, whose
dependency on P0-02 is now satisfied.
Protocol/data versions superseded: none. PROTOCOL.md stays v1.0.1.
Independent confirmation needed: no.

## D029 — P0-08 DONE: Kang 2018 registered; AIDA/Heart as characterised reserves

Date/time: 2026-09-19, P0-08 session
Type: implementation
Related task, feature, gate: P0-08, gate P0
Context: four prior sessions fetched and characterised candidates (commits
`7725827`, `d9c28da`, `3c10c12`, `069994c`, `28818f5`) but never closed the
ledger row. The evidence already exists in
`docs/benchmarks/registry/p0-08_real_data_candidates.tsv`; this session
verifies rather than repeats it.
Decision: register **Kang 2018** as the public multi-donor dataset —
origin GEO GSE96583 via the pertpy scverse mirror
`https://exampledata.scverse.org/pertpy/kang_2018.h5ad`, sha256
`e6a5adac64dcdeb36eaba27db49b63e0c64bb0ed4a64c6705971506b41c39830`
(**re-verified by re-hash this session, match**), 24,673 cells × 15,706 genes,
donor mapping via the `replicate` column (8 donors, 1,042–5,090 cells each),
stim/ctrl label per cell (12,358/12,315). AIDA v2 (625 donors, single assay)
and Heart snRNA slice (14 donors) stay characterised reserves with their
confounds recorded (site-nested-in-country; kit-nested-in-donor); Stephenson
pertpy distribution is NOT USABLE (log1p-normalised, counts absent).
License caveat (unchanged from the TSV): Kang's terms recorded as the user's
2026-09-18 statement ("MIT"), NOT independently verified; Heart CC BY 4.0 read;
confirm before external publication, local runs unaffected.
Evidence paths and experiment IDs: the TSV (§Kang verdict + donor table +
interferon diagnostic, AUC 0.914–0.948 at every rank, 16/30 ISGs pre-listed);
`sha256sum` match this session; run dir
`/exports/para-lipg-hpc/mdmanurung/cnmf-realdata/kang_run/` (ad-hoc diagnostic,
no tracked rows by design).
Trade-offs and negative evidence: 8 donors is thin for feature A (the TSV says
so itself — donor count dominates per D008, so Kang cannot test A's premise);
Kang's role is activity-program recovery with a labelled ground truth, not rank
selection. No benchmark row has used real data yet — registration is done,
biological confirmation is not claimed.
Consequences for the baseline and active feature set: none algorithmic.
Protocol/data versions superseded: none.
Independent confirmation needed: no (registration, not a result).

## D030 — P0-09 BLOCKED: no R on this host, GeneNMF comparator unavailable

Date/time: 2026-09-19, P0-09 session
Type: implementation / deviation (external blocker)
Related task, feature, gate: P0-09, gate P0
Context: P0-09 needs the pinned GeneNMF R workflow plus an R smoke result and
conversion tests. Checked this session: no `Rscript` on PATH, no `/usr/lib/R`,
`module spider R` / `rlang` / `Rscript` all resolve to nothing R-related. An R
comparator cannot be built or tested here.
Options considered: (a) install R locally; (b) record BLOCKED with the exact
failed commands and keep the task open for a host with R.
Decision: **(b).** Installing an R stack (plus RcppML + GeneNMF deps) into the
locked `cnmf_bench` environment would change `environment_hash`, the recorded
provenance on all tracked rows — the same reason pertpy was deliberately not
installed at P0-08. Per the ledger footnote, P0-09 stays BLOCKED (never becomes
DONE by redefinition) and the P0 gate documents no-comparator scope.
Evidence paths and experiment IDs: `which R Rscript` (both absent);
`module spider Rscript` → "Unable to find"; `ls /usr/lib/R` → absent.
Trade-offs and negative evidence: whole-workflow GeneNMF comparisons
(`genenmf_native` anchor) are unavailable until an R host appears; factorial
A/B/C claims are unaffected since they never involve GeneNMF.
Consequences for the baseline and active feature set: none.
Protocol/data versions superseded: none.
Independent confirmation needed: re-check on any new host before unblocking.

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
