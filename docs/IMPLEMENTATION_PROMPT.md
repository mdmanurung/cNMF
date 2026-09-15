# Incremental, benchmark-driven improvements to cNMF

**Coding-agent implementation brief · 15 September 2026**  
**Target:** `dylkot/cNMF`  
**First-cycle scope:** P0 baseline; P1 predictive rank selection (A); P2 donor-balanced discovery (B); P3 run-aware consensus (C).

> This is a specification, not a report of implemented or validated improvements. Every implementation task starts as TODO. Treat all scientific benefits as hypotheses. Source descriptions are supported by the numbered references below; algorithmic choices in this brief are proposed designs to test, not claims that those sources implemented them.

## 1. Your assignment

Act as a scientific software engineer and statistical-methods developer working in a local cNMF checkout or fork. Improve the existing package incrementally, with a growing benchmark suite that can determine which change helps, which harms, and which is useful only in particular settings.

Preserve the original cNMF algorithm and public behavior. Build small, separately selectable additions rather than replacing cNMF with a new solver, introducing a new package brand, or combining many methodological changes in one prototype.

Deliver working code, tests, a reproducible Snakemake workflow, benchmark artifacts, and a continuously maintained `planning/PROGRESS.md`. A clean implementation is not evidence of a scientific improvement: report software correctness and scientific adoption as separate decisions.

### First action and execution boundary

Read existing repository instructions, inspect the checkout, and initialize the progress records. Implement S0 and then P0 before enabling A, B, or C. Once a stage is closed with evidence, proceed to the next eligible stage; a scientifically unsuccessful feature can be left disabled and need not prevent subsequent work. Do not implement deferred extensions during this cycle.

When a session ends, leave a truthful checkpoint and the exact next executable task. Do not claim that work will continue outside an active execution session. Do not invent results, source hashes, successful commands, reviewer assessments, benchmark data, or completed SLURM jobs.

## 2. Required scientific scope

| Stage | Single intervention | New stress test | Main decision |
|---|---|---|---|
| P0 | No algorithm change: instrumentation and evaluation only | Identifiable additive programs; intentionally corrupted solutions | Can we reproduce upstream and trust the measurements? |
| P1 / A | Choose rank using donor-blocked, observation-separated inner validation | Weak additional programs versus no additional structure; noise/depth gradients | Does rank selection improve independent prediction without unacceptable program-recovery loss? |
| P2 / B | Balance donor contributions during dictionary learning | Strong cell-count imbalance versus balanced donors; subgroup programs | Does balancing improve recovery in imbalanced data without suppressing genuine subgroup signals? |
| P3 / C | Limit each optimization run to one contribution per consensus program | Duplicate/merged components versus clearly separated components | Does run-aware aggregation improve recovery without harming valid overlapping programs? |

A, B, and C must be independently switchable. Report all eight configurations: `000`, `100`, `010`, `001`, `110`, `101`, `011`, `111`, with bit order A/B/C. A stage number is not an instruction to retain every previous feature.

**Deferred:** Poisson/NB fitting backends, adaptive solvers or seed budgets, Bayesian uncertainty, donor-specific loading models, graph/persistence inference across ranks, recursive hierarchical NMF, prior-guided factorization, sparsity changes, automatic pruning, multimodal learning, GPU optimization, differential-usage methods, and comprehensive cell QC. They may be recorded in a backlog, but not implemented implicitly.

NB and other non-Poisson distributions are allowed in the simulator: testing misspecification is not the same as implementing an NB inference engine.

## 3. Study existing implementations before designing replacements

Create `planning/SOURCE_AUDIT.md` with repository, resolved full commit SHA, retrieval date, package version, inspected paths/functions, license information, intended lesson, and limitations. Read source, not only README descriptions. Resolve default branches rather than assuming they are named `main`. Read applicable licenses and preserve attribution; prefer conceptual reimplementation or optional external adapters rather than copying code across incompatible licenses.

