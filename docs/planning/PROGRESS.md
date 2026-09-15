# cNMF incremental development — progress tracker

**Specification prepared:** 15 September 2026  
**Target repository:** `dylkot/cNMF`  
**Current state:** IN_PROGRESS — S0-01/S0-02 and P0-01 closed; upstream reproduced within a declared tolerance; S0-03 (protocol freeze) is next  
**Important:** No target-package code has been modified and no scientific benchmarks have been run. S0-01/S0-02 produced an audit only.

## 1. Session dashboard

| Field | Current value |
|---|---|
| Active prototype | P0 — baseline reproduced; next is S0-03 (protocol freeze) |
| Active task | None |
| Next task | **S0-03** — write and freeze `docs/planning/PROTOCOL.md` (see §10 and the approved plan) |
| Implementing agent/session | Claude Code session, 2026-09-15 |
| Local checkout | `/exports/para-lipg-hpc/mdmanurung/cNMF`, branch `main` |
| Environment | conda env `cnmf_bench` (Python 3.10.20, cnmf 1.7.1 editable from this checkout, BLAS scipy-openblas 0.3.29). Activate: `module load tools/miniconda/python3.10/23.3.1 && source activate cnmf_bench` |
| Pinned upstream SHA | `5dbc5baaa0b9079b55bce554d801caa235a50457` (resolved via `git ls-remote https://github.com/dylkot/cNMF HEAD`; identical to local HEAD — see DECISIONS.md D002) |
| Implementation SHA / dirty patch hash | **`5f22d55caf2060d48af3877f8e1a57bf051c0e34`** — first harness commit (planning bundle + P0-01 evidence), parent `5dbc5ba…` (pinned upstream). Local only, **not pushed**. `src/cnmf/**` unmodified: `git diff 5dbc5ba..HEAD -- src/` is empty. Note this row names the commit *containing* the evidence; the row itself necessarily lands in the following commit |
| Environment lock hash | conda `4b79d3c18a7c2cc555a1755140579a82bdddbdc7d96c2eb2eef9b0ca0052e83b`, pip `e5082a753229bbde7e2c469bfcdf46786289522b5f51784a7594aa50b60c86b9` (`docs/benchmarks/registry/env_cnmf_bench.{conda,pip}.txt`) |
| Reproducibility tolerance | Relative Frobenius error < **1e-5**, same-environment, per artifact (D004). Upstream's absolute `TOLERANCE=1e-4` is explicitly **not** reused. No bitwise claim across BLAS/versions/threads/platforms |
| Protocol version/hash | NOT_FROZEN (S0-03 not started) |
| Baseline selector specification | NOT_WRITTEN (P0-06) |
| Recommended configuration | None — baseline not reproduced yet |
| Latest evidence tier | NONE |
| Last update by implementing agent | S0-01/S0-02 session, 2026-09-15 |
| Session checkpoint | S0-01, S0-02 DONE (audit note written); S0-03 not started; P0-01 env build NOT_RUN (module/miniconda path identified, untried) |

## 2. Progress counts

**3 / 31 tasks DONE** (S0-01, S0-02, P0-01).  
TODO: 28 · IN_PROGRESS: 0 · VERIFY: 0 · BLOCKED: 0 · DROPPED: 0

Scientific adoption remains separate and untouched: P0-01 establishes that the measuring apparatus runs and that upstream reproduces within a declared tolerance. It is **not** evidence for any feature.

States: TODO → IN_PROGRESS → VERIFY → DONE; also BLOCKED and DROPPED. Keep the denominator fixed for this scope; show dropped and blocked counts separately. Implementation completion is not scientific adoption.

## 3. Prototype and feature gates

