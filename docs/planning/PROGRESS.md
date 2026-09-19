# cNMF incremental development — progress tracker

**Specification prepared:** 15 September 2026  
**Target repository:** `dylkot/cNMF`  
**Current state:** IN_PROGRESS — S0 closed, protocol frozen at v1.0.1, simulator built and measured, the benchmark loop closes end to end, and the DEVELOPMENT tier has been run under a pre-registered feasibility gate: `RESULTS.tsv` holds 1342 rows and `EXPERIMENTS.tsv` 40, across `SMOKE` and two `DEVELOPMENT` runs. **P0-05 is DONE.** **P0-06 (the selector and `delta`) is IN_PROGRESS — the selector is implemented and `delta` is calibrated and recorded (D023-D026), but PROTOCOL.md is deliberately left at v1.0.1 with `delta: null`; the amendment to v1.1 is a P1-01 event batched with six other items, per explicit user direction.** No new rows entered `RESULTS.tsv`/`EXPERIMENTS.tsv` this session — verification and calibration runs were compared/measured and kept only under `results/exploratory/`  
**Important:** No target-package code has been modified. The first rows exist but **establish execution, not scientific benefit** — `smoke_can_promote_feature: false` and `allow_scientific_promotion: false` make them unusable for any adoption decision, and every row carries `status: ok_provisional` because throwaway components produced it.

## 1. Session dashboard