| Source | Inspect | Borrow now | Do not silently borrow |
|---|---|---|---|
| **cNMF** [1,2] | `README.md`, `Stepwise_Guide.md`, `src/cnmf/cnmf.py`, preprocessing code, packaging, CLI, tests and test-data downloader | Existing data preparation, repeated fits, consensus, spectra/usage refits, output formats, worker parallelism, restart behavior | No new defaults, replacement loss, replacement normalization, or discarded final refit |
| **GeneNMF** [3] | `R/main.R`, `R/utils.R`, `DESCRIPTION`, `NAMESPACE`, vignettes; trace `runNMF`, `multiNMF`, `getMetaPrograms`, `getNMFgenes`, `plotMetaPrograms` | Sample/rank/run provenance, full-loading-vector comparisons, gene-weight summaries, recurrence reporting, small runnable examples, an optional R comparator | Its preprocessing, RcppML engine, specificity weighting, meta-program clustering, or mean consensus must not enter the cNMF baseline |
| **R NMF** [4] | Rank surveys, repeated-run diagnostics, algorithm/initialization interfaces | Transparent diagnostics and reproducible comparisons | A sample-connectivity consensus or cophenetic score is not the same object as cNMF program consensus |
| **SigMoS** [5] | Paper's model-selection section and corresponding repository functions | Misspecification simulations, resampling logic, explicit model checking | Do not describe its full-data-exposure evaluation as strictly untouched test prediction |
| **SUITOR** [6] | Missing-observation validation and separation design | Explicit distinction between unobserved entries and observed zeros | Do not replace withheld entries by zeros in an ordinary NMF call |
| **mosaicMPI** [7] | Program/rank/dataset provenance and multiresolution program analysis | Prior-art awareness and compatible metadata conventions | Do not implement its broader network workflow or claim multi-rank program networks are new |
| **Snakemake** [8] | Current environment, profile, executor, checkpoint and reproducibility documentation | A portable local/SLURM workflow | No unverified historical executor/profile syntax |

The reviewed GeneNMF interface distinguishes `multiNMF` from `getMetaPrograms`; its README describes full-vector cosine comparisons, consensus weights, and gene-inclusion frequencies. Verify these at the pinned revision before using them. Frequencies are descriptive support, not calibrated probabilities. [3]

Current cNMF already has sparse input support, KL-loss capability, preprocessing for batch correction, worker parallelism, and reference-spectrum functionality. Preserve and document what exists; do not advertise those as new work. [2]

Build only **one external comparator adapter in the first cycle: GeneNMF**. Treat it as a different complete workflow, not an ablation of cNMF. Other repositories provide design precedents or future comparison targets, not mandatory dependencies.

## 4. Repository and working practices

Work in a local checkout/fork. Inspect `git status` before modifications and preserve unrelated user changes. Do not force-reset, delete untracked user files, push, open pull requests, or publish results without explicit authorization. Record code SHAs or dirty-tree patch hashes; never fabricate a commit identifier.

Use the existing Python packaging and public API. Prefer thin adapters and small modules; avoid rewriting the main implementation or modernizing packaging in the same change as an algorithmic intervention. A possible layout is below; adapt it after the audit rather than blindly imposing it.

```text
AGENTS.md                            # merge with existing instructions
planning/
  PROGRESS.md                        # task status and session handoff
  SOURCE_AUDIT.md                    # pinned upstream/source findings
  PROTOCOL.md                        # frozen benchmark and selection rules
  DECISIONS.md                       # append-only scientific/design decisions
  contracts/A.md, B.md, C.md          # hypotheses and decision margins
  gates/P0.md, P1.md, P2.md, P3.md    # evidence-based stage decisions
benchmarks/
  configs/                           # smoke/development/frozen configurations
  registry/                          # dataset manifests and split manifests
  comparators/                       # optional R GeneNMF adapter
  EXPERIMENTS.tsv                     # one row per execution, including failures
  RESULTS.tsv                        # tidy per-unit metric observations
workflow/
  Snakefile
  rules/
  scripts/                           # executable Python/R, not notebook logic
  envs/
  profiles/local/
  profiles/slurm/
src/cnmf/                            # preserve upstream package
  experimental/                     # optional: sampling, projection, selection, consensus
  ...existing files...
tests/                               # upstream tests plus focused new tests
results/exploratory/                  # development results; normally gitignored
results/approved/                     # promoted immutable evidence; provenance required
```

