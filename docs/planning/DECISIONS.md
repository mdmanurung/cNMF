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
Trade-offs and negative evidence: **count-unit reporting removes the artifact from the comparison but does not make the two arms the same estimator.** The inference NNLS still solves in each arm's own `1/s_g` weighting, so two arms with identical programs return slightly different usages. That residual is arguably part of what B does in deployment — a practitioner running donor-balanced discovery gets the donor-balanced scale too — but it is a property of the intervention, not something the comparison controls for, and no B result may be reported as if it had been. Second, **a guard that should have caught this did not**: `analysis.assert_poolable` refuses rows spanning more than one `preprocessing_hash` and its docstring claims such rows differ in "gene panels and per-gene scales", but the hash carries `s_g_ddof` and not `s_g` — all four configurations share `c9ba55b825846b53205c1816` at `outer_0`, so the guard would have permitted the pooling its docstring promises to refuse. The arms *are* distinguished by `discovery_hash`, which `assert_poolable` does not read. The fix is deferred, not done: landing a hash change while the DEVELOPMENT factorial is mid-flight would give one table two code definitions. It must also quantize `s_g` to fixed significant digits, or a legitimate replay would trip the guard on BLAS noise. Third, this supersedes the `hardening_requires` text on `features.discovery_sample_b`, which asks for an audit asserting `s_g` identical across arms — that assertion cannot be met as written and is replaced by *reporting* the drift.
Consequences for the baseline and active feature set: none algorithmic; `src/cnmf/**` untouched and verified byte-identical. Feature B's scientific_adoption remains **INCONCLUSIVE** — the correction does not change the verdict, because every difference measured is smaller than the scale drift the arms already differ by, at n=2 folds with a single draw per arm.
Protocol/data versions superseded: none. The ablation plan's `hold_preprocessing_constant_across_B: true` is not edited; this entry records that it is met for `G` and unmeetable for `s_g`, which is a finding about the constraint set, not a change to the plan.
Independent confirmation needed: yes — sampling replicates, so the draw's own variance is reported rather than assumed negligible. Until then no B number may inform an adoption decision.

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