| Prototype | Intervention | Software status | Scientific adoption | Evidence tier | Gate artifact |
|---|---|---|---|---|---|
| P0 | Unchanged baseline + evaluation | UNTESTED | NOT_APPLICABLE | NONE | Not created |
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
| S0-03 | Setup | Freeze scope and initialize benchmark/decision contracts | S0-02 | TODO | PROTOCOL.md draft; registries; baseline/reference distinctions — **not yet available** |
| P0-01 | P0 | Reproduce pinned upstream installation, tests and example | S0-03 (inverted — see D003) | DONE | Env `cnmf_bench` built + locked (`registry/env_cnmf_bench.{conda,pip}.txt`, SOURCE_AUDIT §1.4); test data downloaded + hashed (`registry/pytest_data_manifest.tsv`, 148 files); `pytest -vs tests` run, **1 failed / 37 passed**, full log at `registry/p0-01_pytest_run1.log`; failure diagnosed to upstream's scale-blind tolerance (D004, D005) with env proven correct by bitwise-identical `norm_counts`/`consensus_spectra` and exact seed/gene-list/YAML matches; determinism measured (`registry/nondeterminism_probe.tsv`, SOURCE_AUDIT §1.5.1); reproducibility tolerance declared (D004) |
| P0-02 | P0 | Implement data/artifact schemas, orientation and provenance checks | P0-01 | TODO | Schema tests; manifest examples; explicit expression units — **not yet available** |
| P0-03 | P0 | Implement simulator, scenario registry and data tiers | P0-02 | TODO | Saved truth; independent realizations; sealed manifest policy — **not yet available** |
| P0-04 | P0 | Implement four headline metrics and corruption/invariance tests | P0-03 | TODO | Matching/usage/prediction/cost tests and corruption outcomes — **not yet available** |
| P0-05 | P0 | Implement donor splits, frozen-panel projection and leakage tests | P0-02, P0-04 | TODO | Nested split proof; masked projection tests; normalization leakage tests — **not yet available** |
| P0-06 | P0 | Preregister training-only baseline rank selection and evaluation protocol | P0-04, P0-05 | TODO | Selector equation and edge cases; frozen development protocol — **not yet available** |
| P0-07 | P0 | Implement smoke workflow, CI, cache/restart and local/SLURM profiles | P0-05 | TODO | End-to-end smoke; cache/restart tests; explicit SLURM status — **not yet available** |
| P0-08 | P0 | Register a public multi-donor dataset and verify metadata | P0-02 | TODO | Accession/source, license, checksum and donor mapping; or external blocker — **not yet available** |
| P0-09 | P0 | Implement optional pinned GeneNMF comparator and output checks | S0-02, P0-02, P0-04 | TODO | R smoke result and conversion tests; or explicit environment blocker — **not yet available** |
| P0-10 | P0 | Run baseline/null controls and close P0 readiness gate | P0-01 through P0-09* | TODO | P0 gate, honest external-blocker scope, usable metric report — **not yet available** |
| P1-01 | P1 | Freeze A hypothesis, endpoints, margins and pairing | P0-10 | TODO | contracts/A.md with justified numerical decision rules — **not yet available** |
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

## 10. Resume instruction

Read `AGENTS.md`, `IMPLEMENTATION_PROMPT.md`, and this tracker; inspect the existing worktree; start the next dependency-ready task without implementing deferred features. Update this file and the experiment/decision ledgers with actual evidence before ending the session. If a command cannot run, record why and keep its status NOT_RUN or BLOCKED.

**Note for a cold session:** `docs/planning/contracts/` and `docs/planning/gates/` do not exist yet — only `FEATURE_CONTRACT_TEMPLATE.md` and `GATE_TEMPLATE.md` are present. Nothing in `contracts/` or `gates/` is expected before S0-03 closes.

The next task is **S0-03**: write `docs/planning/PROTOCOL.md`. P0-01 already ran ahead of it by deliberate decision **D003** (read that first — it carries a guard clause that environment findings must not drive scientific choices).

Before writing, read in this order: `SOURCE_AUDIT.md` §1.2 (the cNMF dataflow — three distinct spectra normalizations, two std pipelines), then §1.5 (measured determinism and the declared tolerance), then DECISIONS.md D004/D005.

The transform question flagged in §1.2 is **settled**: `docs/benchmarks/configs/ablation_plan.yaml` sets `test_library_total_normalization: forbidden`, and TPM-normalising a held-out cell uses its total across *all* genes — including validation-panel genes — which would leak validation information into the inference panel. So scoring uses the HVG-panel / `median_spectra` route, not all-gene / `spectra_tpm`.

PROTOCOL.md must define the seven names the configs reference but nothing defines: `preregistered_training_only_baseline_surrogate` (the largest item — the K-selection rule feature A competes against; a weak baseline would invalidate P1), `training_scale_squared_prediction_error`, `equal_donor_mean`, `nonnegative_least_squares_frozen_dictionary`, `transform: training_fitted_and_leakage_audited`, `fixed_gene_panels`, and the `metric`/`metric_definition_version` vocabulary — plus a hash convention. Numerical margins stay **null** here; they belong in `contracts/{A,B,C}.md`.