Do not create many empty abstractions or scaffold future methods. A few well-tested functions are preferable to a framework of unimplemented classes. R and Snakemake belong in optional comparator/workflow environments, not unconditional core-package dependencies. Use maintained Conda environments or existing images where practical; pin versions and image digests. Heavy work belongs in scripts, with notebooks used only to inspect produced artifacts.

## 5. Minimal data and artifact contracts

Use `X` as **cells × genes**, `U` as **cells × programs**, and `V` as **programs × genes** internally. An R adapter must explicitly transpose when needed. Gene names, cell IDs, and feature order must survive every conversion.

### Input contract

Accept an explicit expression source (`.X` or a named layer), immutable original counts, and metadata including unique `cell_id`, `sample_id`, and `donor_id`; optional columns include condition, timepoint, cohort, batch, and coarse cell type. Never infer donors from barcodes without a documented mapping. The basic legacy workflow may run without donor IDs, but donor-aware methods must fail clearly rather than treating cells as independent donors.

Validate dimensions, finite nonnegative values for factorization input, uniqueness, alignment, zero-variance genes, all-zero cells, missing donor IDs, invalid rank grids, and duplicate/missing features. Do not silently round corrected values into counts. Missing features and observed zeros are different states.

### Output contract

Each fit produces a dictionary artifact, usage artifact, program metadata, and a manifest containing the upstream SHA, implementation SHA/patch hash, environment, input checksums, preprocessing state, feature universe/order, discovery-cell hash, donor splits, seeds, rank, feature flags, consensus settings, runtime, failures, and parent artifact hashes.

Keep normalized and unnormalized usages explicitly distinct. Distinguish factorization spectra, TPM-like spectra, and signed association scores. Signed gene-score matrices are not valid nonnegative dictionaries. Save any transformation needed to put inferred and simulated loadings into the same gene units.

Cache keys must depend on input content, preprocessing fit, genes/order, discovery cells, split, rank, seed, solver, code revision, and relevant options. Consensus caches additionally depend on the factor-bank hash and C configuration. A/B/C variants must not overwrite or silently reuse incompatible artifacts.

## 6. P0: unchanged baseline and trustworthy evaluation

### P0.1 — Pin and reproduce upstream

1. Resolve the cNMF revision and install it in an isolated, reproducible environment.
2. Run available upstream tests and the smallest valid example; distinguish unavailable test data from a failing algorithm.
3. Save fixtures covering preparation, representative individual spectra, consensus spectra, usages, and result loading.
4. Establish same-environment reproducibility tolerances, considering label permutations and numerical roundoff; do not promise bitwise identity across BLAS implementations or platforms.
5. Keep an isolated upstream invocation as the reference. With all experimental behavior disabled and full-data discovery, outputs must match that reference within the preregistered tolerances.
6. Audit any internal use of training/global means, variances, TPM totals, and final usage/spectrum refits. Record this dataflow in `SOURCE_AUDIT.md`.

Do not bypass known upstream steps merely because another representation is more convenient. Evaluation adapters can use a named compatible representation, but must state exactly which artifact is being scored.

### P0.2 — Simulator and data registry

Implement a deterministic additive count simulator with saved normalized true loadings, usages, expected counts, donor/sample/context metadata, and independent stochastic realizations. Begin with identifiable, partially overlapping identity and activity programs with some discriminating genes; do not make the only test a perfectly separable toy.

Provide these progressively enabled scenarios:

- `base_identifiable`: overlapping programs with adequate independent variation.
- `A_weak` and `A_null`: a weak added activity versus no added latent component.
- `B_imbalanced` and `B_balanced`: unequal versus equal cell counts with otherwise controlled biology.
- `B_context`: an activity restricted to an eligible subgroup, not universal across donors.
- `C_duplicate_merge` and `C_separated`: difficult factor organization versus clear components.

Vary depth and Poisson/NB noise without changing the inference engine. Reserve perfectly collinear or non-identifiable scenarios for ambiguity diagnostics: do not demand a unique factor recovery that the simulated observations cannot identify.