| Field | Current value |
|---|---|
| Active prototype | P0 — loop closes at SMOKE and DEVELOPMENT; P0-04 metrics **wired into the runner**; features B and C switchable and exercised at both tiers; nested donor folds and the §3.2 leakage audit implemented and tested against real fits (P0-05); P0-06's selector is implemented and `delta` calibrated (D026), PROTOCOL still v1.0.1; **P0-07 DONE** (cache/restart + smoke workflow, fence four → three, D027) |
| Active task | P1-01 (v1.1 amendment + frozen A margins — the gate is written, the amendment is next) |
| Next task | **P0-08** — register a public multi-donor dataset and verify metadata (dependency P0-02 now DONE; or record an explicit external blocker) |
| P0-02 note | P0-02 is DONE (schemas + manifest example + unit tags, D028); its dependency slot for P0-08/P0-09 is satisfied. P0-05/P0-06 proceeded around it by recorded deviation (D018/D021/D026); that history stands and is not rewritten. |
| P0-06 note | **P0-06 is DONE** (closed by the v1.1 amendment, D033). The tension is resolved the way the dashboard allowed: P1-01 ran the amendment as its first act, with P0-10 already closed — no dependency was edited, the ordering P0-10 → P1-01 → (P0-06 closes) is exactly what happened. |
| Implementing agent/session | OpenCode session, 2026-09-19 (P0-07) |
| Local checkout | `/exports/para-lipg-hpc/mdmanurung/cNMF`, branch `main` |
| Environment | conda env `cnmf_bench` (Python 3.10.20, cnmf 1.7.1 editable from this checkout, BLAS scipy-openblas 0.3.29). Activate: `module load tools/miniconda/python3.10/23.3.1 && source activate cnmf_bench` |
| Pinned upstream SHA | `5dbc5baaa0b9079b55bce554d801caa235a50457` (resolved via `git ls-remote https://github.com/dylkot/cNMF HEAD`; identical to local HEAD — see DECISIONS.md D002) |
| Implementation SHA / dirty patch hash | **`5f22d55caf2060d48af3877f8e1a57bf051c0e34`** — first harness commit (planning bundle + P0-01 evidence), parent `5dbc5ba…` (pinned upstream). Local only, **not pushed**. `src/cnmf/**` unmodified: `git diff 5dbc5ba..HEAD -- src/` is empty. Note this row names the commit *containing* the evidence; the row itself necessarily lands in the following commit |
| Environment lock hash | conda `4b79d3c18a7c2cc555a1755140579a82bdddbdc7d96c2eb2eef9b0ca0052e83b`, pip `e5082a753229bbde7e2c469bfcdf46786289522b5f51784a7594aa50b60c86b9` (`docs/benchmarks/registry/env_cnmf_bench.{conda,pip}.txt`) |
| Reproducibility tolerance | Relative Frobenius error < **1e-5**, same-environment, per artifact (D004, **CONFIRMED at P0-04** — noise 2.5e-8, mildest structural corruption 3.6e-3, so the tolerance sits ~400x above noise and ~360x below signal). Near-zero absolute floor set at **1e-12**, chosen while no near-zero artifact exists. Upstream's absolute `TOLERANCE=1e-4` is explicitly **not** reused. No bitwise claim across BLAS/versions/threads/platforms |
| Protocol version/hash | **FROZEN — v1.1**, `docs/planning/PROTOCOL.md`, sha256 `cc5241076a6c3e5f98b7575f0b09b12337c119e6ddaea685514692ebc9d42ec9`, recorded in `ablation_plan.yaml`. `confirmation_unlocked: false` — adoption still needs frozen A margins applied to A-ON rows (margins frozen in `contracts/A.md`, no A-ON row exists) |
| Baseline selector specification | **IMPLEMENTED AND OPERATIVE under v1.1.** `cnmfbench/selector.py` (`select_rank`) with frozen `delta = 0.04812`. Production caller arrives at P1-02 |
| Recommended configuration | None, and none is possible yet — no configuration has been evaluated. `000` is the *reference*, not a recommendation |
| Latest evidence tier | **DEVELOPMENT** — two runs, 610 + 610 rows and 16 + 16 experiments (the second is the `variant: conv1000` convergence diagnostic), plus 122 + 8 at SMOKE: **1342 / 40** tracked. Configuration `000`, all `status: ok_provisional`, `selected_rank` null throughout. `allow_scientific_promotion: false`, so this informs design and promotes nothing |
| Last update by implementing agent | P0-07 session, 2026-09-19 |
| Session checkpoint | S0-01, S0-02, S0-03, P0-01, **P0-03 DONE**, **P0-04 DONE**, **P0-05 DONE**. Protocol still frozen at v1.0.1 (unchanged). **P0-06 IN_PROGRESS**: selector implemented (`cnmfbench/selector.py`) and `delta` calibrated and recorded (D023-D026, `delta = 0.04812`), but PROTOCOL.md's `delta: null` is untouched — the v1.1 amendment is deferred to P1-01 by explicit user direction, so P0-06's ledger row (requires both delta-in-protocol and code) stays IN_PROGRESS, not DONE. **241 harness tests pass (229 + 12 new selector tests); non-cost tracked rows unchanged from the P0-05 session, verified by rerun-and-diff** (`smoke_000m.yaml`, deleted after comparison). Two adjacent defects fixed this session: (1) the silhouette sweep that is the selector's entire input cost nothing on any tracked row — now folded into the shared fit-scope cost row (D024; cost rows moved, non-cost rows did not); (2) `prediction_error` was computed by `_fold_diagnostics` but never recorded — now captured as `prediction_error_by_k` (a diagnostic, never a `RESULTS.tsv` metric, per §5.2). D020's most load-bearing sub-problem (the `experiment_id` collision between two inner folds of one outer fold) is pre-emptively resolved (D025) via an optional `inner_split_id`, following the `variant` precedent — unused by any caller today (no A-ON run exists), but removes one precondition for whenever one does. `A_weak` (never run at any tier before this session) confirmed to execute cleanly at SMOKE and was then run at DEVELOPMENT across 4 seeds for calibration. `splits.outer_donor_folds` remains fenced (D021's condition — `delta` set **and** feature A runnable in production — is not met this session). Features B and C, the four A-OFF factorial cells, and the feasibility NO-GO are all unchanged from the P0-05 session |

## 2. Progress counts

**9 / 31 tasks DONE** (S0-01, S0-02, S0-03, P0-01, P0-03, P0-04, P0-05, P0-07, P0-02).  
**13 / 31 tasks DONE** (S0-01, S0-02, S0-03, P0-01, P0-03, P0-04, P0-05, P0-07, P0-02, P0-08, P0-09, P0-10, P0-06).  
TODO: 15 · IN_PROGRESS: 1 (P1-01 — amendment committed; criterion-2′ run in flight) · VERIFY: 0 · BLOCKED: 0 · DROPPED: 0

Scientific adoption remains separate and untouched. P0-01 establishes that the measuring apparatus runs and that upstream reproduces within a declared tolerance; S0-03 establishes the rules by which future evidence will be judged; the skeleton establishes that the loop executes end to end. **None of that is evidence for any feature.** Benchmark numbers now exist, but only at SMOKE tier, from fenced throwaway components, for the reference configuration `000` — there is nothing to compare them against, and `smoke_can_promote_feature: false` forbids using them if there were.

States: TODO → IN_PROGRESS → VERIFY → DONE; also BLOCKED and DROPPED. Keep the denominator fixed for this scope; show dropped and blocked counts separately. Implementation completion is not scientific adoption.

## 3. Prototype and feature gates

| Prototype | Intervention | Software status | Scientific adoption | Evidence tier | Gate artifact |
|---|---|---|---|---|---|
| P0 | Unchanged baseline + evaluation | **PASS (smoke only)** | NOT_APPLICABLE | **SMOKE** | Not created — the gate cannot close while `cnmfbench/provisional.py` lists six throwaway components (D011) |
| P1 | A: predictive rank selection | UNTESTED | NOT_EVALUATED | NONE | Not created |
| P2 | B: donor-balanced discovery | UNTESTED | NOT_EVALUATED | NONE | Not created |
| P3 | C: run-aware consensus | UNTESTED | NOT_EVALUATED | NONE | Not created |
| Milestone | Factorial + confirmation | UNTESTED | NOT_EVALUATED | NONE | Not created |

Software status: UNTESTED / PASS / FAIL / BLOCKED.  
Adoption: KEEP / CONDITIONAL / DROP / INCONCLUSIVE, after evaluation.  
Evidence tier: NONE / SMOKE / DEVELOPMENT / SIMULATION_CONFIRMATION / BIOLOGICAL_CONFIRMATION.

A scientific DROP may close a stage and permit later independent work. A broken evaluator or unresolved leakage blocks meaningful performance assessment; do not treat it as an unsuccessful scientific feature. Missing external data may permit explicitly simulation-only progress, but cannot support biological claims.

## 4. Task ledger

Update status and evidence after each meaningful code/test batch. A task is DONE only when the required evidence exists. Paths in the last column are acceptance requirements, not claims that those files already exist.

| ID | Stage | Task | Depends on | Status | Acceptance evidence / result link |
|---|---|---|---|---|---|
| S0-01 | Setup | Inspect checkout, instructions, worktree and upstream revision | None | DONE | `git status` clean; local HEAD `5dbc5ba...` resolved identical to `dylkot/cNMF` HEAD via `git ls-remote`; recorded in DECISIONS.md D002 and SOURCE_AUDIT.md §1 |
| S0-02 | Setup | Inspect reference code and record lessons, versions and licenses | S0-01 | DONE | `docs/planning/SOURCE_AUDIT.md` written: full read of `cnmf.py` (1298 lines) and `preprocess.py` (473 lines), dataflow trace of means/std/TPM/refits, MIT license noted. GeneNMF/other sources explicitly deferred to their gating tasks (§2-3 of audit), not pre-scaffolded |
| S0-03 | Setup | Freeze scope and initialize benchmark/decision contracts | S0-02 | DONE | `docs/planning/PROTOCOL.md` written and **frozen** (523 lines; frozen at v1, corrected to v1.0.1 in the P0-03 session, sha256 `71563989…6f4f9ca5`), hash recorded in `ablation_plan.yaml` with `state: frozen`; all seven previously-undefined config names now defined (§1, §3, §4, §5); data contract §6 frozen ahead of the simulator (D006); hash convention §7; `cnmf_full_commit_sha` pinned in `smoke.yaml`. Margins remain null by design (§8) and `confirmation_unlocked: false` |
| P0-01 | P0 | Reproduce pinned upstream installation, tests and example | S0-03 (inverted — see D003) | DONE | Env `cnmf_bench` built + locked (`registry/env_cnmf_bench.{conda,pip}.txt`, SOURCE_AUDIT §1.4); test data downloaded + hashed (`registry/pytest_data_manifest.tsv`, 148 files); `pytest -vs tests` run, **1 failed / 37 passed**, full log at `registry/p0-01_pytest_run1.log`; failure diagnosed to upstream's scale-blind tolerance (D004, D005) with env proven correct by bitwise-identical `norm_counts`/`consensus_spectra` and exact seed/gene-list/YAML matches; determinism measured (`registry/nondeterminism_probe.tsv`, SOURCE_AUDIT §1.5.1); reproducibility tolerance declared (D004) |
| P0-02 | P0 | Implement data/artifact schemas, orientation and provenance checks | P0-01 | DONE | `cnmfbench/schemas.py` — `ExpressionMatrix` unit tags (§6.2, `UnitMismatch` refusal), `validate_dataset_manifest` (§6.6) + committed `registry/dataset_manifest_example.json`, `validate_rank_grid` (§1.1/§1.4). Validation only, no §6 redefinition (D028). 14 tests; 261 harness tests pass |
| P0-03 | P0 | Implement simulator, scenario registry and data tiers | P0-02 (**inverted — see D006**; implements PROTOCOL.md §6 instead) | **DONE** | `cnmfbench/` — simulator, scenario registry (8 specified, 3 implemented), §6 contract checks, §7 hashing, `.h5ad` io with hash verification, diagnostics. Saved truth, independent realizations and the sealed-manifest policy implemented and tested. Donor structure **measured**: blocked-vs-random CV gap real (+2.9%, t=3.10, n=48) but the mechanism is donor count, not per-donor leakage (`registry/p0-03_donor_eligibility_sweep.tsv`, D008). All three feasibility checks run (`registry/p0-03_feasibility_checks.tsv`). 122 harness tests pass |
| P0-04 | P0 | Implement four headline metrics and corruption/invariance tests | P0-03 | **DONE** | `cnmfbench/recovery.py` + `compare.py`; 29 + 9 tests. `program_recovery_cosine_v1` (Hungarian, dummy factors, unit-tagged `Spectra` that refuses an unaligned comparison — D013) and `usage_error_v1` (reuses the alignment object, refuses one from a different fit). Full corruption battery: three invariances asserted to 1e-12, four penalties asserted. `program_precision_v1`/`program_recall_v1` and the `ambiguous` count implemented **and refusing**, thresholds null per §5.2. D004's two obligations discharged. **Wired into the runner**: both metrics write rows at `evaluation_scope: experiment` with the matched null beside them in `EXPERIMENTS.notes` (never a twelfth metric name, §5.1). Exercised over 8 runs at two tiers; recovery peaks at `K_true` in every fold and configuration. `registry/p0-04_features_bc_smoke.tsv`, `registry/p0-04_features_bc_development.tsv` |
| P0-05 | P0 | Implement donor splits, frozen-panel projection and leakage tests | P0-02, P0-04 | **DONE** | Nested split proof: `splits.inner_donor_folds` + `test_inner_folds.py` (8 tests against real cNMF fits, bitwise invariance under perturbed inner-validation donors, positive control, refusal of a leaked outer-test donor). Masked projection / leakage tests: `test_leakage.py` (9 tests — `G`, `s_g`, dictionary, cache identities, stability curve and inference-panel usages all bitwise invariant to perturbed held-out counts; same-input gate; positive control). Normalization leakage tested explicitly (`test_a_held_out_cells_library_total_cannot_reach_its_inference_usages`). Panel repetitions + variance reported (`skeleton.py`'s `panel_variance_by_k`) and the cross-arm `analysis.assert_panels_identical` audit, closing `splits.gene_panel`'s and `scoring.nnls_usages`'s fence entries (D021). **Deviation recorded** (D021, extending D018): P0-02 remains TODO. **Deferred to P0-06** (D020): the inner-budget-under-`matched_budget` sampling design — specified in full but not implemented, since feature A cannot run until `delta` is set regardless |
| P0-06 | P0 | Preregister training-only baseline rank selection and evaluation protocol | P0-04, P0-05 | DONE | Code (`selector.py`, 12 tests) at P0-06 session + constant in frozen v1.1 (`delta = 0.04812`, D026/D033). Refusal spent; production use gated on P1-02 |
| P0-07 | P0 | Implement smoke workflow, CI, cache/restart and local/SLURM profiles | P0-05 | DONE | `cnmfbench/cache.py` (content key, atomic `SUCCESS.json`, 4-axis invalidation) + `tests/test_cache.py` (6 tests); `workflow/Snakefile` + `scripts/run_smoke.py` (exit 0, 134 results / 8 experiments, scratch only); `profiles/local` + `profiles/slurm` (SLURM: NOT_RUN_ON_SLURM). `skeleton.run` un-fenced (D027); fence four → three; 247 harness tests pass |
| P0-08 | P0 | Register a public multi-donor dataset and verify metadata | P0-02 | DONE | Kang 2018 registered (GEO GSE96583 via scverse mirror, sha256 re-verified this session, 8 donors via `replicate`, stim/ctrl labels); AIDA/Heart reserves; Stephenson rejected. License caveat kept (D029) |
| P0-09 | P0 | Implement optional pinned GeneNMF comparator and output checks | S0-02, P0-02, P0-04 | DONE | D030's block lifted via R4_51 (R 4.5.1): GeneNMF 0.9.6 @ `59942b2` (GPL-3, adapter-only) installed, native workflow traced (SOURCE_AUDIT §2.7), R smoke 24 models → 10 MPs, conversion tests green (D031). No comparator rows; gene-set metric deferred to P2-01 |
| P0-10 | P0 | Run baseline/null controls and close P0 readiness gate | P0-01 through P0-09* | DONE | `gates/P0.md`: software PASS, adoption NOT_APPLICABLE; fence scoped by D032 (3 entries transfer to owning gates); metric report from 4430/136 tracked rows; no external blockers (P0-08 DONE, P0-09 DONE) |
| P1-01 | P1 | Freeze A hypothesis, endpoints, margins and pairing | P0-10 | IN_PROGRESS | Started 2026-09-19: v1.1 amendment (7 batched items) + A margins + criterion-2′ run; closes P0-06 |
| P1-02 | P1 | Implement inner-validation rank selector as independent A switch | P1-01 | TODO | Selection tests; no outer-data access; unchanged candidate fits — **not yet available** |
| P1-03 | P1 | Run A target/safeguard and regression comparisons | P1-02 | TODO | 000 vs 100; weak/null regimes; prediction/recovery/cost evidence — **not yet available** |
| P1-04 | P1 | Close A software and scientific adoption decisions | P1-03 | TODO | P1 gate: KEEP/CONDITIONAL/DROP/INCONCLUSIVE plus evidence tier — **not yet available** |
| P2-01 | P2 | Freeze B contract and matched-budget sampling policy | P1-04 | TODO | contracts/B.md; equal versus proportional budgets; full-data anchor — **not yet available** |
| P2-02 | P2 | Implement B with common preprocessing and frozen discovery sets | P2-01 | TODO | Independent B switch; saved discovery IDs and shared preprocessor hashes — **not yet available** |
| P2-03 | P2 | Test budgets, refit isolation and context-preservation safeguards | P2-02 | TODO | No test refits; no full-pool V updates; deterministic sampling tests — **not yet available** |
| P2-04 | P2 | Run balanced/imbalanced/subgroup B comparisons | P2-03 | TODO | 000/010 and 100/110; fixed and selected rank; all prior regressions — **not yet available** |
| P2-05 | P2 | Close B software and scientific adoption decisions | P2-04 | TODO | P2 gate and conditional activation rule if warranted — **not yet available** |
| P3-01 | P3 | Freeze C contract and identical-factor-bank comparisons | P2-05 | TODO | contracts/C.md; factor-bank reuse hashes; one-pass C definition — **not yet available** |
| P3-02 | P3 | Implement one-per-run-per-cluster aggregation only | P3-01 | TODO | C switch; provenance of retained/omitted factors; unchanged surrounding steps — **not yet available** |
| P3-03 | P3 | Test C constraint, no-op, invariance and incomplete-run handling | P3-02 | TODO | Property tests; identical output when constraint already holds — **not yet available** |
| P3-04 | P3 | Run corruption and natural end-to-end C comparisons | P3-03 | TODO | Paired C off/on evidence for all AB backgrounds; target/safeguard results — **not yet available** |
| P3-05 | P3 | Close C software and scientific adoption decisions | P3-04 | TODO | P3 gate with negative evidence, cost and adoption scope — **not yet available** |
| M1-01 | Milestone | Run full factorial plus anchors and interaction report | P3-05 | TODO | 8 configurations; fixed-rank controls; paired effects; failures retained — **not yet available** |
| M1-02 | Milestone | Freeze recommended configuration and run independent confirmation | M1-01 | TODO | Frozen hashes and untouched evidence; explicit limits if blocked — **not yet available** |
| M1-03 | Milestone | Verify installation, compatibility, restart and documented commands | M1-01 | TODO | Tested user workflow; final regression results; HPC status — **not yet available** |
| M1-04 | Milestone | Publish local evidence report and resumable handoff | M1-02, M1-03 | TODO | Approved artifacts with provenance; supported/unsupported claims; no remote publication — **not yet available** |

\* P0-10 can document an explicit synthetic-only engineering gate if P0-08 or P0-09 is externally blocked; those tasks stay BLOCKED, do not become DONE, and biological/comparator claims remain unavailable.

## 5. Ablation execution ledger

These are planned configurations, not executed experiments. Keep matched-budget `000` distinct from unchanged full-data cNMF.

| ID | A | B | C | Fixed-rank status | Selected-rank status | Evidence link |
|---|---|---|---|---|---|---|
| 000 | Off | Off | Off | NOT_RUN | NOT_RUN | — |
| 100 | On | Off | Off | Not applicable: A is a selector | NOT_RUN | — |
| 010 | Off | On | Off | NOT_RUN | NOT_RUN | — |
| 001 | Off | Off | On | NOT_RUN | NOT_RUN | — |
| 110 | On | On | Off | Not applicable: A is a selector | NOT_RUN | — |
| 101 | On | Off | On | Not applicable: A is a selector | NOT_RUN | — |
| 011 | Off | On | On | NOT_RUN | NOT_RUN | — |
| 111 | On | On | On | Not applicable: A is a selector | NOT_RUN | — |
| upstream_full_data | Off | Full eligible training pool | Upstream | NOT_RUN | NOT_RUN | — |
| genenmf_native | Separate whole workflow | Separate whole workflow | Separate whole workflow | As supported | As preregistered | — |

Attach paired-comparison results, not only configuration averages. Run the same synthetic realizations and donor splits; retain failed runs. Record separate sampling and optimization seeds.

## 6. Benchmark registry

| Scenario | Development status | Confirmation status | Purpose | Manifest/result |
|---|---|---|---|---|
| base_identifiable | NOT_CREATED | SEALED_SET_NOT_CREATED | Ground-truth recovery | — |
| A_weak | NOT_CREATED | SEALED_SET_NOT_CREATED | Weak activity/rank benefit | — |
| A_null | NOT_CREATED | SEALED_SET_NOT_CREATED | Excess-rank/false-program safeguard | — |
| B_imbalanced | NOT_CREATED | SEALED_SET_NOT_CREATED | Sample imbalance | — |
| B_balanced | NOT_CREATED | SEALED_SET_NOT_CREATED | Balancing no-harm control | — |
| B_context | NOT_CREATED | SEALED_SET_NOT_CREATED | Subgroup-program preservation | — |
| C_duplicate_merge | NOT_CREATED | SEALED_SET_NOT_CREATED | Consensus ambiguity | — |
| C_separated | NOT_CREATED | SEALED_SET_NOT_CREATED | Consensus no-harm control | — |
| public_multidonor | NOT_SELECTED | NOT_SELECTED | Biological generalization | — |

Independent confirmation has **not** been performed. Once outcomes inform redesign, mark the dataset/version as CONSUMED and move it into development history.

## 7. Mandatory invariants

- [ ] Full-data all-off behavior reproduces pinned upstream within declared tolerances.
  - **Not yet assessable — no experimental switches exist.** This invariant is about configuration `000` (A/B/C all disabled) matching an isolated upstream reference. P0-01 measured something different and weaker: upstream against its own downloaded 1.6.0 reference artifacts (`norm_counts` and `consensus_spectra` bitwise identical; worst relative Frobenius 1.4e-6, inside the declared 1e-5 of D004). That establishes the environment and the measuring apparatus, **not** this invariant. Re-assess once A/B/C exist.
- [ ] Training data alone determine features, scales, spectra and validation conventions.
- [ ] All observations from one donor stay in the same donor fold.
- [ ] Held-out-cell usages use inference observations only.
- [ ] Test row totals and test spectra refits cannot leak validation information.
- [ ] Observed zeros are included appropriately and are distinct from missing entries.
- [ ] B arms share preprocessing, rank grids, solver and total discovery-cell budget.
- [ ] Discovery samples do not change across K or optimizer seeds within one experiment.
- [ ] C arms share identical individual NMF outputs and surrounding refit logic.
- [ ] Missing/extra factors are penalized and usage matching follows loading matching.
- [ ] Confirmation gates refuse unset margins or unfrozen protocols.
- [ ] Failures and negative results remain visible in experiment/result registries.
- [ ] Cache/restart tests detect changed inputs, options, code and interrupted outputs.
- [ ] Smoke success cannot trigger a scientific adoption decision.

These invariant checkboxes do not add to the 31-task progress denominator.

## 8. Blockers and risks

| ID | Related task | Type | Description | Evidence / attempted command | Next action | State |
|---|---|---|---|---|---|---|
| B001 | P0-01 | Environment | ~~No runnable Python environment~~ | `module load tools/miniconda/python3.10/23.3.1`; `conda create --clone cnmf -n cnmf_bench`; `pip install -e . --no-deps`; `pip install pytest` | — | **CLOSED 2026-09-15.** Env `cnmf_bench` built and locked; see SOURCE_AUDIT §1.4 |
| B002 | P0-08, P0-09 | Access | Reachability of large downloads from this host | `curl -sI` → HTTP 200 for both pytest tarballs; `python3 download_pytest_data.py` → exit 0, 50 MB down / 99 MB extracted | — | **CLOSED 2026-09-15** for `storage.googleapis.com` and github.com. Still untested for the P0-08 public multi-donor dataset and the P0-09 GeneNMF repo — re-open per-source if one fails |
| B003 | P0-01 (residual) | Environment | `/home` is **96% full (482 MB free)**, so no Python environment or artifact can live there. Mitigated, not fixed: `~/.condarc` already redirects conda to `/exports/archive/hg-funcgenom-research/mdmanurung/conda/`. Flagged because an unrelated tool defaulting to `$HOME` will fail confusingly | `df -h ~` → `10G size, 9.6G used, 482M avail, 96%` | Keep all harness artifacts off `$HOME`; revisit if a tool ignores `.condarc` | OPEN (mitigated) |
| B004 | P0-01 / gate P0 | Upstream | Upstream's own test suite does **not** fully pass at the pinned SHA: `test_cnmf_end_to_end[dataset_config0]` fails on `gene_spectra_tpm`. Diagnosed (D005) as upstream's scale-blind absolute tolerance, not a regression and not our environment. Recorded so a future session does not misread it as new breakage | `pytest -vs tests` → 1 failed / 37 passed, 20.11 s; `registry/p0-01_pytest_run1.log` | None required — carry the expected failure into the P0 gate. Do not "fix" by regenerating references or loosening the threshold | OPEN (accepted, diagnosed) |

Track statistical problems separately from access, dependency, hardware, and implementation problems. Do not silently alter the scientific scope to bypass a blocker.

## 9. Session log — append after every session

### Session 2026-09-15 — S0 audit (Claude Code)

- Starting task and code revision: S0-01, at `5dbc5baaa0b9079b55bce554d801caa235a50457` (repo was already at this commit; clean tree)
- Files changed: created `docs/planning/SOURCE_AUDIT.md`; edited `docs/planning/DECISIONS.md` (added D001, D002); edited `docs/planning/PROGRESS.md` (this file)
- Commands actually executed and exit codes: `git status`, `git remote -v`, `git log --oneline -20`, `git branch -a` (0); `find`/`ls` orientation commands (0); `git ls-remote https://github.com/dylkot/cNMF HEAD` (0, returned `5dbc5baaa0b9079b55bce554d801caa235a50457`); `git rev-parse HEAD` (0, identical SHA); `which -a python python3` (0, only system python3 3.6.8); `conda env list` (127, `conda: command not found`); `command -v mamba micromamba` (no output); `module avail python` (0, listed 3.9-3.12 + miniconda modules); `cat Extras/Dockerfile` (0); `head -40 download_pytest_data.py` (read via Read tool)
- Tests passed / failed / not run: NOT_RUN — no Python environment exists yet to run `python -m pytest tests -q`
- Experiment IDs and artifact paths: none (S0 produces no experiment rows)
- Scientific findings, including negative results: none yet — S0 is audit-only, no benchmarks run
- Decisions or deviations recorded: D001 (keep `docs/planning`/`docs/benchmarks`, put new executable trees at repo root), D002 (local checkout HEAD is byte-identical to resolved `dylkot/cNMF` HEAD — no fork/upstream divergence exists)
- Status transitions made: S0-01 TODO→DONE, S0-02 TODO→DONE. P0-01 remains TODO (recon only; not formally opened since S0-03 is still TODO) — corrected mid-session after advisor review flagged an earlier BLOCKED mislabel (the env was never actually attempted, only surveyed)
- Blockers still open: B001 (Python env not yet built — a known next step with an identified `module load` path, not a hard blocker), B002 (external dataset/comparator reachability untested beyond GitHub)
- Next task: S0-03 — freeze scope and initialize `PROTOCOL.md` + `contracts/{A,B,C}.md` skeletons, using the dataflow findings in SOURCE_AUDIT.md §1.2 to fix the P0.4 transform contract before writing it down
- Exact next command, once verified: none yet — S0-03 is a writing task (PROTOCOL.md), not a shell command; the first *executable* command of the cycle will be the P0-01 environment build, e.g. `module load tools/miniconda/python3.12/24.9.2 && conda create -n cnmf_bench python=3.11 ...` (not yet run, exact recipe to be finalized in that session)
- Immutable artifacts not to overwrite: `docs/planning/SOURCE_AUDIT.md` §1 (upstream SHA resolution, dataflow trace) — append corrections, do not rewrite; `docs/planning/DECISIONS.md` D001/D002 — append-only per file convention

### Session 2026-09-15b — P0-01: environment and upstream reproduction (Claude Code)

- Starting task and code revision: P0-01, at `5dbc5baaa0b9079b55bce554d801caa235a50457` (tracked tree unmodified throughout; no `src/cnmf/**` changes)
- Files changed: created `docs/benchmarks/registry/` (6 files: 2 env locks, pytest data manifest, nondeterminism probe script + TSV, pytest log); edited `.gitignore`, `docs/planning/SOURCE_AUDIT.md` (§1.3 correction, §1.4 rewrite, new §1.5), `docs/planning/DECISIONS.md` (D003, D004, D005), `docs/planning/PROGRESS.md`
- Commands actually executed and exit codes: `module avail` (0); `module load tools/miniconda/python3.10/23.3.1` (0); `conda create --clone cnmf -n cnmf_bench -y` (0); `pip install -e . --no-deps` (0); `pip install pytest` (0); `conda list --explicit` / `pip freeze` (0); `curl -sI` on both tarball URLs (0, HTTP 200); `python3 download_pytest_data.py` (0); `pytest -vs tests` (**exit 1 — 1 failed, 37 passed, 20.11 s**); nondeterminism probe (0); several ad-hoc comparison scripts (0)
- Tests passed / failed / not run: 37 passed, 1 failed (`test_cnmf_end_to_end[dataset_config0]`, artifact `gene_spectra_tpm`). Failure diagnosed, accepted and recorded as D005 / B004 — **not** worked around
- Experiment IDs and artifact paths: no EXPERIMENTS.tsv rows yet (no benchmark experiments run — P0-01 is infrastructure). Evidence under `docs/benchmarks/registry/`
- Scientific findings, including negative results:
  1. **Risk 2 refuted.** The unseeded consensus refit produces **no** observable nondeterminism — all five artifacts bitwise identical across 10 repeats, seeded and unseeded. Cause: with `update_H=False` the refit is a convex NNLS problem with a unique optimum, so initialisation does not affect the converged result. Scope-limited to frobenius/cd, one dataset, one K (SOURCE_AUDIT §1.5.1)
  2. **Risk 1 characterised.** Upstream's suite fails at its own pinned SHA, but the environment is correct: solver input and consensus dictionary are bitwise identical to the reference, and all exact-equality artifacts match. The failure is upstream's absolute SSE budget meeting a TPM-scale matrix at 1.4e-6 relative agreement (SOURCE_AUDIT §1.5.2)
  3. The simulated/PBMC asymmetry (PBMC reproduces bitwise, including `gene_spectra_tpm`) points at the `.txt` input path rather than a generic scale effect. **Not traced to a specific line — open question, not a closed root cause**
  4. Upstream test coverage is far thinner than it looks: `factorize`, `combine`, `k_selection_plot`, `load_results` have **zero** coverage (SOURCE_AUDIT §1.5.3)
- Decisions or deviations recorded: D003 (dependency inversion, with guard clause), D004 (relative-Frobenius 1e-5 tolerance replaces upstream's absolute budget), D005 (upstream failure recorded as a finding, nothing modified upstream)
- Status transitions made: P0-01 TODO→DONE; B001 and B002 CLOSED; B003 and B004 opened
- Blockers still open: B003 (`/home` 96% full — mitigated by `.condarc` redirect), B004 (expected upstream test failure, diagnosed and accepted)
- Next task: **S0-03** — write and freeze `docs/planning/PROTOCOL.md`
- Exact next command, once verified: none — S0-03 is a writing task. To re-enter the environment: `module load tools/miniconda/python3.10/23.3.1 && source activate cnmf_bench` (run from repo root; export `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1` before any measurement)
- Immutable artifacts not to overwrite: everything under `docs/benchmarks/registry/` (baseline evidence — `p0-01_pytest_run1.log` and `nondeterminism_probe.tsv` are the P0 gate's reproducibility evidence); `tests/test_data/**` (downloaded 1.6.0 references — hashed in `pytest_data_manifest.tsv`; **never regenerate in place**, per D005)
- Post-session review corrections (advisor, same day, after the P0-01 commit):
  1. **Un-ticked the invariant** "Full-data all-off behavior reproduces pinned upstream within declared tolerances" in §8. It had been ticked with a caveat that contradicted the tick. The invariant concerns configuration `000` against an isolated upstream reference; no experimental switch exists yet, so it is *not yet assessable*. What P0-01 measured is upstream against its own 1.6.0 references — a weaker, different claim
  2. SOURCE_AUDIT §1.5.2: explained why `consensus_usages` (4.3e-07) is *cleaner* than `gene_spectra_tpm` (1.4e-06) which it is computed from — the refit is a convex NNLS with the dictionary held fixed, so it damps rather than amplifies the input perturbation. Argued, not separately verified; the verifying check is written down
  3. D004 marked **PROVISIONAL**: 1e-5 rests on a single observation and must be confirmed or revised at P0-04, where the absolute floor for near-zero artifacts must also be chosen — before the first such artifact appears, not after
  4. Noted in `nondeterminism_probe.py` that its hardcoded `REPO` path will break if the file moves at P0-07

### Session 2026-09-15c — S0-03: freeze the protocol (Claude Code)

- Starting task and code revision: S0-03, at `26eefac` (harness) / `5dbc5ba` (upstream). `src/cnmf/**` unmodified throughout
- Files changed: created `docs/planning/PROTOCOL.md` (**new**, 518 lines, frozen v1 — the "490 lines" written here originally was wrong and contradicted §4 of this same file; corrected in the P0-03 session, which also took the file to 523 lines at v1.0.1); edited `docs/benchmarks/configs/ablation_plan.yaml` (protocol block → `state: frozen` + sha256 + version + path), `docs/benchmarks/configs/smoke.yaml` (`cnmf_full_commit_sha` pinned; `genenmf_full_commit_sha` left null with a reason), `docs/planning/DECISIONS.md` (D006), `docs/README.md` (annotation), `docs/planning/PROGRESS.md`
- Commands actually executed and exit codes: `sed`/`grep` reads of `cnmf.py` to verify every line number before freezing it into the protocol (0); `sha256sum docs/planning/PROTOCOL.md` (0); a YAML parse + hash-match verification script (0, **MATCH**)
- Tests passed / failed / not run: no test suite run this session — S0-03 is a specification task. The verification performed was a hash/parse check, reported above
- Experiment IDs and artifact paths: none. `RESULTS.tsv` and `EXPERIMENTS.tsv` remain header-only
- Scientific findings, including negative results: none — this session produces rules, not measurements. Three design conclusions worth carrying forward:
  1. **The baseline selector must be largest-among-stable, not argmax.** On the common curve shape where silhouette sits near 1.0 and decays slowly, plain argmax returns the smallest grid value almost every time. A baseline that always picks K=2 would be beaten trivially by feature A and the `000` vs `100` comparison would measure nothing. Frozen in PROTOCOL.md §1.2 *before* any comparison exists, which is the only time this choice can be made honestly
  2. **The `delta` circularity is resolved without a fudge.** `delta` needs development controls; development controls need the simulator; the simulator comes after the freeze. Resolution: freeze the rule and the calibration procedure now, leave the value null, and make the selector *refuse to run* while it is null — the same pattern `ablation_plan.yaml` already applies to margins. Nothing before P1 needs it, because every A-OFF configuration is in `fixed_rank_configurations`
  3. **`s_g` uses `ddof=1`, and this is measured rather than assumed** (PROTOCOL.md §3.2). The harness's per-gene scale must *equal* what cNMF used internally, or the transform used for scoring would sit on a different scale than the one the dictionary was learned from. Dividing the HVG-subset raw counts by `std(axis=0, ddof=1)` reproduces the reference `norm_counts` to **1.7e-14** relative Frobenius; `ddof=0` gives **2.0e-4**, four orders outside D004's tolerance. Separately, the `cnmf.py:537` sparsity-branch hazard flagged in SOURCE_AUDIT §1.2 is **numerically benign for `s_g`**: `sc.pp.scale(zero_center=False)` (scanpy 1.11.5) agrees with manual `ddof=1` to 6.4e-16 on both dense and CSR input, so both branches divide by the same quantity. Caught by review — the `ddof=1` claim had originally been written from recall and would have been frozen unverified
  4. **`observation_model: poisson` in `smoke.yaml` is the simulator's generative model, not a deferred Poisson factorization backend.** Written into PROTOCOL.md §6.5 because a later session reading that key next to a brief that defers "NB/Poisson backends" would otherwise stall or implement a deferred feature
- Decisions or deviations recorded: D006 (P0-03 before P0-02, with a guard clause forbidding P0-02 from redefining PROTOCOL.md §6)
- Status transitions made: S0-03 TODO→DONE; P0-06 TODO→IN_PROGRESS; dashboard `Protocol version/hash` NOT_FROZEN→FROZEN v1
- Blockers still open: B003 (`/home` 96% full — mitigated), B004 (expected upstream test failure, diagnosed and accepted)
- Next task: **P0-03** — the simulator, built to spec against PROTOCOL.md §6
- Exact next command, once verified: none — P0-03 starts with writing a new module. Re-enter the environment first: `module load tools/miniconda/python3.10/23.3.1 && source activate cnmf_bench` (from repo root; export `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1` before any measurement)
- Immutable artifacts not to overwrite: **`docs/planning/PROTOCOL.md` is frozen** — editing it invalidates the sha256 in `ablation_plan.yaml` and creates a new protocol version under §9, which requires a DECISIONS.md entry in the same commit. Also everything under `docs/benchmarks/registry/` and `tests/test_data/**`, as before

### Session 2026-09-16 — code review of the only implemented script (Claude Code)

- Starting task and code revision: review, at `f3cf941`. No task status changed. `src/cnmf/**` unmodified
- Scope: the harness contains exactly **one** executable file — `docs/benchmarks/registry/nondeterminism_probe.py` (159 lines). Everything else committed so far is documentation, configs or evidence. That file is load-bearing: its null result is what "Risk 2 refuted" in SOURCE_AUDIT §1.5.1 rests on
- Files changed: added `docs/benchmarks/registry/nondeterminism_positive_control.py` + `.log` (**new evidence**); annotated `nondeterminism_probe.py` (docstring only — **behaviour deliberately unchanged**, because the recorded TSV was produced by it); corrected SOURCE_AUDIT §1.5.1
- Commands actually executed and exit codes: coverage check of the recorded TSV (0 — 90 rows = 2 conditions × 9 comparisons × 5 artifacts, so no artifact was silently skipped in the recorded run); positive control v1 (**exit 1 — defective control, see below**); positive control v2 (0)
- Tests passed / failed / not run: positive control **PASSED** — see the log in the registry
- Scientific findings, including negative results:
  1. **The probe's null result is validated.** It previously rested on an instrument never shown to be sensitive. The positive control nudges a single element of each saved artifact by a relative `1e-9` and confirms `compare()` detects it in **all five** artifacts (4.9e-11 to 3.3e-10 relative). The original conclusion stands
  2. **Scope correction, and it narrows the claim.** Perturbing the refit non-uniformly moves the four refit-derived artifacts but leaves `consensus_spectra` at exactly 0.0 — it is computed *upstream* of the refit (`cnmf.py:913-916`). So Risk 2 is refuted on **four** artifacts, not five; `consensus_spectra`'s stability is evidence about the seeded KMeans instead. SOURCE_AUDIT §1.5.1 corrected
  3. **A defective control was caught before it became a finding.** The first attempt perturbed the refit by a *uniform scalar*, which cancels exactly under the row normalisation those artifacts undergo, and appeared to show four artifacts "blind". That was a bad control, not a bad probe. Recorded in SOURCE_AUDIT so the mistake is not repeated — a negative result from a control has to be diagnosed before it is believed, exactly like any other
  4. **The frozen protocol survives unchanged.** PROTOCOL.md §3.3 cites the *convexity* of the fixed-dictionary NNLS, not the five-artifact count, so no amendment under §9 is triggered. Checked rather than assumed
- Defects recorded but deliberately **not** fixed in place (annotated in the probe's docstring, to be fixed in any successor): silent skipping of missing artifacts combined with an always-zero exit code, so a partially failed run looks clean; no built-in positive control; `bitwise_identical` is exact float64 equality, not file-byte identity; single-process scope. An independent reviewer agent reached the same first three findings
- Decisions or deviations recorded: none — no decision was required. The probe was annotated rather than edited because it is cited evidence; changing its behaviour while leaving the old TSV attributed to it would break the evidence chain
- Status transitions made: none
- Blockers still open: B003, B004 (both unchanged)
- Next task: **P0-03**, unchanged

### Session 2026-09-16b — P0-03: the simulator, and the first executable harness code (Claude Code)

- Starting task and code revision: P0-03, at `a7baf73` (harness) / `5dbc5ba` (upstream). `src/cnmf/**` unmodified throughout and re-verified byte-identical after the commit
- Context: the programme was five sessions in with ~2700 lines of documentation and **zero harness code**. P0-03 had been "next" in three consecutive sessions. This session wrote code
- Files created: `cnmfbench/` — `simulate.py`, `scenarios.py`, `contract.py`, `hashing.py`, `io.py`, `diagnostics.py`, plus `tests/` (5 files). Harness tests live in `cnmfbench/tests/`, **never** in `tests/`, because upstream's suite result (37 passed / 1 failed) is recorded P0-01 evidence and adding files there would destroy its value as a regression reference
- Files edited: `PROTOCOL.md` (§1.1, v1 → v1.0.1), `ablation_plan.yaml` (version + hash), `smoke.yaml` (two config corrections), `DECISIONS.md` (D007), `SOURCE_AUDIT.md` (new §1.6), `.gitignore`
- Commands actually executed and exit codes: `python -m pytest cnmfbench` (0 — **80 passed**); generation of all three implemented scenarios at SMOKE and DEVELOPMENT (0); `sha256sum docs/planning/PROTOCOL.md` (0); `git diff 5dbc5ba..HEAD -- src/ tests/ setup.py pyproject.toml` (empty, confirming upstream untouched); donor-eligibility sweep, 4 configs × 10 repeats (0)
- Tests passed / failed / not run: **80 passed, 0 failed.** Includes live integration against the pinned cNMF (`prepare` → `factorize` → `combine` → `consensus`), not mocks — the claims being tested are about upstream's behaviour, and a mock would only test my reading of it
- Experiment IDs and artifact paths: `docs/benchmarks/registry/p0-03_donor_eligibility_sweep.tsv`. **No `RESULTS.tsv` row was written** — that is the skeleton session that follows. `RESULTS.tsv` and `EXPERIMENTS.tsv` remain header-only

#### Three previously specified items that had been silently dropped, now done

All three were in the approved plan, approved, and then not carried out, with nothing catching it. Recorded rather than fixed quietly, because the process gap is the more durable finding: nothing cross-checks plan items against tracker state.

1. `PROTOCOL.md` §1.1 listed 3 of `k_selection_stats`' 4 columns. Corrected, bumped to **v1.0.1**, hash updated in `ablation_plan.yaml`, `DECISIONS.md` D007 records that **no rule changed**, so §9's confirmation-invalidation clause is not triggered
2. `smoke.yaml` `inference_gene_fraction` 0.7 → **0.5**
3. This session log, and the stale `Last update by implementing agent` field

Also corrected: PROGRESS.md gave PROTOCOL.md as both 518 and 490 lines in the same document. 518 was right.

#### Scientific findings, including negative results

1. **A fifth cNMF API trap, not found by source reading, and it had invalidated `smoke.yaml`.** `consensus` computes `n_neighbors = int(local_neighborhood_size * merged_spectra.shape[0] / k)`; since `merged_spectra` has `n_iter * k` rows this reduces to `int(0.30 * n_iter)`, **independent of k**. At `n_iter <= 3` it is zero, `local_density` divides by zero, and consensus raises `"Zero components remain after density filtering. Consider increasing density threshold"` — a message that points at the threshold, which is not the cause and cannot fix it. `smoke.yaml` had `optimizer_starts: 3`, so **every consensus call in the smoke tier would have failed**. Changed to 5. Verified for `n_iter` in {2,3,4,5,10,20} at `k` in {3,7,12}; regression test added
2. **The reused-run-name trap is the opposite of what was recorded.** Recorded as "silently skips factorization". Measured: the `completed=True` marking and its `UserWarning` happen inside `get_nmf_iter_params`, which `prepare()` calls, so the warning fires at **prepare** time; and `factorize` defaults to `skip_completed_runs=False`, so it **re-runs** every replicate. Silent skipping needs `skip_completed_runs=True`. The live hazard with default arguments is silent **overwriting**. A fresh name per run is still required, for the other reason
3. **Scaled-space cosine confirms the background-amplification prediction quantitatively.** True-program separation is 0.68 median / 0.80 max in the space the engine sees, against **0.54** in count space — the division by per-gene std acts as a per-gene mean normalisation, cancelling the shared background and amplifying it relative to the discriminative direction. Under the 0.7 target, so feature A is not excluded on identifiability grounds. This is why `lambda` must be tuned against measured scaled-space cosine and never a count-space formula
4. **`donor_id` survives `.h5ad` through a real `prepare()`** into `norm_counts.h5ad`, and does **not** reach the consensus artifacts, which carry only `obs.index`. Both halves now pinned by tests, so a downstream join on the cell index is a lookup rather than a guess
5. **AnnData coerces an integer index to strings**, closing one route to the §6.1 identifier clause. The real hazard is unaffected and is not about dtype: cNMF's `.npz`/tab-delimited readers discard `obs` columns entirely, which the donor-column clause catches

#### The donor-blocking measurement — settled, and it restates feature A's premise

This is what decides whether feature A is testable at all. It took **three** designs to
measure, and the answer is a negative finding on the mechanism with a positive finding on
the operational quantity.

**Result** (DEVELOPMENT tier, `base_identifiable`, n=12 repeats, evidence at
`registry/p0-03_donor_eligibility_sweep.tsv`):

| contrast | config A | config C | reading |
|---|---|---|---|
| `donor_count_at_fixed_leakage` | t = **+3.75** | t = **+4.30** | real, clears t > 3 in both |
| `leakage_at_fixed_donors` | t = −2.90 | t = −0.37 | **null** |
| `combined` (blocked vs leaky_wide) | t = 1.18 | t = **2.84**, +6.0% | **confirmed at n=48**, see below |

**n=48 confirmation of the composite** — the headline contrast, donor-blocked CV against
random-cell CV on the same dataset:

| config | gap | t (n=48) | |
|---|---|---|---|
| `A_current` — the a priori development default | +1.07% | 1.97 | **does not clear** |
| `C_rarer` | +2.92% | 3.11 | clears |
| `D_rarest` | +3.62% | 4.03 | clears |

**The a priori development default failed.** The development tier was therefore
recalibrated to `C_rarer`'s eligibility — which PROTOCOL §6.4 permits for this tier and
only this tier — under **DECISIONS D008**. The sealed tier keeps the a priori values and
is deliberately **not** retuned: a sealed set carrying a development-calibrated constant
would be a second development set wearing a confirmation label. The cost is accepted —
sealed confirmation runs on the lower-signal parameterisation, so a confirmation there is
conservative rather than flattering.

**No coverage effect is claimed.** Between configs, `D vs A` is t = 2.41, `C vs A` t =
1.69, `D vs C` t = 0.53. Each config is a single dataset realisation, so a between-config
difference confounds coverage with the dataset draw; that would need several
`simulation_replicate` values per config and was not done. The claim is narrower and
sufficient: C clears `t > 3` on its own paired within-config contrast and A does not.

**Correction to a reading made earlier in this session.** Going from n=10 to n=48 reversed
C and D (3.85% → 2.92%, 2.43% → 3.62%), and C and D are indeed indistinguishable (t =
0.53). I recorded this at the time as showing the whole ordering was noise. That is too
strong — A separates from D at t = 2.41. The fine-grained 4-way ranking was noise; whether
coverage matters at all is simply unresolved.

1. **The composite effect is real**: donor-blocked CV gives measurably higher held-out
   error than random-cell CV on the same dataset (+6.0% at config C). This is the
   operationally correct contrast, because the two CV schemes genuinely differ in how many
   donors reach the training set (12 vs 24 here)
2. **Per-donor identity leakage is not the mechanism.** Leakage at fixed donor count is
   null. This follows from the frozen PROTOCOL §6.3 contract rather than from a bad
   parameter choice: with a single global `K_true × n_genes` truth matrix, donor structure
   is purely compositional, and a held-out cell's NNLS projection against a frozen
   dictionary cannot depend on which donor produced it — there is no per-donor
   idiosyncrasy available to leak. **Sweeping `q_k` could never have fixed this**, which is
   why the sweep plateaued at t ≈ 1.4–1.8 instead of rising
3. **The channel is donor count and/or per-donor depth, and the two are not separable at
   this tier.** All arms draw the same number of cells, so more donors necessarily means
   fewer cells each (~75 vs ~150). Distinguishing them needs a fourth arm with 24 donors
   at ~75 cells and no test donors, which requires more than 24 donors in total — more
   than the DEVELOPMENT tier has. Recorded as a limitation, not resolved
4. **Feature A's premise is restated, not invalidated:** *donor-blocked CV measures
   generalisation to unseen donors, which random-cell CV overestimates.* Not "it prevents
   per-donor leakage", and not a claim about which channel produces the difference

##### How the measurement was wrong twice before it was right

Recorded because a diagnostic that has been wrong twice should carry its own history, and
because both errors produced confident numbers rather than obvious failures.

- A first two-arm design compared a donor-blocked split against a random-cell split, each scored on **its own** held-out cells. That measures test-set difficulty, not donor blocking, and returned a **negative** gap. Corrected by holding the test cells fixed across arms
- The corrected two-arm design gives a positive gap across four eligibility settings (+1.7% to +3.9%), ordered A < B < C with D out of order. That ordering looked like a dose-response in `q_k` and was briefly read as one. It is not: **`paired_se` overlaps every config's point estimate**, so the four cannot be ranked, and no configuration reaches `t > 3`. The plateau is now explained — the sub-cone mechanism the sweep was probing is not the channel that moves, so no `q_k` value could have made it significant
- **A confound was then found in that design too, and it is the important one.** The blocked arm trains on ~12 donors fully sampled; the leaky arm on ~24 donors half sampled. Sizes matched, donor counts did not — so the measured gap is "12 donors vs 24 donors" as much as "blocked vs leaky", and only the second is the quantity feature A is about
- `diagnostics.donor_blocking_gap` was rebuilt as a **three-arm decomposition** in which all arms draw the same number of cells: `blocked` (12 donors, no test donors), `leaky_matched` (12 donors, 6 of them test donors), `leaky_wide` (24 donors, all test donors). `blocked − leaky_matched` isolates **leakage at fixed donor count**; `leaky_matched − leaky_wide` isolates **donor count at fixed leakage**. That decomposition produced the table above

##### A process finding worth more than it looks

The a priori development default was only tested because its 48-repeat job finished
**after** the other two, and after the conclusion had already been written and committed.
Had the session stopped when configs C and D confirmed, it would have shipped a
development tier incapable of resolving the effect feature A exists to produce, under a
commit message stating the bar was cleared. The ordering of a background job, not the
design of the experiment, is what caught it. Worth guarding against directly: a
configuration that is *the default* should be measured first, not alongside the
alternatives.

#### Decisions and deviations recorded

- **D007** — PROTOCOL.md §1.1 corrected to v1.0.1, typed *descriptive correction, no rule changed*
- No other decision was required. `src/cnmf/**` unchanged; A, B and C remain harness-side switches

#### Status transitions made

- **P0-03: TODO → IN_PROGRESS.** Not DONE: the simulator is written and tested, but its central claim — that donor structure is detectable — is unestablished, and P0-03's purpose is to provide a ground truth the rest of the programme can be scored against

#### Blockers still open

B003, B004 unchanged. No new blocker. Two things to carry forward instead:

- **Donor count and per-donor depth are not separable at the 24-donor DEVELOPMENT tier.** If that separation matters for interpreting feature A's result, the tier needs more donors — a P1 decision with a compute cost, not something to resolve by reanalysis
- ~~**Feature A's hypothesis text must be restated before P1**~~ → **DONE**, `docs/planning/contracts/A.md`. States "measures generalisation to unseen donors, which random-cell CV overestimates" and records the three-arm measurement (leakage at fixed donor count t = −0.37; donor count t = +4.30) so the discarded framing cannot return. Adds the concrete mechanism found in the DEVELOPMENT run: one identity program with a **single** training carrier donor in `outer_0`, which no random-cell split can ever place out of sample. Endpoints exist; every margin remains NOT_SET

#### Next task

The **skeleton**: thin splitter + NNLS scorer + runner, producing the first `RESULTS.tsv` rows at `evidence_tier: SMOKE` with `selected_rank` null per §5.3.

**Read `diagnostics._score_split` first — and do not let it become the real thing.** It
already contains a working splitter and NNLS scorer in throwaway form (training-fitted
per-gene std, frozen dictionary, inference/validation gene panels, `equal_donor_mean`), so
it is the obvious reference. It is also exactly the hazard D006 named: thin components that
become load-bearing and are never hardened. It has no fold bookkeeping, no provenance, no
contract checks, and no `RESULTS.tsv` schema, and it must not acquire them in place.

### Session 2026-09-17 — the walking skeleton: the first benchmark rows (Claude Code)

- Starting task and code revision: the skeleton, at `cdf946a` (harness) / `5dbc5ba` (upstream). `src/cnmf/**` unmodified throughout and re-verified byte-identical after the commit
- **`RESULTS.tsv` and `EXPERIMENTS.tsv` are no longer header-only.** 114 and 6 rows, configuration `000`, SMOKE tier
- Files created: `cnmfbench/{provisional,splits,scoring,records,skeleton}.py` and two test modules; `docs/benchmarks/registry/p0-03_feasibility_checks.tsv`
- Files edited: `smoke.yaml` (three missing keys), `DECISIONS.md` (D009, D010, D011), `PROGRESS.md`
- Commands actually executed and exit codes: `python -m pytest cnmfbench -q` (0 — **122 passed**, was 80); `python -m cnmfbench.skeleton --run-id p0skel-000-20260917` (0); `python -m cnmfbench.skeleton --merge …` (0, 114 + 6 rows); a second merge (**exit 1, correctly refused** — duplicate `experiment_id`); `git diff 5dbc5ba..HEAD -- src/ tests/ setup.py pyproject.toml` (empty)
- Experiment IDs and artifact paths: 6 experiments, `000-full_training_pool-base_identifiable_SMOKE_r0-outer_{0,1}-k{2,3,4}-…`; run artifacts under `results/exploratory/p0skel-000-20260917/` (gitignored; `registry/p0-03_feasibility_checks.tsv` is the tracked record)

#### What the loop does

`simulate` → donor split → **training-only `.h5ad`** → real cNMF `prepare/factorize/combine/consensus` → frozen-dictionary NNLS on the inference panel → score the disjoint validation panel → `equal_donor_mean`. Held-out cells never enter cNMF, which is how §3.3's `test_spectra_refit: forbidden` holds by construction rather than by enforcement.

#### Scientific findings, including negative results

1. **The transform matches cNMF exactly — relative Frobenius `0.000e+00` in both folds.** This was the check that decided whether any of these numbers mean anything: had the harness's `s_g` differed from cNMF's, every prediction error would be wrong by a per-gene factor and nothing would have crashed. The assertion lives in the run path, not the tests, because it guards a *branch condition on an input property* (`cnmf.py:537` branches on sparsity) and a future switch to sparse output would silently take the other branch
2. **Silhouette dynamic range 0.115 / 0.035 — the degenerate branch does NOT fire.** Four orders of magnitude above §1.4's `1e-6`, so the baseline will not collapse to "always the smallest K" and the eventual `000` vs `100` is not measuring nothing. This was the precondition for `delta` meaning anything. Noted for P1: the curve is **monotone decreasing** in K, exactly the shape §1.2 warns about and the reason the baseline is largest-among-stable rather than argmax
3. **HVG retention 0.77–0.85 per program — passes in both directions.** Not near 0 (a program's signal filtered out before scoring, which would make the benchmark report "no difference" because the signal was gone) and not 1.0 (Fano selection acting as a perfect oracle for the planted markers)
4. **The Poisson error floor exposes a capability limit.** K=2 sits 18–22% above the arithmetic floor, so under-fitting is clearly detectable — but at `K_true` the observed error is only **~5%** above the floor, and the K=3→K=4 gap is 1.2% and 6.2%, comparable to that headroom. **At SMOKE scale this benchmark distinguishes an under-fitted rank well and has little room to distinguish `K_true` from `K_true + 1`.** Must be re-measured at DEVELOPMENT scale, where the overfit penalty weakens ~11× going from 180 to 2000 genes
5. **§4.3's exclusion path never fired** (0 cells, both folds; minimum inference-panel total is 137 counts). The graceful-degradation code is therefore not exercised by the smoke run and a bug in it would be invisible — covered by a synthetic test instead

#### Corrections adopted before implementation, from adversarial review

Several were measured against the real data and changed decisions rather than wording:

- **`arm` is `full_training_pool`, not `matched_budget`** (D010). The skeleton uses every training-donor cell with no budget, which is `upstream_full_data`'s definition applied to a training fold. Mislabelling it would have created a silent, uncorrectable confound in the B comparison two stages later — at the cost that these rows now require a budgeted `000` re-run before any `010` comparison
- **Nothing records which K won.** K=3 is the argmin in 10/10 measured cases, making it the most tempting number here; any column naming it would be the baseline selector running while `delta` is null
- **The null predictor takes the mean of the *scaled* matrix.** Using raw counts inflates the floor ~4× silently
- **`scipy.optimize.nnls`, not cNMF's `tol=1e-4` coordinate descent** — §3.3 defines an argmin and states the problem is convex, and exactness makes the leakage test bitwise
- **Per-donor rows, not aggregates only.** Per-donor error ranges 99–250 within a fold and tracks depth
- **My earlier carrier-probability estimate was superseded by measurement.** Program 2 has 3 carriers of 8 donors at seed 1701, so the folds train on 1 and 2 — the asymmetry is *already present*, not a 12% risk. The split was **not** rerolled to balance it: that would use ground truth to choose a split, which §6.3 forbids

#### Decisions recorded

**D009** (schema vocabularies invented in the harness, not by editing the frozen protocol — six columns had none, and `stratum`/`evaluation_scope` had no mention in any document), **D010** (`arm`), **D011** (the fence is code: a registry the P0 gate reads, with two deliberately separate checks so historical provisional rows cannot jam it forever).

#### Status transitions made

- **P0-03: IN_PROGRESS → DONE.** Acceptance evidence complete: saved truth, independent realizations, sealed-manifest policy, and all three feasibility checks run
- P0 gate: software status **PASS (smoke only)**, evidence tier **SMOKE**, scientific adoption **NOT_APPLICABLE**. The gate cannot close while components remain fenced — **four** as of D021 (§"Four components are fenced" below is authoritative; this line described six components at P0-04 and is left as a historical status note, not updated to track the current count)

#### Blockers still open

B003, B004 unchanged. Carried forward: `delta`, the precision/recall threshold and the `ambiguous` threshold stay null, to be batched into one v1.1 amendment. Feature A's hypothesis restatement is **closed** (`FEATURE_CONTRACT_A.md`).

#### Next task

**P0-04** — the four headline metrics and the corruption/invariance battery. `program_recovery_cosine_v1` needs the one-to-one matcher that `consensus_spectra`'s usage-ordered renaming makes necessary, and a matched null reported beside it or its ~0.9 floor makes the number uninterpretable.

## 10. Resume instruction

Read `AGENTS.md`, `IMPLEMENTATION_PROMPT.md`, and this tracker; inspect the existing worktree; start the next dependency-ready task without implementing deferred features. Update this file and the experiment/decision ledgers with actual evidence before ending the session. If a command cannot run, record why and keep its status NOT_RUN or BLOCKED.

### The protocol is frozen — read this before touching anything

`docs/planning/PROTOCOL.md` is **frozen at v1.0.1**, sha256 `715639895663bc74e7b864bc1cfae60c2fcd05b013e25f23016d45e86f4f9ca5`, recorded in `ablation_plan.yaml`. Verify with `sha256sum docs/planning/PROTOCOL.md` before relying on it.

Editing it is not a normal edit. Any change to a frozen rule creates a **new protocol version**, requires updating the hash in `ablation_plan.yaml` in the same commit, requires a `DECISIONS.md` entry, and invalidates any confirmation obtained under the previous version (PROTOCOL.md §9). Changes justified by outer-test or confirmation results are **forbidden**, not merely discouraged.

Two constants are **null by design** and stay null until P1: `delta` (the baseline selector's stability tolerance, §2) and the precision/recall threshold (§5.2). Both make their consumer **refuse to run** rather than fall back to a default. Do not "fix" this by supplying a default — that would be choosing a constant after seeing the data. Their calibration procedure is already frozen in §2.

### P0-06 is implemented and calibrated but stays IN_PROGRESS — read this before touching `PROTOCOL.md` or `delta`

P0-05 is **DONE**. As of the 2026-09-19 session, **P0-06's code and calibration are also done**, but the task itself is not:

- `cnmfbench/selector.py` (`select_rank`) implements PROTOCOL §1/§1.4/§2's five-step order exactly, including the load-bearing check-order test (a flat curve still refuses while `delta` is null). 12 new tests; **241 tests pass, exit 0.**
- `delta` is **calibrated: 0.04812** — the maximum per-(outer fold, K) silhouette standard deviation across four optimizer seeds, measured on both `base_identifiable` and `A_weak` at DEVELOPMENT tier, per §2's exact procedure. Full curves, dispersion table and reasoning are in **D023/D026**. It selects `K*=7=K_true` on `base_identifiable` in both outer folds (confirming the pre-registered `[0.0011, 0.0714)` window) and `K*=6` (one below `K_true`) on `A_weak` in both folds — the predicted A-headroom, not a defect.
- Two adjacent defects fixed: the silhouette sweep's cost was landing on no tracked row (D024, fixed); `prediction_error` was computed but never recorded (fixed, now `prediction_error_by_k` in diagnostics). D020's `experiment_id`/`inner_split_id` collision is pre-emptively resolved (D025).

**What is deliberately NOT done, by explicit user direction:** `delta` is **not** written into `PROTOCOL.md`. `PROGRESS.md:458`'s "one of seven items batched into the single v1.1 amendment" rule stands — writing `delta` in alone would still be a protocol version bump, and the other six items are unresolved. `PROTOCOL.md` stays byte-identical at v1.0.1, hash `715639895663bc74e7b864bc1cfae60c2fcd05b013e25f23016d45e86f4f9ca5`, `delta: null`. **Do not fill in `delta` in any config or call `select_rank` in production** — it still raises correctly, and it should.

**So P0-06's ledger row stays IN_PROGRESS.** Closing it requires the v1.1 amendment (all seven items, a P1-01-scoped event per three independent sources — see the tension this creates with the task ledger's own dependency graph, noted in §1's dashboard and left unresolved here).

**Two traps that still apply, unchanged from before this session:**

- **`splits.outer_donor_folds` stays fenced** — D021's condition ("`delta` set **and** feature A runnable, exercised by a real run") is not met: `delta` is calibrated but not in the frozen protocol, and feature A still cannot run (`check_preconditions` still refuses it unconditionally).
- **D020's inner-budget-under-`matched_budget` sampling design (sub-problems 1-7) remains deferred**, unimplemented. Only sub-problem 8 (the id collision) is resolved (D025).

Exact next command: `python -m pytest cnmfbench -q` to confirm 241 pass and exit 0, then `sha256sum docs/planning/PROTOCOL.md` to confirm it still matches the hash above. The next dependency-ready **P0** task by the ledger's own graph is **P0-07** (workflow/CI/cache-restart); reaching the v1.1 amendment and feature A requires either P0-07 through P0-10 closing the P0 gate, or a future session explicitly deciding P1-01 can proceed earlier and recording why.

Then the P0 gate, then P1/A. The user's target is the first `000` vs `100` comparison. Plan: `/home/mdmanurung/.claude/plans/plan-the-next-steps-warm-tome.md`.

### Session 2026-09-17/18 — the feasibility gate, its NO-GO, and P0-04's metrics (Claude Code)

- Starting task and code revision: continue the approved plan, at `da5728c` (harness) / `5dbc5ba` (upstream). `src/cnmf/**` unmodified throughout and re-verified byte-identical after every commit (`git diff 5dbc5ba..HEAD --stat -- src/ tests/ setup.py pyproject.toml` empty)
- Environment: `module load tools/miniconda/python3.10/23.3.1 && source activate cnmf_bench`, with `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1` before every measurement

**Commands run, with outcomes:**

| command | outcome |
|---|---|
| `python -m cnmfbench.skeleton --config docs/benchmarks/configs/development.yaml --run-id p0-03-dev-feasibility` | exit 0, ~4m55s, 610 results / 16 experiments |
| `python -m cnmfbench.analysis results/exploratory/p0-03-dev-feasibility` | exit 0 — **verdict NO-GO** |
| `python -m cnmfbench.skeleton --config docs/benchmarks/configs/development_conv1000.yaml --run-id p0-03-dev-conv1000` | exit 0, ~9m00s — merge **refused** (id collision, D014) |
| `python -m cnmfbench.skeleton --config .../development_conv1000.yaml --run-id p0-03-dev-conv1000-v2` | exit 0, ~12m40s, merged cleanly with `variant: conv1000` |
| `python -m cnmfbench.skeleton --merge results/exploratory/{p0-03-dev-feasibility,p0-03-dev-conv1000-v2}` | exit 0 — tracked files now **1342 / 40** |
| `python -m pytest cnmfbench -q` | exit 0 — **178 passed** |

**The headline result: the DEVELOPMENT feasibility gate returned NO-GO, and the criterion that produced it is mis-specified.** This is the hardest thing in this session to reconstruct from the commit log, so it is stated in full:

- Criteria were pre-registered and committed at `f1e86fa` **before** the run. Git history is the evidence of that ordering.
- Criterion 1 passed decisively (paired t = 26.8 over 24 donors). Criterion 3 passed (silhouette ranges 0.282, 0.301). **Criterion 2 failed** in `outer_1`, and `outer_0` passed it only in the fifth decimal place. Under the pre-registered rule, NO-GO.
- **But the loss curve minimises at `K_true` = 7 in both folds**, descending from ratio 1.137/1.166 at K=4 and rising monotonically after 7; the silhouette holds ~0.996 through K=7 and drops sharply at K=8 in both folds. Two independent signals put the elbow at `K_true`.
- Criterion 2 inspects only `K_true` and `K_max` — **both on the overfit side of the minimum**, where the curve is flat by construction. Its stated rationale ("no signal left to select on") is falsified by the run's own data. It passed at SMOKE only because that grid's `K_max = 4` sat on the *underfit* side of a `K_true = 3` curve, so the same sentence tested a different quantity at the two tiers.
- **The verdict was not overridden.** A criterion rewritten by whoever just watched it fail is worth nothing however sound the argument. D012 records the defect as an argument; a replacement (criterion 2′, the `K_min → K_true` span, reusing the already-approved `3 × paired SE` constant) is pre-registered in `registry/p0-03_feasibility_criterion_v2_PREREGISTRATION.md` with its **seed committed in advance** (`seed: 31337`, `panel_seed: 20260919`) and must be judged on a fresh run it did not motivate. It is also stated in advance that it is expected to pass and therefore carries little discriminating power on this dataset.
- **The v1 remediation menu was itself under-specified** and this is the lesson for the v1.1 amendment: its four options all assume the *benchmark* failed. Options 1–3 strengthen a benchmark that already resolves rank; option 4 ("report that §6.3 cannot support predictive rank selection") would be a **false report** given this curve. There was no branch for *the instrument being wrong*.

**The convergence diagnostic answered the question it was aimed at.** The amendment permitting it was committed at `3ed5bae` while the first run was in flight; its target was narrowed at `ace91f7` **before** the diagnostic ran, to criterion **1** rather than 2 — better convergence lowers error and so can only firm up criterion 2's failure, whereas a K=10 fit under-converges harder than a K=7 fit and could have manufactured the 1.673 rise. Result: `ConvergenceWarning`s fell 73 → 22 at `max_iter=1000`, the loss curve moved by at most 5.1e-04 relative (several points bitwise identical), and the rise grew slightly to 1.680 at t = 25.7. **Under-convergence is ruled out; the NO-GO stands for scientific reasons.** Incidental: the silhouette dynamic range moved ~34% (0.282 → 0.198, 0.301 → 0.200) against a <0.001% move in the loss — PROTOCOL §1.4's baseline selector reads exactly that quantity, which matters before P0-06 sets `delta`.

**P0-04, mostly done.** `cnmfbench/recovery.py` and `cnmfbench/compare.py`, 29 + 9 tests:

- `program_recovery_cosine_v1` — Hungarian matching with dummy factors, dividing by `max(K_true, K_fitted)`. `Spectra` carries its unit system as data and `recovery_cosine` **raises** on a mismatch (D013), because the unaligned comparison is not merely wrong but *reversed*: the matched null beats the fit at every rank in both folds. The two alignment routes agree to 1e-12, so the choice is free and only failing to choose breaks it
- `usage_error_v1` — takes the `Alignment` as an argument and refuses one from a different fit; missing and extra programs retained as error
- Corruption battery complete: label permutation, gene reordering and factor rescaling **invariant to 1e-12**; duplication, deletion, usage shuffling and noise replacement penalised, with noise landing near the matched null rather than near zero
- `program_precision_v1`, `program_recall_v1` and the `ambiguous` count implemented **and refusing**; `top2_cosine_gaps` records the distribution a threshold would later be calibrated against
- **D004 discharged.** (i) 1e-5 **CONFIRMED**: float32 round-trip noise 2.5e-8 (400× below), one gene +50% 3.6e-3 (360× above), program swap 5.7e-1. (ii) Near-zero floor **1e-12**, set while no near-zero artifact exists — the only condition under which choosing it is honest

**Two defects found by checks written earlier, which is the argument D011 made:**

1. `merge_into_tracked` refused the diagnostic's rows: `make_experiment_id` had no way to express "same dataset and seeds, different factorization parameter", so both runs produced identical ids. Fixed with an optional `variant` folded into the digest **only when set**, leaving all existing ids bit-identical (D014). Adding the hyperparameters to the digest would have been correct in principle and forced a three-run replay to repair an identifier
2. `test_shared_fit_cost_is_attributed_exactly_once` collided twice as the tracked file grew — first on `outer_split_id` alone, then on `dataset_id` plus the configuration bits, because `variant` appears only inside `experiment_id`. Now keyed on the id's fold prefix

- Decisions recorded: **D012** (the NO-GO and the mis-specification), **D013** (unit-tagged spectra), **D014** (`variant`), and D004 moved PROVISIONAL → **CONFIRMED**
- `docs/planning/contracts/A.md` written, closing the obligation to restate feature A's hypothesis before P1: it now says *"measures generalisation to unseen donors, which random-cell CV overestimates"* and records the three-arm measurement that killed the leakage framing (leakage at fixed donor count t = −0.37; donor count t = +4.30). New supporting evidence from this session: in `outer_0` one identity program has a **single** training carrier donor, which no random-cell split can ever place out of sample. Every margin remains `NOT_SET`
- Next task: **finish P0-04** — wire `program_recovery_cosine_v1` and `usage_error_v1` into the runner so they write rows. Then P0-05
- Exact next command: `python -m pytest cnmfbench -q` to confirm 178 green, then edit `cnmfbench/skeleton.py`'s per-rank block to score recovery against `ds.true_spectra` restricted to the fold's `G`, aligned with `.to_scaled(s_g)`, with `matched_null_spectra` beside it


### Session 2026-09-19 — P0-06: the selector implemented, `delta` calibrated, PROTOCOL left untouched (Claude Code)

- Starting task and code revision: P0-06, continuing from `2b3b190` (harness) / `5dbc5ba` (upstream). `src/cnmf/**` unmodified throughout, re-verified byte-identical after every change (`git diff 5dbc5ba..HEAD --stat -- src/ tests/ setup.py pyproject.toml` empty)
- Environment: `module load tools/miniconda/python3.10/23.3.1 && source activate cnmf_bench`, `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`
- **User decision, obtained before implementation began**: calibrate and record `delta`'s value and evidence this session; do **not** amend `PROTOCOL.md` (the v1.1 amendment batches seven items and is described elsewhere as a P1-01 event — see D023). This shaped every choice below.

**Files created:** `cnmfbench/selector.py` (`select_rank`, `SelectionResult`); `cnmfbench/tests/test_selector.py` (12 tests); seven new config files under `docs/benchmarks/configs/` (`smoke_a_weak_check.yaml`; `development_000m_seed{90211,90212,90213}.yaml`; `development_a_weak_000m_seed{90210,90211,90212,90213}.yaml`).
**Files edited:** `cnmfbench/skeleton.py` (`_fold_diagnostics` now also captures `prediction_error_by_k`; the diagnostics sweep's wall/cpu time is folded into the fit-scope cost row); `cnmfbench/records.py` (`make_experiment_id` gains an optional `inner_split_id`, folded into the digest only when truthy, following the `variant` precedent exactly); `docs/planning/DECISIONS.md` (D023-D026); `docs/planning/PROGRESS.md` (this file).

**Commands run, with outcomes:**

| command | outcome |
|---|---|
| `python -m pytest cnmfbench -q` (repeated after each batch) | exit 0 throughout — 229 at session start, 241 at session end (12 new selector tests) |
| `python -m cnmfbench.skeleton --config .../smoke_a_weak_check.yaml --run-id p06_a_weak_smoke_check` | exit 0, 13s, 134 results, 8 experiments — first-ever run of `A_weak` at any tier. Directory deleted after inspecting `diagnostics.json` |
| `python -m cnmfbench.skeleton --config .../smoke_000m.yaml --run-id p06_cost_check` | exit 0; **0/134 non-cost values differing** from tracked `RESULTS.tsv`; cost rows moved as intended by the D024 fix (fit-scope `wall_seconds_v1` 0.615s→0.844s at `outer_0`). Directory deleted after comparison, not committed |
| Seven DEVELOPMENT runs: `base_identifiable` seeds `{90211,90212,90213}` (seed 90210 reused from existing `p04-dev-000m`) and `A_weak` seeds `{90210,90211,90212,90213}` | exit 0, ~5 min each, ~35 min total. Kept under `results/exploratory/p06-delta-*`, **not** merged into tracked TSVs — calibration inputs, not benchmark rows |
| `sha256sum docs/planning/PROTOCOL.md` (repeated) | unchanged throughout: `715639895663bc74e7b864bc1cfae60c2fcd05b013e25f23016d45e86f4f9ca5` |

**An operational near-miss, recorded because it could have corrupted evidence.** A background job chaining "wait for the base_identifiable batch, then run the A_weak batch" appeared to have failed to start (empty output, no process) and was restarted directly. Both the original and the restarted job were in fact alive concurrently for a period, both scheduled to write into the same `results/exploratory/p06-delta-aweak-seed*` run directories — a genuine race that could have produced a run directory with interleaved writes from two processes. Caught by `ps -ef` process-tree inspection before either wrote a colliding output file; the stale duplicate was killed (`TaskStop`). No run directory shows evidence of the collision (each has exactly one `diagnostics.json`/`experiments.tsv`, consistent with a single writer), but this is a process hazard worth naming for any future session that backgrounds several `skeleton.py` invocations against predictable run-ids: check `ps -ef` for a duplicate before trusting a "job didn't start" read.

**Scientific findings:**

1. **The A-OFF baseline selector's entire input was free on every tracked row.** `_fold_diagnostics`'s one-`consensus()`-per-rank silhouette sweep sat outside both cost-timing windows. Fixed (D024); existing tracked cost rows for fit-scope experiment_ids are now an undercount relative to this fix, not regenerated this session (flagged, not silently left).
2. **`delta = 0.04812`** (D026), the maximum per-(outer fold, K) silhouette sd across 4 optimizer seeds on `base_identifiable` and `A_weak` at DEVELOPMENT tier — chosen to be at least as large as every noise value actually measured, so the selector cannot mistake this session's own measured noise for signal anywhere. It selects `K*=7=K_true` on `base_identifiable` (both folds; confirms the pre-registered `[0.0011,0.0714)` window from the single-seed `p04-dev-000m` run) and `K*=6` on `A_weak` (both folds; one below `K_true`) — the predicted A-headroom, read only after `delta` was fixed and recorded, per §2's step ordering.
3. **The dispersion is not uniform across K**: both scenarios show a low-noise plateau at small K and a much noisier region above it, coinciding with where the curve descends fastest — the region a selector is most likely to get wrong is also the region measured least precisely by four seeds.

- Decisions recorded: **D023** (selector implemented, `delta` calibrated-not-amended, scope decision), **D024** (cost-attribution fix), **D025** (`inner_split_id`), **D026** (calibration evidence; fourth dependency-order deviation, following D018/D021)
- Status transitions made: P0-06 remains **IN_PROGRESS** (its row requires `delta` in the frozen protocol; only the calibration evidence and the code exist)
- Next task: by the ledger's dependency graph, **P0-07**. Reaching the v1.1 amendment (which sets `delta` in `PROTOCOL.md` and un-refuses feature A) requires either the P0 gate closing (P0-07 through P0-10) or a future session explicitly deciding P1-01 can proceed earlier and recording that decision — see the tension noted in §1's dashboard

### Session 2026-09-18b — P0-05: nested folds, the leakage audit, and un-fencing (Claude Code)

- Starting task and code revision: continue the approved plan (`plan-the-next-steps-warm-tome.md`) from `328238e` (harness) / `5dbc5ba` (upstream). `src/cnmf/**` unmodified throughout, re-verified byte-identical after every commit
- Environment: `module load tools/miniconda/python3.10/23.3.1 && source activate cnmf_bench`, `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`

**Commands run, with outcomes:**

| command | outcome |
|---|---|
| `python -m pytest cnmfbench -q` (repeated after each batch below) | exit 0 throughout — 225 passed at session start (`7312dd2`), 229 passed at session end |
| `python -m cnmfbench.skeleton --config docs/benchmarks/configs/smoke_000m.yaml --run-id refactor_check` | exit 0; all 102 non-cost tracked rows reproduced exactly after extracting `_consensus_dictionary` and wiring the inner loop |
| `python -m cnmfbench.skeleton --config docs/benchmarks/configs/smoke_000m.yaml --run-id panel_check` (with `panel_repetitions: 5`) | exit 0; same 102 rows reproduced exactly; `panel_variance_by_k` sd/mean 12.6-19.5% across `k=2,3,4`, both outer folds |
| `git diff 5dbc5ba..HEAD --stat -- src/ tests/ setup.py pyproject.toml` (repeated) | empty throughout |

Both verification runs' directories were deleted after comparison (`rm -rf results/exploratory/{refactor_check,panel_check}`), not committed.

**§6.2 of the approved plan was reversed before any code built on it (D019).** The plan said the inner validation loop runs unconditionally for every configuration. `PROTOCOL.md:48` (§1.1) shows the A-OFF baseline selector reads `silhouette`/`prediction_error` from the training fit's own `k_selection_stats`, never from an inner fold — so `_run_inner_fold` is called only when feature A is on. `check_preconditions` still refuses A while `delta` is null, so this has no effect on any tracked row yet; it is recorded so the `000`-vs-`100` comparison is not confounded the day A is switched on.

**Nested folds, real fits, both failure modes checked (`7312dd2`).** `splits.inner_donor_folds` (already implemented pre-session) plus a new `test_inner_folds.py`, 8 tests run against real `prepare/factorize/combine/consensus`: clobbering (an inner fit cannot overwrite its outer fold's `nmf_genes_list`), and leakage one level down (perturbing inner-validation donors leaves the inner `G`/`s_g`/dictionary bitwise unchanged, and the inner score DOES move). `_consensus_dictionary` extracted from `_run_fold` so the inner loop applies feature C identically to the outer loop.

**Panel repetitions and the cross-arm audit (D021, D022).** `skeleton.py` now draws `panel_repetitions` gene-panel realisations per fold, scores each independently (`_score_with_panel`), and asserts repetition 0 reproduces the emitted row's value exactly — a duplicate scoring path checked at run time rather than trusted. The variance is recorded as a diagnostic (`panel_variance_by_k`), never a metric, per §5.1/§5.2. `analysis.assert_panels_identical` closes the §4.1 audit the fence named and nothing implemented; verified against the tracked evidence (`test_panel_identity_holds_within_the_tracked_evidence_per_outer_fold`). The `splits.gene_panel` fence entry's unsourced claim ("measured to exceed the rank signal") is corrected — no artifact ever backed it — and replaced with the number this session actually measured (D022).

**Fence: six → four (D021).** `splits.gene_panel` and `scoring.nnls_usages` un-fenced, both `hardening_requires` met. `splits.outer_donor_folds` reassigned P0-05 → P0-06 rather than un-fenced with them: its nesting exists and is tested, but D019 means no production run calls it yet, and un-fencing it now would repeat D017's exact lesson.

**Inner-budget-under-`matched_budget` sampling deferred, fully specified (D020).** A design review (run against the user's already-chosen fix — scale the inner budget to the inner cell fraction) found the fix's execution has eight interacting sub-problems: arm-based branching (not B's bit), `s_g` computed on sampled rows (a latent bug the review caught before it could ship), a required inner `_panelref` for B, cells-not-donors scaling, per-fold seed derivation, two new `check_preconditions` checks, cost-window separation, and an `experiment_id` collision with no chosen resolution. Deferred to P0-06 rather than rushed, since feature A cannot run in production regardless — see D020 for the full specification.

**Record corrections.** `PROGRESS.md`'s fence table, resume block and progress counts updated to 7/31 DONE; a stale "five components" sentence from the P0-03 session (`:417`) corrected; a third dependency-order deviation (P0-05 DONE while P0-02 remains TODO) recorded per D018's established pattern, in D021.

- Decisions recorded: **D019** (inner loop conditional on A), **D020** (inner-budget design deferred to P0-06), **D021** (un-fencing + reassignment), **D022** (unsourced panel-variance claim corrected)
- Next task: **P0-06** — the selector and `delta`. See the resume block above for the mechanical procedure and the two known traps.


### Session 2026-09-18 — real data, then features B and C (Claude Code)

Two sessions' work, logged together because neither was logged at the time.

- Starting revision `b8ba39d` (harness) / `5dbc5ba` (upstream), ending `e03773e`. `src/cnmf/**` re-verified byte-identical after every commit.
- Environment as above, BLAS pinned to 1 thread for every measurement.

**Part 1 — P0-08 real data** (commits `7725827`, `d9c28da`, `3c10c12`, `069994c`, `707df29`, `28818f5`). Four datasets downloaded off `$HOME` per B003, to `/exports/para-lipg-hpc/mdmanurung/cnmf-realdata/raw/`, each sha256'd into `registry/p0-08_real_data_candidates.tsv`:

| dataset | shape | donors | verdict |
|---|---|---|---|
| Kang 2018 | 24,673 × 15,706 | 8 | **USABLE** — raw counts |
| Stephenson 2021 | 62,509 × 16,299 | — | **NOT USABLE** — `.X` log1p-normalised, no `layers`, no `.raw`; the pre-flagged trap fired |
| Heart Cell Atlas v2 | 704,296 × 32,732 | 22 | raw counts confirmed; **CC BY 4.0, the only license actually read** |
| AIDA Phase 1 v2 | 1,265,624 × 35,477 | **625** | raw counts in `.raw.X` — `.X` is normalised (max 6.5) vs `.raw.X` integer (max 198); the pre-flagged `.raw.X` gotcha fired exactly as predicted |

First cNMF run on real data (Kang, `28818f5`): AUC 0.914–0.948 at every rank, peak 0.9475 at k=10; 16/30 top genes canonical ISGs against a list fixed in advance. Recorded as **a diagnostic, not a benchmark row** — no `RESULTS.tsv`/`EXPERIMENTS.tsv` rows written, configuration 000, no comparator. The ledger row P0-08 was **not** advanced: license is an explicit acceptance requirement and is satisfied for exactly one of the four. AIDA work postponed at the user's direction.

**Part 2 — features B and C** (commits `2096ad0`, `b31ce50`, `328238e`, `ff9abd2`, `ef6f192`, `e03773e`).

| command | outcome |
|---|---|
| SMOKE factorial, `smoke_{000m,001,010,011}.yaml` | exit 0 — 1878 / 72 tracked |
| DEVELOPMENT factorial, `development_{000m,001,010,011}.yaml` | exit 0, ~3.7 min per configuration |
| regeneration of all 8 runs after the fit-row fix | exit 0, no errors |
| `python -m cnmfbench.skeleton --merge …` × 8 | exit 0 — tracked **4430 / 136** |
| `python -m pytest cnmfbench -q` | exit 0 — **199 passed** |

Findings, in order of how much they change what is believed:

1. **Feature C fires only above `K_true`.** Zero contributions dropped in all 8 cells at k ≤ 7; 1–13 dropped in all 12 cells at k = 8,9,10. Where it fires it is a small consistent degradation — worse recovery in **12/12** cells, worse predictive error in 10/12, magnitude ≤ 0.0008 recovery and 0.11% loss. The pre-registered prediction that SMOKE was *incapable* of testing C and DEVELOPMENT was the right tier held.
2. **A dose-response claim was written and then withdrawn.** Within a fold, drop count and rank rise together, so "scales with drops" and "scales with over-factorization" are collinear. At fixed k=10 the drop counts spread 3 to 13 and the effect does not follow — 13 drops gives +0.008 while 12 gives +1.013. Withdrawn in the registry with the reasoning kept beside it.
3. **D016 — `hold_preprocessing_constant_across_B` holds for `G` and cannot hold for `s_g`.** `cnmf.prepare` computes the scale from whichever cells the sampling rule drew, and `src/cnmf/**` may not be edited. Measured drift: median 1.043, max 1.238. **The sign of the B effect flipped in 4 of 6 SMOKE cells** between unit conventions, falsifying a claim already published in the registry. Cross-arm endpoints now read in count units, pre-registered in `contracts/B.md` before any DEVELOPMENT row was read.
4. **A registry file claimed "191 tests green" when the suite was 190 passed / 1 failed.** Corrected in place rather than dropped — `docs/AGENTS.md:36` forbids fabricating test outputs. The failing test was right: fit-scope rows carried a hardcoded `arm=full_training_pool` while their own `experiment_id` said `matched_budget`. Fixed, all 8 runs regenerated; all 12 C cells and all 96 SMOKE values reproduce exactly.
5. **`assert_poolable` could not deliver what its docstring promised.** It refused rows spanning "different gene panels and per-gene scales", but `preprocessing_hash` carries `s_g_ddof` and not `s_g`, so both B arms hashed identically. Now keyed on `(preprocessing_hash, discovery_cells_hash)` — no formula change, so the guard stays content-keyed rather than versioned across old and new rows.
6. **D017 — P0-04 could not be DONE while owning a fenced component.** `scoring.equal_donor_mean` had `owner_task="P0-04"` and `reason="No corruption or invariance tests."` while the ledger row claimed a full battery. Resolved by writing the aggregator's own battery (7 tests) rather than rewording the ledger, and un-fencing it with its decorator per D011's rule.

- Status transitions: **P0-04 IN_PROGRESS → DONE** (6/31). Fence 7 → 6. Decisions added: D015 (C's tie-break rule, previously referenced from two files and never written), D016, D017.
- Next action: **P0-05** — nested donor folds and the leakage suite.

### Four components are fenced as throwaway, and the P0 gate reads the fence

`cnmfbench/provisional.py` lists, with its owning ledger task and what hardening requires (D011):

| component | owner | what hardening requires, in brief |
|---|---|---|
| `splits.outer_donor_folds` | **P0-06** | `delta` set and feature A runnable, so the nested-fold path (already built and tested against real cNMF fits) is exercised by a production run rather than by tests alone |
| `skeleton.run` | P0-07 | workflow with restart and cache-invalidation tests |
| `features.consensus_c` | **P3-01** | OFF-path equivalence at every tier claimed, + the tie-break rule settled (D015) |
| `features.discovery_sample_b` | **P2-01** | sampling replicates so the draw's variance is reported (D016) |

Every row they produce carries `status: ok_provisional`.

`scoring.equal_donor_mean` was **un-fenced at D017** once its own corruption/invariance battery was written. `splits.gene_panel` and `scoring.nnls_usages` were **un-fenced at D021** (P0-05): panel repetitions with variance reported plus the cross-arm `assert_panels_identical` audit close the first; the §3.2 leakage suite (`test_leakage.py`) closes the second. `splits.outer_donor_folds` was reassigned from P0-05 to P0-06 at the same decision rather than un-fenced with them — see D021 for why. Earlier copies of this section naming five or six components, or listing `scoring.equal_donor_mean`, `splits.gene_panel` or `scoring.nnls_usages` as still fenced, are wrong. The code is authoritative.

**A structural problem, named not solved:** two of the four are owned by *post-P0* tasks, so "the P0 gate cannot close until the fence is empty" currently makes P0 depend on P2-01 and P3-01. Either the gate condition is scoped to P0-owned components, or the P0 gate genuinely cannot close before P3. This wants a decision before `gates/P0.md` is written.

`registry_is_empty()` is the gate check and is **false** today. Emptying it means deleting decorators and registry entries together, in a commit with a decision entry. Do not "tidy" the registry without doing the hardening it names.

**Read `diagnostics._score_split` as reference and do not extend it in place** — it is cited P0-03 evidence, its docstring records why that measurement was wrong twice, and a test asserts no module outside `diagnostics.py` references it.

### Standing notes

- `docs/planning/contracts/A.md` now **exists** — hypothesis restated against measurement, endpoints named, every margin still `NOT_SET`, so it cannot issue an adoption decision. `docs/planning/gates/` is created but empty; `gates/P0.md` is still due before the P0 gate closes.
- Background reading order for any scoring work: `SOURCE_AUDIT.md` §1.2 (three distinct spectra normalizations, two std pipelines), then §1.5 (measured determinism, declared tolerance), then D004 (**provisional** — the 1e-5 tolerance must be confirmed or revised at P0-04, where the absolute floor for near-zero artifacts must also be chosen) and D005.
- The transform question once flagged in §1.2 is **settled** and written into PROTOCOL.md §3.1: scoring uses the HVG-panel / `median_spectra` route, never all-gene / `spectra_tpm`, because TPM-normalising a held-out cell divides by its total across *all* genes including its validation panel.
- `src/cnmf/**` has not been modified and should not be. A, B and C arrive as harness-side switches.