Create three tiers: smoke tests for code execution, development experiments for design and calibration, and sealed confirmation datasets/seeds. The attached smoke configuration is illustrative, not an evidence-grade sample-size plan. Determine scientific replicate counts using pilot variability and desired precision, then freeze them before evaluation.

Add one small public multi-donor scRNA-seq dataset with a genuine donor mapping, recorded accession/download source, license, checksum, and processing manifest. Prefer an experimentally controlled condition when feasible. If network, permission, or data availability prevents this, run the synthetic suite, mark the real-data task BLOCKED, and do not claim biological validation. Do not use private user data unless explicitly supplied or authorized.

### P0.3 — Four headline measurements

1. **Program recovery:** align full loading vectors in common gene units with maximum-weight one-to-one matching and dummy unmatched factors. Report a continuous score `sum(matched cosine similarities) / max(K_true, K_inferred)` plus program precision/recall using a threshold calibrated on development controls and frozen before assessment. Record matched, missing, extra, and ambiguous factors; test specificity/background sensitivity.
2. **Usage accuracy:** use the loading-derived alignment, not a second alignment chosen to maximize usage agreement. Normalize consistently, retain missing/extra components as error terms in a union representation, and report donor-averaged error; conditional error among recovered programs is secondary and explicitly labeled.
3. **Generalization:** compute prediction loss on observations that entered neither dictionary fitting nor the corresponding usage estimation. Average within donors first, then across donors; report lineage/context strata as safeguards.
4. **Cost and reliability:** include complete selection/refitting cost, wall time, CPU time where available, peak memory with its measurement scope, failed fits, retries, and incomplete configurations. Cache reuse may be reported separately but cannot make an expensive algorithm appear free.

Add corruption tests: duplicate an inferred factor; delete a true program; shuffle or corrupt usages; permute labels; positively rescale a factor with compensating usage; reorder genes; and replace a solution by noise. The metrics must penalize damaging changes and remain invariant to irrelevant permutations and equivalent positive rescaling.

Do not use ARI, pathway enrichment, seed stability, or visually attractive embeddings as the principal success criterion.

### P0.4 — Implement the common validation machinery before A

The validation engine is shared by all configurations. **A changes whether inner validation selects rank; it does not give A a different outer evaluator.**

Use this nesting:

```text
Outer training donors
  ├── inner training donors → preprocessing + candidate dictionary fits
  └── inner validation donors
        ├── inference observations → estimate usages with frozen dictionaries
        └── validation observations → score candidates, choose K if A is on

Refit selected configuration on all outer training donors
Outer test donors
  ├── inference observations → estimate usages only
  └── unused observations → final evaluation; no retuning
```

Keep all samples, conditions, timepoints, and batches from an individual together in the donor split. Never allocate a donor across training and validation because its conditions differ. Stratification may use prespecified metadata, not gene-expression outcomes. Log folds that cannot support the scientific comparison; never silently drop difficult donors to improve results.

**Use a frozen gene-panel inference/validation split initially.** Training donors retain all eligible genes; only the held-out donors have one panel withheld from their usage estimation. Derive gene eligibility, selection, and scaling from the appropriate training donors. Generate panels from training information and independent fixed seeds, cover zeros as well as nonzeros, and use identical panels for all candidate ranks/configurations within a comparison. Record panel sizes and dictionary identifiability on the inference panel. Insufficient-information cases need a documented handling rule and a reported failure rate, not a test-informed replacement panel.

For a suitable nonnegative factorization-space dictionary:

```text
U_test = argmin_{U >= 0} || X_test[inference] - U @ V[inference] ||²
prediction = U_test @ V[validation]
```

The `X_test` above must be transformed using a **training-fitted, leakage-audited** transform. A practical first choice, if confirmed by the pinned upstream dataflow, is raw expression divided by training gene standard deviations, without a held-out-cell library-total normalization. Then usages absorb cell-level amplitude and predictions can be transformed back to count units using the same training scales. Do not insert a held-out total computed from validation genes. If the chosen upstream dictionary requires a different transform, write and test an explicit conversion/offset contract before running predictive evaluations.

Use the nonnegative dictionary in the matching factorization units, not normalized usage proportions or signed gene scores. All-gene refits, standardization, and gene-weight estimates use training/discovery cells only; test cells only receive frozen-dictionary projection. Do not update spectra on the test donor.

Primary P0–P3 loss is a clearly specified training-scale squared prediction error with common gene weights across variants; additionally report raw-unit reconstruction loss where valid. Do not label a squared loss a likelihood, or compare incompatible native losses as if they were the same metric. Freeze the evaluated gene universe, loss weights, and null/reference predictor within a fold. The null predictor must also use inference-only amplitude estimation.

Required leakage tests must show that modifying held-out values does not change the dictionary, preprocessing state, usages inferred from the inference panel, rank selection on unrelated inner folds, or cache identities of training-only artifacts. Modifying true outer-test values may change its score, but never chosen hyperparameters. Test row-total normalization leakage explicitly.

### P0.5 — Baseline rank procedure

Upstream cNMF provides a stability–error inspection workflow, not one universally prescribed automatic selector. [1,2] In `PROTOCOL.md`, define and freeze an auditable training-only baseline selector, its equation, tie handling, degenerate-curve behavior, and search-boundary behavior. Label it a **benchmark surrogate**, not an official upstream algorithm. Include complete fixed-rank curves and a second simple training-only heuristic as a sensitivity check; an independently recorded training-plot expert choice may be added but is not required for execution.

Do not tune the baseline or the new selector using true simulated rank or outer-test results. A true-rank oracle is permitted only as an explicitly labeled diagnostic and never as a deployable method.

### P0.6 — Workflow, comparator, and gate

Implement a smoke workflow that starts from generated data and reaches a machine-readable metric table and a brief report. Add local execution, CI, and a SLURM profile with declared resources; test the actual cluster submission only where a cluster is available, otherwise record `NOT_RUN_ON_SLURM`.

Add a small optional GeneNMF R adapter using the pinned source's native workflow. Record its feature selection, normalization, factor ranks, meta-program count (`nMP`), seed policy, and runtime. Convert its output with feature/order checks. Never tune `nMP` on the test set or simulated truth. When only native gene sets are available, score gene-set outcomes; any additional NNLS projection must be labeled an adapter-derived score, not a native GeneNMF usage. Use a frozen compatible full-weight dictionary for cross-method predictive scoring where possible; declare unavailable metrics rather than inventing comparability.

**P0 software gate:** reference compatibility, metric corruption tests, leakage tests, deterministic manifests, smoke workflow, and restart/cache checks pass. **P0 evidence gate:** baseline and null controls yield usable measurements, the real-data status is explicit, and a frozen protocol exists. A missing external dataset does not prohibit synthetic engineering work, but scientific claims remain simulation-only.

## 7. P1 / A: predictive rank selection only

1. Complete `contracts/A.md` before evaluating the feature: hypothesis, target regime, baseline comparator, primary endpoint, safeguards, minimum worthwhile gain, acceptable harm margins, compute cap, and independent evaluation units.
2. Implement a selector consuming only inner-validation results. Candidate fits, preprocessing, masks, and aggregation remain unchanged.
3. Primary A policy: choose minimum donor-averaged inner-validation loss, with deterministic preference for smaller K among exact/numerically defined ties. Report uncertainty and boundary minima. Keep a parsimonious tolerance/one-standard-error option as a separately labeled sensitivity, not a silently tuned second feature.
4. If reporting a one-standard-error heuristic, estimate uncertainty at the donor/independent-replicate level and label the rule a heuristic, not a confidence interval for a true biological rank; overlapping folds and optimization seeds are not independent samples.
5. Evaluate `000` versus `100` on `A_weak`, `A_null`, depth/noise gradients, and previous regression scenarios. Report prediction, recovery, rare-program sensitivity, selected-rank distributions, and full costs.
6. Test grid-boundary and flat-curve behavior; do not expand the rank grid after seeing outer-test outcomes. Expansion using inner-development evidence creates a new protocol version and requires fresh confirmation.
7. Close P1 with separate correctness and adoption decisions. A reduced test loss is not automatically better biological recovery; explicitly record trade-offs.

## 8. P2 / B: donor-balanced dictionary discovery only

1. Complete `contracts/B.md` before assessing outcomes.
2. For each training fold, fit **one common preprocessing state on the eligible training pool before either sampling arm**, and hold gene selection, scale, solver, rank grid, and consensus settings fixed. This deliberate shared state isolates cell-sampling effects; donor-aware HVG selection is deferred.
3. Choose a discovery-cell budget feasible for every eligible training donor. For the first implementation use a fixed per-donor cap, reduced using training metadata when necessary, sampling without replacement; document eligibility and shortfall handling.
4. Construct **B=1** with equal donor contributions and **B=0** with proportional contributions using the same total number of cells. Also retain unchanged full-data cNMF as a separate practical anchor. The matched-budget `000` arm is not identical to the full-data legacy anchor.
5. Preserve within-donor condition/timepoint composition through a fixed sampling policy; do not introduce condition balancing, cell-type balancing, donor-specific loading models, or additional regularization.
6. Save discovery cell IDs and seeds. Keep the sampled cell set fixed across ranks and optimization starts in an experiment; vary sampling only through a separately indexed sampling replicate. Do not confound sampling resamples with optimizer seeds.
7. Fit dictionaries and any spectra-changing refits using the selected discovery cells. Larger training pools and test cells may receive usages through frozen projection, but must not update V and thereby undo the balancing intervention.
8. Evaluate matched-budget `000` versus `010`, and `100` versus `110`, including fixed-rank comparisons. Test balanced, imbalanced, and subgroup-specific regimes using the same independent evaluation cells.
9. Report equal-donor and cell-weighted results separately. Preserve genuine context-specific programs; absence in an ineligible donor must not count as failed replication. These are reporting safeguards, not new program filters.
10. Close P2 as KEEP, CONDITIONAL, DROP, or INCONCLUSIVE with evidence; a conditional benefit under imbalance is a legitimate result, not a reason to declare universal superiority.

## 9. P3 / C: one contribution per run per consensus program

1. Complete `contracts/C.md` and save raw factor-bank hashes.
2. Use exactly the same individual factorizations for C off and C on, including input cells, K, seeds, convergence limits, and failure handling.
3. Preserve upstream factor normalization, density filtering, initial clustering, median/other verified summary convention, output ordering, and final refitting. Change only how many factors from a run contribute to an existing consensus cluster.
4. Start with a **one-pass run-aware deduplication**: for each baseline cluster and each run, keep at most the factor closest to that cluster's frozen baseline representative using the existing compatible normalized distance; resolve ties by stable component ID, then recompute the representative with the same upstream summary and normalizations.
5. Use baseline representatives only for that selection pass; do not add iterative re-clustering, Hungarian reassignment, new rejection thresholds, new outlier tuning, or adaptive K in this prototype. Record any later alternative as a deferred subexperiment, not the same C feature.
6. Report retained and omitted components, counts of distinct contributing runs, eligible/scheduled run denominators, cluster ambiguity, and effective nonempty rank. Never silently replace a failed fit or drop an empty component without a recorded reason. A missing consensus program cannot be disguised by inventing a replacement.
7. Test the one-contribution constraint, label/order invariance, deterministic ties, identical output when baseline clusters already satisfy the constraint, and handling of incomplete or invalid runs.
8. Benchmark direct factor-bank corruption fixtures and end-to-end correlated-program simulations. Deliberately injected duplicate factors validate mechanics; natural end-to-end failures are required to support a claim of practical benefit.
9. Compare `000` vs `001`, `100` vs `101`, `010` vs `011`, and `110` vs `111`; perform fixed-K tests before interpreting end-to-end selected-K results.
10. If there is no useful gain, retain the diagnostics but leave run-aware aggregation off. Do not enlarge C into a different consensus algorithm merely to obtain a favorable result.

## 10. Complete ablations and scientific decisions

At milestone evaluation run all eight A/B/C configurations on common data and folds, plus the full-data legacy anchor and the optional GeneNMF workflow comparator. Factorial causal interpretations apply to A/B/C, not to whole-workflow comparisons against GeneNMF.

Keep two analyses separate:

- **Fixed K:** `000`, `010`, `001`, `011` at the same candidate ranks; isolates B/C dictionary changes.
- **Selected K:** all eight configurations, each using its assigned selector; evaluates the complete workflow.

For each endpoint show paired differences, uncertainty, and prespecified strata. Report standalone effects, incremental effects, and interaction differences such as `S(AB)-S(A)-S(B)+S(000)` with metric direction stated. Do not search all endpoints and report only favorable contrasts.

Synthetic dataset realizations are independent units for simulator claims; donors or independent cohorts are the relevant units for biological claims, with appropriate grouping for repeated measurements. Aggregate repeated masks or optimization starts within their actual independent unit. Do not treat genes, cells, overlapping CV folds, or seeds as independent biological replicates. Describe limitations of any bootstrap/interval method and include failures in the summary.

Freeze gain and non-inferiority/harm margins in feature contracts using development pilot variability and scientific priorities. Numerical gates must refuse to run when required margins are null. Never back-fill margins after inspecting confirmation results. More precision can be collected under a recorded plan; repeated unplanned peeking cannot be sold as confirmation.

Every feature decision is one of:

- **KEEP:** adequate benefit in the claimed scope; safeguards and cost acceptable.
- **CONDITIONAL:** adequate benefit only in a defined regime; document the activation rule.
- **DROP:** no worthwhile benefit or unacceptable harm; default remains off.
- **INCONCLUSIVE:** insufficient evidence; no superiority claim and no automatic promotion.

Separately record **software status** as UNTESTED / PASS / FAIL / BLOCKED and **evidence tier** as SMOKE / DEVELOPMENT / SIMULATION_CONFIRMATION / BIOLOGICAL_CONFIRMATION. Passing smoke tests cannot yield a KEEP decision.

The reusable regression suite becomes development data through repeated use. A sealed confirmation set must be evaluated only after the method/configuration is frozen; once used to redesign the method, mark it consumed and require new independent confirmation. No dataset or code change may silently rewrite old benchmark decisions.

## 11. Workflow, software quality, and verification

Use script-based Snakemake rules for input validation, simulation/download, immutable donor splits, training transforms, discovery sampling, candidate fits, consensus, masked projection, rank selection, outer refitting, test scoring, comparator execution, aggregation, and reports. Factorization jobs should be independently restartable with success sentinels written atomically only after output validation.

Support local and SLURM profiles. Declare threads, memory, and runtime resources; cap BLAS/OpenMP threads to avoid nested oversubscription. Record actual scheduled resources. Do not submit heavy work to a login node. Sparse/chunked operations are required where practical; no dense N×N cell-consensus matrix or unconditional densification of a large dataset.

Create and test a small stable command interface. These are **requested commands to implement, not commands already present in upstream cNMF**:

```bash
python -m pytest tests -q
snakemake --snakefile workflow/Snakefile --profile workflow/profiles/local \
  --configfile benchmarks/configs/smoke.yaml smoke
snakemake --snakefile workflow/Snakefile --profile workflow/profiles/local \
  --configfile benchmarks/configs/development.yaml ablation_report
snakemake --snakefile workflow/Snakefile --profile workflow/profiles/slurm \
  --configfile benchmarks/configs/frozen.yaml confirmatory_report
```

Reconcile profile/config syntax with the installed pinned Snakemake release. Confirmation must require an explicit frozen-protocol state and cannot be triggered by an ordinary smoke run. Document exact tested commands and exit codes; where the environment prevents execution, label the command NOT_RUN and explain the blocker.

Required tests span: upstream compatibility; schemas; orientations; zero/missing handling; deterministic seeds; split integrity; masking and normalization leakage; metric corruption/invariance; matched discovery budgets; unchanged preprocessor state across B arms; identical factor banks across C arms; C constraint and no-op behavior; rank-selector edge cases; cache invalidation; interrupted-run restart; and end-to-end smoke output validation.

Prioritize correctness and transparent failures over coverage percentages. No fabricated external benchmarking, silent fallbacks, placeholders returning plausible numbers, or skipped scientific tests reported as passes. Keep large datasets and generated artifacts out of version control; preserve small manifests and audit summaries.

## 12. Track progress as part of every work session

Use `planning/PROGRESS.md` as the human-readable status document, not as a notebook of speculation. Before work, read it and select the next dependency-ready task. After every meaningful code/test batch, update task status, files changed, commands actually executed, result locations, and blockers. Update the decision and experiment ledgers alongside it.

Task states: `TODO → IN_PROGRESS → VERIFY → DONE`, plus `BLOCKED` and `DROPPED`. A checked task means its acceptance evidence exists, not that code was drafted. Report completion as `DONE / fixed in-scope task count`; show blocked/dropped counts separately and do not inflate completion by shrinking the denominator. Scientific adoption remains a separate field.

A gate document must contain: frozen protocol hash; code/environment versions; experiments and eligible units; primary paired effect and interval; every safeguard; costs/failures; deviations; software decision; scientific decision; supported scope; unsupported claims; and next permitted task.

At session end write: current prototype, last completed task, tested commands and outcomes, unresolved issues, exact next task, exact next command where known, and which artifacts must not be overwritten. If resources are unavailable, preserve the partial implementation and evidence instead of claiming completion.

## 13. Definition of the first-cycle deliverable

The cycle is complete when P0 is reproducible; A/B/C can be independently exercised; fixed-rank and selected-rank ablations run or have explicitly bounded external blockers; the GeneNMF comparator status is transparent; results and failure cases are auditable; compatibility and leakage tests pass; each feature has a recorded adoption decision; and a recommended configuration is supported by the available evidence tier.

The recommended configuration is allowed to be the original baseline. Negative or conditional results are valid outputs. Do not introduce a fourth methodological feature to avoid that conclusion.

Begin with **S0-01: audit the existing checkout and instructions**, initialize the supplied tracker, and work through P0. Do not begin by implementing all three switches at once.

## References and source entry points

[1] Kotliar et al. *Identifying gene expression programs of cell-type identity and cellular activity with single-cell RNA-Seq*. eLife, 2019. DOI: 10.7554/eLife.43803. https://elifesciences.org/articles/43803

[2] cNMF source and documentation. https://github.com/dylkot/cNMF ; https://github.com/dylkot/cNMF/blob/main/src/cnmf/cnmf.py ; https://github.com/dylkot/cNMF/blob/main/Stepwise_Guide.md

[3] GeneNMF source and documentation. https://github.com/carmonalab/GeneNMF ; https://github.com/carmonalab/GeneNMF/blob/master/R/main.R ; https://github.com/carmonalab/GeneNMF/blob/master/R/utils.R ; https://github.com/carmonalab/GeneNMF/blob/master/NAMESPACE

[4] Gaujoux and Seoighe. *A flexible R package for nonnegative matrix factorization*. BMC Bioinformatics, 2010. DOI: 10.1186/1471-2105-11-367. https://link.springer.com/article/10.1186/1471-2105-11-367 ; https://cran.r-project.org/web/packages/NMF/index.html

[5] Pelizzola, Laursen and Hobolth. *Model selection and robust inference of mutational signatures using Negative Binomial non-negative matrix factorization*. BMC Bioinformatics, 2023. DOI: 10.1186/s12859-023-05304-1. https://link.springer.com/article/10.1186/s12859-023-05304-1 ; https://github.com/MartaPelizzola/SigMoS

[6] *SUITOR: Selecting the number of mutational signatures through cross-validation*. PLOS Computational Biology, 2022. DOI: 10.1371/journal.pcbi.1009309. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1009309

[7] mosaicMPI, official documentation and repository link therein. https://mosaicmpi.readthedocs.io/en/latest/

[8] Snakemake, official deployment/reproducibility documentation. https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html

Default-branch links are source entry points, not reproducibility pins. Resolve immutable commits at implementation time and record them. Do not infer package maturity or scientific superiority from these descriptions alone.
