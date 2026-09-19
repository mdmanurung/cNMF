# Source audit

Append-only. Do not delete earlier findings; add a dated correction entry instead.

## 1. cNMF (target package)

- **Repository:** `dylkot/cNMF` (canonical upstream), checked out locally as git remote `origin = git@github.com:mdmanurung/cNMF.git`.
- **Resolved commit SHA:** `5dbc5baaa0b9079b55bce554d801caa235a50457`
- **Resolution method:** `git ls-remote https://github.com/dylkot/cNMF HEAD` on 2026-09-15, compared against local `git rev-parse HEAD`. **The two SHAs are identical.** The local checkout's HEAD commit ("made preprocess compatible with Harmony 2.0") is upstream `dylkot/cNMF`'s current default-branch HEAD at audit time.
- **Consequence:** there is no fork/upstream divergence to reconcile. The four most-recent commits (`5dbc5ba`, `bc797f2`, `221a3c3`, `d5c7a45`) are all authored by `Dylan Kotliar <dylkot@gmail.com>` (verified via `git log -4 --format='%H %an <%ae>'`) — i.e. this is a synced fork carrying zero local modifications on top of upstream, not a fork with the checkout owner's own patches. "Reproduce pinned upstream" and "this local checkout" are the same object. See DECISIONS.md D002.
- **Retrieval date:** 2026-09-15.
- **Package version:** `1.7.1` (`src/cnmf/version.py`).
- **License:** MIT (`LICENSE`, root). Author: Dylan Kotliar. Attribution preserved as-is; no code copied out of tree — we work directly in this checkout.
- **Network status:** GitHub reachable from this host at audit time (`git ls-remote` succeeded in <15s). Not yet re-verified for large-file downloads (`download_pytest_data.py` targets `storage.googleapis.com`, untested this session).

### 1.1 Inspected paths/functions

`src/cnmf/cnmf.py` (1298 lines, read in full), `src/cnmf/preprocess.py` (473 lines, read in full), `src/cnmf/__init__.py`, `src/cnmf/version.py`, `setup.py`, `pyproject.toml`, `Extras/Dockerfile`, `download_pytest_data.py`, `README.md` (skimmed), `Stepwise_Guide.md` (not yet read line-by-line — deferred, not required for the P0.4 transform question).

### 1.2 Dataflow audit (P0.1 item 6): means, variances, TPM totals, refits

There are **two independent normalization/scale artifacts** in the core `cNMF` class, and they are used at different stages. Neither is computed per-fold; both are computed once, globally, over whatever set of cells is handed to `prepare()`/`consensus()`. This is the leakage surface any donor-blocked validation harness must replace.

**(a) Initial factorization matrix — `norm_counts`, built in `get_norm_counts` (cnmf.py:487-556), called from `prepare` (cnmf.py:452).**

1. HVGs are selected by `get_highvar_genes` / `get_highvar_genes_sparse` (cnmf.py:136-242) run on the **TPM matrix** (`tpm.X`, target_sum=1e6 via `compute_tpm`, cnmf.py:245-251) — a Fano-factor method (mean/var via `get_mean_var` = `sklearn.StandardScaler(with_mean=False)`, i.e. no centering, `.var_` only), not scanpy's `highly_variable_genes`. This uses **all cells passed into `prepare`** — no split awareness.
2. The **raw counts** matrix (`counts`, the object passed as `counts_fn`, not TPM) is subset to those HVGs → `norm_counts`.
3. `norm_counts` is scaled to unit variance, **zero_center=False** (`sc.pp.scale(norm_counts, zero_center=False)` for sparse; `norm_counts.X /= norm_counts.X.std(axis=0, ddof=1)` for dense) — i.e. **std-only scaling, no mean subtraction**, and the std is computed from `norm_counts` itself (the same cells, post-HVG-subset raw counts), not from TPM. Note the branch at cnmf.py:537 tests `sp.issparse(tpm.X)` to decide which scaling code path to take, but the object actually being scaled is `norm_counts`, not `tpm` — if a caller ever passes sparse counts with a dense `tpm_fn` (or vice versa), the wrong branch executes. Not exercised by any current test; flagged for a P0 input-validation/regression test, not fixed here (S0/P0 preserve upstream behavior, do not patch it).
4. This is the matrix (`self.paths['normalized_counts']`) that `factorize()` actually feeds to `sklearn.decomposition.non_negative_factorization`.
5. **Confirms** the brief's P0.4 proposal ("raw expression divided by training gene standard deviations, without a held-out-cell library-total normalization") is the right shape for *this* artifact — but the std must come from raw HVG counts, not TPM, and no library-size/total normalization is applied at this stage at all (TPM is used only for HVG selection, not as the input to the solver).
6. Failure mode already present upstream: any cell with 0 total counts across the HVG panel raises `Exception` (cnmf.py:550-554) — a hard crash, not a graceful drop. Any HVG with zero variance in the passed-in cell set divides by zero → NaN, only a `print()` warning (cnmf.py:539-540, 543-544), no exception. Both are candidate P0 input-validation checks (zero-variance genes, all-zero cells) already called out in the brief.

**(b) TPM-space artifacts — `tpm_stats`, `spectra_tpm`, final `refit_usage` — computed in `prepare` and consumed in `consensus`.**

1. `prepare()` computes `tpm = compute_tpm(input_counts)` (target_sum=1e6) once, then `input_tpm_stats` (`__mean`, `__std`, via `get_mean_var` / `.std(ddof=0)` for dense) over **all genes**, saved to `self.paths['tpm_stats']` (cnmf.py:435-445). This is a **global**, all-input-cells statistic, computed once, and reused unchanged for every later `consensus()` call regardless of K.
2. In `consensus()` (cnmf.py:823-985): after k-means clustering the L2-normalized merged spectra into `median_spectra` (a probability distribution per component, sums to 1 over HVGs) and refitting usages (`refit_usage`, NNLS via `non_negative_factorization` with `update_H=False`) against `norm_counts` to get `rf_usages`, the pipeline does a **second, separate refit** in TPM space: `refit_spectra(tpm.X, norm_usages)` → `spectra_tpm` (all genes, non-negative, TPM units — this is the "TPM-like spectra" object in the brief's contract).
3. `usage_coef` (`gene_spectra_score`) is computed by `efficient_ols_all_cols(rf_usages, tpm.X, normalize_y=True)` (cnmf.py:958) — OLS coefficients of TPM columns (globally mean/var normalized via the same `get_mean_var`, i.e. **global test+train stats if TPM here includes held-out cells**) regressed on usages. This is a **signed** matrix — explicitly not a valid non-negative dictionary, matching the brief's warning.
4. If `refit_usage=True` (default, cnmf.py:961-975 — the "final refit the brief forbids discarding"): `norm_tpm = tpm[:, hvgs]`, re-scaled to unit variance the same std-only way as (a) but **using `norm_tpm`'s own std** (freshly computed, not the saved `tpm_stats`); meanwhile `spectra_tpm_rf = spectra_tpm.loc[:, hvgs] / tpm_stats.loc[hvgs, '__std']` uses the **saved, `prepare()`-time global `tpm_stats` std** — i.e. two different std sources are combined in one refit (one fresh, one cached from `prepare`). Final `rf_usages` (the ones actually saved as `consensus_usages`) come out of this NNLS refit, not the pre-TPM-refit `rf_usages` from step 2.
5. **Practical consequence for P0.4:** if evaluation is scored against `median_spectra`/`merged_spectra` (raw-count-std units), the matching test-cell transform is raw-HVG-counts / training-raw-count-std (confirmed above). If scored against `spectra_tpm` / the final `refit_usage`-corrected usages, the matching transform is TPM(target_sum=1e6) at HVGs / training TPM-std — a **different** normalization pipeline than (a). These must not be conflated; the benchmark harness needs to declare, per metric, which dictionary/units it is scoring against, per the brief's "state exactly which artifact is being scored."

**(c) `k_selection_plot` / stability–error curve (cnmf.py:1119-1158, P0.5 relevant).** For each K it calls `consensus(k, skip_density_and_return_after_stats=True, ...)`, which skips density filtering (`density_threshold_str='2'`), runs k-means + `refit_usage` on the **same cells used for factorization** (no held-out split), and reports `silhouette_score` (stability proxy) and reconstruction sum-of-squared-error (`prediction_error`) as **in-sample** metrics. The two curves are plotted together (`k_selection_plot`) for the user to inspect visually; there is no automatic K-selection rule upstream. **Confirms** the brief's claim in P0.5 that upstream provides "a stability–error inspection workflow, not one universally prescribed automatic selector" — this is an in-sample diagnostic, not a validation-based selector, and must not be mistaken for one when building the A/P1 baseline surrogate.

**(d) Consensus / factor-bank provenance (P3/C relevant).** `combine_nmf` (cnmf.py:748-773) concatenates per-iteration spectra into `merged_spectra`, indexed by strings `'iter{iter}_topic{topic}'` — run identity (`iter`) and within-run component identity (`topic`) are already preserved in this index. `merged_spectra` itself is **unnormalized** (raw sklearn `non_negative_factorization` output). `consensus()` (cnmf.py:882) builds `l2_spectra = merged_spectra` with each row **L2-normalized to unit length** (`row / sqrt(sum(row**2))`) — this is the object used for the distance matrix, density filter, and k-means. After clustering, `median_spectra` (cnmf.py:913-916) is the **component-wise median** of `l2_spectra` rows within each cluster, then **row-sum-normalized to 1** (a probability distribution over HVGs) — a third, distinct normalization from both `merged_spectra` and `l2_spectra`. These three objects (unnormalized `merged_spectra`/`iter_spectra`, L2-unit-norm `l2_spectra`, sum-to-1 `median_spectra`) must not be conflated when the transform contract or a C implementation references "the spectra": clustering and distance calculations happen in `l2_spectra` units, but the saved consensus dictionary is `median_spectra` units. The distance matrix itself is **dense but over factors, not cells** (`euclidean_distances(l2_spectra.values)`, size = `n_iter*k` × `n_iter*k`) — acceptable, not the "no dense N×N cell matrix" concern from the brief. K-means clusters into `k` groups with **no run-membership constraint** (a single run's iteration can legally contribute multiple factors to one cluster — this is exactly the situation P3/C targets). A C implementation should operate on `l2_spectra`'s index-parseable run-provenance, at or before the k-means/median step, per the brief's "one contribution per run per consensus program."

**(e) `factorize()` discards per-run usages.** `self.paths['iter_usages']` is defined (cnmf.py:308) but never written; `factorize()` (cnmf.py:692-745) only saves `iter_spectra`. Usages are only ever obtained downstream via `refit_usage` against consensus/median spectra. This matters for any C variant that might want per-run usage, not just spectra — none currently exists upstream.

### 1.3 Two independent preprocessing entry points already exist (do not re-invent)

- **`cNMF.prepare()`** (cnmf.py) — the pipeline traced in 1.2(a)/(b). Internal Fano-factor HVG selection on TPM (target_sum=1e6), raw-count std-scaling, no batch correction.
- **`Preprocess.preprocess_for_cnmf()`** (preprocess.py:135-267) — a separate, optional front door. Uses scanpy's `sc.pp.highly_variable_genes(flavor='seurat_v3')` for HVG selection (operates on raw counts, not TPM), library-size normalizes to **target_sum=1e4 ("TP10K", not TPM/1e6)** for the `tp10k` output, applies `stdscale_quantile_celing` (std-only scale + top-quantile ceiling, default 99.99th pctile) to the HVG-subset matrix, and optionally batch-corrects via Harmony (`harmony_correct_X`, MOE ridge correction reapplied to expression space, not just PCs — `harmonypy.run_harmony`). Supports RNA+ADT splitting and an `exclude_genes` filter (upstream's own recent commits `221a3c3`/`bc797f2`/`d5c7a45`, all by Dylan Kotliar, touch this path: `exclude_genes` param, generic exclude-message, and a TP10K compute fix for newer scanpy). Output feeds `cNMF.prepare()` as **three separate inputs** — this was flagged as an open question in the S0-02 session and is now **RESOLVED** by the worked example at `README.md:96-101`: `counts_fn=<base>.Corrected.HVG.Varnorm.h5ad`, `tpm_fn=<base>.TP10K.h5ad`, `genes_file=<base>.Corrected.HVGs.txt`. Note also that `librarysize_targetsum` is a parameter — the README example passes `1e6`, so the `.TP10K` filename is a fixed label, not a guarantee about the normalization target actually used.
- **Consequence:** both pipelines compute "the std" from whatever cells are passed in, at a single global pass, no held-out awareness, consistent with the leakage risk described in 1.2. Neither pipeline can be called as-is inside the nested donor-split harness without modification (they don't accept separate "fit on training, transform test" calls) — P0.4/P0.5 implementation will need thin wrapper functions that replicate the training-only half of these transforms and apply frozen scales to held-out cells, not reuse `prepare()`/`preprocess_for_cnmf()` directly on mixed train+test data.

### 1.4 Environment status (blocks P0-01, not S0)

- System `python3` is 3.6.8 (`/usr/bin/python3`); `pip list` returns nothing usable — no scientific stack on system Python. cNMF's `install_requires` (`scikit-learn>=1.0`, `anndata>=0.9`, `scanpy`) cannot run on 3.6.
- No `conda`/`mamba`/`micromamba` on PATH. `module avail python` (Environment Modules) offers `system/python/3.9.x` through `3.12.6` and `tools/miniconda/python3.{8,9,10,12}/*`.
- Upstream's own `Extras/Dockerfile` pins `python==3.7`, `scikit-learn==0.23.2`, `scanpy==1.6.0`, etc. — too old to satisfy the checked-in `install_requires` floor (`scikit-learn>=1.0`, `anndata>=0.9`) and not usable as a literal recipe; it documents *intent* (conda-forge/bioconda channel pins), not a runnable spec against current `install_requires`.
- **Status: RESOLVED 2026-09-15 (P0-01).** Environment built and locked; see §1.5 for measurements. Resolution:
  - `module load tools/miniconda/python3.10/23.3.1` provides conda. `~/.condarc` already redirects `envs_dirs`/`pkgs_dirs` to `/exports/archive/hg-funcgenom-research/mdmanurung/conda/` — necessary, because **`/home` is 96% full (482 MB free)** and cannot hold a scanpy stack.
  - A pre-existing env named `cnmf` was found (Python 3.10.20, cnmf 1.7.1, all deps present). Its `site-packages/cnmf/*.py` is **byte-identical** to this checkout, but it is a non-editable install, so it tests a *copy* rather than the checkout. It belongs to the user's working setup and was **left untouched**.
  - Built `cnmf_bench` as `conda create --clone cnmf`, then `pip install -e . --no-deps` (so `import cnmf` resolves to `/exports/para-lipg-hpc/mdmanurung/cNMF/src/cnmf/__init__.py`) plus `pytest`. `pip freeze` records the editable install as `git+ssh://…/cNMF.git@5dbc5baaa0b9079b55bce554d801caa235a50457`, pinning the commit in the lock itself.
  - Locks: `docs/benchmarks/registry/env_cnmf_bench.{conda,pip}.txt`. BLAS is `scipy-openblas 0.3.29`; thread caps were set explicitly for all measurements, as unset thread counts change floating-point reduction order.
  - Upstream's `Extras/Dockerfile` pins (python 3.7, scikit-learn 0.23.2, scanpy 1.6.0) remain unusable against the checked-in `install_requires` floor and were not followed.

## 1.5 Measured reproducibility and determinism (P0-01, 2026-09-15)

All measurements below come from the isolated `cnmf_bench` environment (conda, Python 3.10.20, cnmf 1.7.1 installed editable from this checkout, numpy 2.2.6 / scipy 1.15.3 / scikit-learn 1.7.2 / scanpy 1.11.5, BLAS `scipy-openblas 0.3.29`), with `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`. Environment locks: `docs/benchmarks/registry/env_cnmf_bench.{conda,pip}.txt`.

### 1.5.1 Risk 2 — the unseeded consensus refit does NOT produce nondeterminism

Predicted risk (from the S0-02 source read): `get_nmf_iter_params` builds `_nmf_kwargs` (cnmf.py:618-627) with **no `random_state`** and `init='random'`; `factorize()` injects `random_state` per replicate (cnmf.py:738) but `refit_usage()` (cnmf.py:792-798) re-loads the kwargs from the saved YAML, which never contained one. So the consensus usage refit initialises `W` from numpy's **global** RNG.

**Measured result: no observable nondeterminism.** With the factor bank held fixed (upstream's own reference `merged_spectra`, as `tests/test_reproducibility.py` does), `consensus(k=7, density_threshold=0.1)` was called 10× under two conditions — `free` (no seeding between calls) and `seeded` (`np.random.seed(12345)` before each call). **All five saved artifacts were bitwise identical across all repeats in both conditions** (`consensus_spectra`, `consensus_usages`, `gene_spectra_tpm`, `gene_spectra_score`, `starcat_spectra`). Evidence: `docs/benchmarks/registry/nondeterminism_probe.tsv`, script `nondeterminism_probe.py`.

**Explanation:** with `update_H=False` the spectra are fixed, so minimising `‖X − WH‖²` over `W ≥ 0` is a **convex** problem with a unique optimum. Initialisation therefore does not change the converged solution. The `free` condition genuinely did start from different RNG states (each `consensus()` call consumes entropy, so successive calls begin at different states), and still produced identical output.

**Instrument validated after the fact (2026-09-16 review).** The paragraph above reports a *null* result, and a null from an instrument never shown to be sensitive is not evidence. A positive control was therefore added — `docs/benchmarks/registry/nondeterminism_positive_control.py`, log alongside it — which reuses the probe's own `compare()` and `snapshot()`:

- **Measuring chain is sensitive.** Nudging a single element of each saved artifact by a relative `1e-9` and re-running `compare()` is detected for **all five** artifacts (relative Frobenius 4.9e-11 to 3.3e-10, `bitwise_identical=False` in every case). The probe could have seen a difference had one existed.
- **Causal reach is narrower than the original claim.** Perturbing the refit output non-uniformly by a relative `1e-6` moves `consensus_usages` (2.5e-07), `gene_spectra_tpm` (4.0e-07), `gene_spectra_score` (3.5e-07) and `starcat_spectra` (2.0e-07) — but leaves `consensus_spectra` at exactly 0.0, because it is computed **upstream** of the refit (`cnmf.py:913-916`, KMeans `random_state=1`).

**Correction to the claim above:** Risk 2 concerns the *unseeded refit*, so only the **four refit-derived artifacts** are evidence about it. `consensus_spectra` was never capable of testing Risk 2; its stability is evidence about the seeded KMeans instead. The refutation stands on four artifacts, not five. (A first attempt at this control used a *uniform scalar* perturbation of the refit and appeared to show four artifacts "blind"; that was a defective control — a global factor cancels exactly under the row normalisation those artifacts undergo — not a finding about the probe. Recorded so the mistake is not repeated.)

**Terminology.** "Bitwise identical" here means exact numeric equality of `float64` arrays after `load_df_from_npz`, not identity of file bytes. For these artifacts the two coincide; the looser phrase is retained above only because it is what the recorded evidence used.

**Scope limits — do not over-generalise.** This was measured at one dataset, one K, one density threshold, and the default `beta_loss='frobenius'` → `solver='cd'` path. All repeats ran in **one process**, which exercises the global-RNG mechanism Risk 2 names but not cross-process effects. It does **not** establish determinism for the `kullback-leibler`/`mu` solver, for ill-conditioned or rank-deficient `H`, or for larger problems where the convergence tolerance (`tol=1e-4`, `max_iter=1000`) may bite before the fixed point is reached. Re-measure before relying on it in a different configuration. The harness should still set seeds defensively; it simply does not need to treat consensus as a nondeterminism hazard in this configuration.

### 1.5.2 Risk 1 — upstream's own test suite fails at its pinned SHA, for a tolerance-scale reason

`pytest -vs tests` → **1 failed, 37 passed** in 20.11 s (full log: `docs/benchmarks/registry/p0-01_pytest_run1.log`). All 36 `test_prepare.py` tests pass. Of the two `test_reproducibility.py` cases, the **PBMC** case passes and the **simulated** case fails.

The single failure is `gene_spectra_tpm.k_7.dt_0_1` on the simulated dataset: SSE `0.0718` against a budget of `1e-4`. Because the test's loop order is `consensus_spectra → consensus_usages → gene_spectra_score → gene_spectra_tpm → starcat_spectra`, the first three **passed** before the failure.

Measured agreement against the reference, simulated dataset:

| Artifact | Shape | Absolute SSE | Relative Frobenius | Verdict at 1e-4 |
|---|---|---|---|---|
| `norm_counts` (solver input) | 2500 × 1000 | **0.000** | **0.000** | PASS (bitwise) |
| `consensus_spectra` | 7 × 1000 | **0.000** | **0.000** | PASS (bitwise) |
| `gene_spectra_score` | 7 × 7394 | 1.2e-17 | 4.3e-08 | PASS |
| `consensus_usages` | 2500 × 7 | 2.5e-10 | 4.3e-07 | PASS |
| `starcat_spectra` | 7 × 1000 | 5.9e-10 | 6.4e-07 | PASS |
| `tpm_stats` | 7394 × 2 | 3.1e-06 | 2.0e-08 | PASS |
| `tpm` | 2500 × 7394 | 2.4e-02 | 3.6e-08 | would FAIL (never reached) |
| `gene_spectra_tpm` | 7 × 7394 | 7.2e-02 | **1.4e-06** | **FAIL** |

**Why a downstream artifact is cleaner than its input.** The table looks self-inconsistent at first read: `consensus_usages` agrees to 4.3e-07 while `gene_spectra_tpm` — which it is computed *from* — differs by 1.4e-06. This is not a measurement error. The final `refit_usage` (cnmf.py:961-975) derives `spectra_tpm_rf` from `spectra_tpm`, then solves a **convex** NNLS for the usages with that matrix held fixed. A ~1e-6 relative perturbation of `H` moves the optimum of that problem by less than itself, so the usages are *less* perturbed than their input — the same convexity that explains §1.5.1. This is argued, not separately verified; a direct check (perturb `spectra_tpm` by 1e-6 relative, re-run the refit, measure the usage change) is cheap and would settle it if it ever becomes load-bearing.

Exact-equality artifacts — which are BLAS- and version-independent and therefore decide whether the *environment* is correct — all match: `nmf_replicate_parameters` seed columns EXACT, overdispersed gene list EXACT (1000 genes), `nmf_run_parameters` YAML EXACT.

**Diagnosis.** The environment is correct: the matrix that actually reaches the solver (`norm_counts`) and the consensus dictionary (`consensus_spectra`) are *bitwise* identical to the reference. Every discrepancy is confined to TPM-unit matrices, whose entries reach ~6.3e4, at a **relative** error of 1e-6–1e-8 — ordinary floating-point/library difference. The test compares an **absolute** sum of squared error over the whole matrix against a fixed `1e-4`, so a matrix in TPM units breaches the budget at a relative agreement that is, scientifically, exact.

**This is not stale-reference drift in the general sense, and not a regression.** Our own repeated runs are bitwise identical to each other (§1.5.1); they differ from the 1.6.0-generated reference only on the TPM-scale artifacts of the *simulated* dataset. The PBMC dataset reproduces **bitwise, including its `gene_spectra_tpm`** (max |value| 6.99e4) — so this is specific to the simulated input path (a `.txt` counts file, parsed by `pd.read_csv` then converted dense→CSR at cnmf.py:390-402) rather than a generic scale effect, and most likely originates in `compute_tpm`'s `sc.pp.normalize_total` on that input under a newer scanpy/numpy.

**Declared same-environment reproducibility tolerance** (for our own harness, replacing upstream's scale-blind budget): compare on **relative Frobenius error with a threshold of 1e-5**, applied per artifact, plus a bitwise check reported separately where it holds. No bitwise-identity promise is made across BLAS implementations, library versions, thread counts or platforms. Upstream's absolute `TOLERANCE = 1e-4` must not be reused as a correctness criterion for TPM-unit matrices.

### 1.5.3 Upstream test coverage map — what the suite can and cannot certify

| Pipeline step | Covered? | By what |
|---|---|---|
| `prepare` | Partly | `test_prepare.py` asserts **file existence only**, no numerics; `test_reproducibility.py` compares its outputs numerically |
| `factorize` | **No** | Never called — `test_reproducibility.py` copies reference `merged_spectra` in instead |
| `combine` / `combine_nmf` | **No** | Never called |
| `consensus` | Yes | Numerically, at fixed K and density threshold |
| `k_selection_plot` | **No** | Never called |
| `load_results` | **No** | Never called |

Consequences: the two most expensive and most seed-sensitive steps (`factorize`, `combine`) have **zero** upstream coverage, and the stability/error curve underlying any K-selection surrogate (`k_selection_plot`) is untested. Our harness must supply its own coverage there; passing upstream's suite certifies far less than it appears to. There is also no `conftest.py`, no `skipif` and no data-availability fixture — absent test data produces an error inside the test body, not a skip.

## 2. The meta-program lineage: Gavish et al. and GeneNMF (documentation audit, 2026-09-16)

Read at the user's direction. **Documentation only — no code inspected, nothing installed, no SHA resolved.** The comparator adapter remains deferred to P0-09; what follows is prior art that bears on decisions being taken *now*, recorded so those decisions are made with it in view rather than retrofitted to it later.

Sources: the GeneNMF CRAN reference manual (v0.9.2, dated 2025-09-11, GPL-3, `carmonalab/GeneNMF`), read in full; the BCC methods excerpt supplied by the user; and the pan-cancer meta-program methods of Gavish et al., *Nature* 2023 (`s41586-023-06130-4`), supplied by the user. GeneNMF packages the Gavish approach, so they are one lineage, not two independent precedents.

### 2.1 What the lineage actually does

Both factorize **each sample separately** over a **range of K** and then cluster the resulting programs across samples into *meta-programs* (MPs). Neither selects a rank.

| | Gavish et al. 2023 | GeneNMF (`getMetaPrograms`) |
|---|---|---|
| Per-sample NMF over K | K = 4…9 → 39 programs/tumour | `multiNMF(k=5:6, ...)`, any vector |
| Input scale | centred expression, negatives set to 0 | `slot="data"` (log-normalised), `center=FALSE`, `scale=FALSE` |
| Program representation | **top 50 genes** by NMF coefficient | top genes by `weight.explained=0.5`, capped at `max.genes=200` |
| Similarity | **Jaccard** on gene sets | `metric = "cosine"` or `"jaccard"` |
| Clustering | custom greedy founder/accretion algorithm | `hclust`, `hclust.method="ward.D2"`, cut to `nMP` |
| MP definition | genes common to member programs, completed to 50 by NMF score | genes seen in ≥ `min.confidence` of member programs |
| Number of MPs | emergent (67 initial → 41 retained) | `nMP` is a **user-set hyperparameter** (default 10) |

Gavish's three robustness criteria are worth stating exactly, because two of them map onto features in this programme:

1. **robust within the tumour** — a program recurring across K values in the same tumour (≥70% gene overlap, 35/50 genes)
2. **robust across tumours** — ≥20% similarity with any program in any other tumour
3. **non-redundant within the tumour** — programs ranked by similarity to other tumours' programs and selected greedily; once selected, any other program *from the same tumour* overlapping ≥20% is **removed**

### 2.2 Feature C has published precedent

**Criterion 3 is feature C.** The brief's C is "for each baseline cluster and each run, keep at most the factor closest to that cluster's frozen baseline representative"; Gavish's is "once a program is selected, drop any other program from the same tumour that overlaps it". Same intent — stop one source contributing several near-duplicate factors to one consensus — differing in the unit (their *tumour*, our *run*) and the rule (their greedy overlap threshold, our nearest-to-representative).

GeneNMF **exposes the diagnostic but does not deduplicate**: `metaprograms.metrics` reports "number of gene programs in MP" and `metaprogram.composition` reports "the number of individual [programs] for each sample that contributed to the consensus MPs". So the pathology is measured and left to the user.

Consequences, to be carried into `contracts/C.md` when P3 opens: C is not a novel invention and must not be presented as one; the greedy-overlap formulation is a legitimate alternative worth reporting as a sensitivity; and `metaprogram.composition` is the natural diagnostic to report for our own consensus, whether or not C is adopted.

### 2.3 Both operate on gene sets, not spectra vectors — a metric gap

cNMF clusters **full L2-normalised nonnegative spectra** by Euclidean distance (`cnmf.py:882, 908`). This lineage reduces each program to a **top-gene set** and compares by Jaccard. That is a different object, not a different parameterisation of the same one.

`PROTOCOL.md` §5.2 defines `program_recovery_cosine_v1` over "full loading vectors in common gene units". **For a comparator that emits only gene sets, that metric is unavailable** — which is exactly the case `IMPLEMENTATION_PROMPT.md:204` anticipates ("When only native gene sets are available, score gene-set outcomes; any additional NNLS projection must be labeled an adapter-derived score, not a native GeneNMF usage").

**Open item, flagged now rather than discovered at P0-09:** the frozen §5.2 vocabulary contains no gene-set recovery metric. Adding one (a Jaccard/overlap sibling to the cosine metric) is a **protocol amendment under §9**. It is not needed for P0 or P1 — which are cNMF-vs-cNMF and have full spectra on both sides — but it must be added *before* any comparator row is written, and the cleanest moment is the v1.1 amendment that sets `delta`. Recorded so it is not back-filled under deadline.

### 2.4 The comparator is structurally uninformative for feature A

Feature A selects a rank. **This lineage never selects a rank** — it sweeps K and pools every program across all K values, moving the hyperparameter to `nMP` (GeneNMF) or letting cluster count emerge (Gavish). There is therefore no sense in which GeneNMF "chooses K better or worse" than our baseline.

So: the GeneNMF comparator is informative for **B** (per-sample factorization is the limiting case of donor-balanced discovery) and for **C** (§2.2), and **not** for A. Recording this prevents a later attempt to construct an A-comparison that has no meaning. Note also `IMPLEMENTATION_PROMPT.md:204` already forbids tuning `nMP` on the test set or simulated truth — with `nMP` user-set and unjustified even in the source papers (the BCC paper "asked for 10 target MPs" with no stated rationale), that is a live risk.

### 2.5 Sample coverage — the finding that changes P0-03 now

Both papers filter programs by how many samples support them, at very different thresholds:

- Gavish criterion 2: a program must resemble a program in **at least one other** tumour (≥20% similarity) — an effective floor of 2 samples; MPs drawn from only a single study were additionally dropped.
- BCC/GeneNMF: MPs with **sample coverage below 40%** were dropped, alongside filters on <5 genes and negative average silhouette. `metaprograms.metrics` field (a) is "freq. of samples where the MP is present"; the paper defines coverage as "the proportion of samples in which the MP was detected".

**Direct consequence for the simulator (P0-03, in progress).** The plan's donor-eligibility fix sets `q_k ≈ 0.10–0.20`, i.e. programs present in 10–20% of donors. A GeneNMF comparator configured as the BCC paper configured it would **discard every such program by construction**, and would then appear to fail at rare-program recovery for a reason that is a documented user setting rather than a property of the method. That would be an unfair comparison, and the unfairness would be invisible in the result.

The simulator must therefore **span the coverage axis rather than sit at one end of it** — programs at roughly universal (1.0), common (~0.5), and rare (~0.15) donor coverage within the same dataset, so that any method's coverage threshold is exercised on both sides and its filtering behaviour is measured rather than assumed. This also serves `B_context` directly, and gives `rare_context_recovery_maximum_harm` something real to bind on.

### 2.6 Still deferred

Repository SHA, license verification in situ, installation, and any code inspection remain P0-09 work. Nothing here has been executed and no comparator row may be written until those are done and `genenmf_full_commit_sha` is pinned in the configs (currently `null`, with a recorded reason).

## 2.7 P0-09 execution (R smoke, 2026-09-19)

§2.6's deferred items are now done. Pinned source `carmonalab/GeneNMF`
`59942b27c2cc2dbf55264b80b4ff26e3188cdf41` (v0.9.6), cloned off-repo to
`cnmf-comparators/GeneNMF-59942b2/`. License verified in situ: **GPL-3**
(DESCRIPTION) — hence adapter-only use; no GeneNMF code is copied into this
repository. Installed into conda env `R4_51` (R 4.5.1; only missing dep was
`lsa`, installed from CRAN); `cnmf_bench` untouched, so `environment_hash`
provenance on all tracked rows is unaffected. Code inspected: `multiNMF`
(R/main.R:43 — per-sample RcppML::nmf over a K vector, Seurat `data` slot,
own `findHVG`; sample exclusion under `min.cells.per.sample`) and
`getMetaPrograms` (R/main.R:209 — cosine/Jaccard similarity, ward.D2 hclust
cut to user-set `nMP`, consensus genes at `min.confidence`, empties removed,
weights renormalised to sum 1). R smoke (`docs/benchmarks/comparators/
run_genenmf_smoke.R`): 240×180 SMOKE counts → 24 models (8 donors × k=2:4) →
10 MPs in 2.3 s; record at `registry/p0-09_genenmf_smoke.tsv`. Two §2
predictions confirmed in execution: MP weights sum to 1 (asserted in
`test_comparator.py`), and Seurat rewrites `gene_00001` → `gene-00001`,
which the conversion check accounts for. Gene-set recovery metric still
absent from §5.2 by design — no comparator row may be written until P2-01
adds it by amendment; smoke needs none.

## 1.6 cNMF API behaviour, measured by running it (P0-03, 2026-09-16)

The traps below were previously recorded from source reading. They have now been
**executed** against the pinned revision, and running them corrected two of the recorded
claims and added one that source reading had missed. Regression tests:
`cnmfbench/tests/test_io_and_cnmf_interop.py`. None of these raises a clear error on its
own; each produces a run that completes and reports something other than what it appears
to.

### 1.6.1 `n_iter <= 3` breaks density filtering — **new, not found by reading**

`consensus` computes
`n_neighbors = int(local_neighborhood_size * merged_spectra.shape[0] / k)`
(`cnmf.py:879`). Since `merged_spectra` has `n_iter * k` rows, this reduces to
`int(0.30 * n_iter)` and is **independent of k**. At `n_iter <= 3` it is zero,
`local_density` is a sum divided by zero, every comparison against the threshold is
False, and consensus raises:

> `RuntimeError: Zero components remain after density filtering. Consider increasing density threshold`

The message points at the threshold, which is not the cause — no threshold value fixes a
division by zero. Verified for `n_iter` in {2, 3, 4, 5, 10, 20} at `k` in {3, 7, 12}.

**This invalidated `smoke.yaml`**, which had `optimizer_starts: 3`. Every consensus call
in the smoke tier would have failed. Changed to 5.

### 1.6.2 The reused-run-name trap is the opposite of what was recorded

Recorded previously as "a reused name silently skips factorization". Measured, the
`completed=True` marking and its `UserWarning` occur inside `get_nmf_iter_params`, which
`prepare()` calls — so the warning fires at **prepare** time. And `factorize` defaults to
`skip_completed_runs=False` (`cnmf.py:692`), so with default arguments it **re-runs**
every replicate.

So silent skipping requires `skip_completed_runs=True`. The live hazard with default
arguments is that a reused directory silently **overwrites** the previous run's factors
while the warning scrolls past. A fresh `name`/`output_dir` per run is still required; the
reason is overwriting, not skipping.

### 1.6.3 The `.h5ad` requirement is confirmed end-to-end

`obs['donor_id']` survives `prepare()` into `norm_counts.h5ad` — asserted against the real
pinned package, not a mock. It does **not** reach the consensus artifacts, which carry
only `obs.index` (`cnmf.py:920, 975`), so donor labels must be re-joined on the cell index
downstream. Both halves are now pinned by tests.

### 1.6.4 AnnData closes one route to the §6.1 identifier clause

AnnData coerces an integer index to strings on construction
(`ImplicitModificationWarning: Transforming to str index`), so a dataset built through
AnnData cannot violate the positional-identifier clause. The underlying hazard is real but
is not about dtype: cNMF's `.npz` and tab-delimited readers rebuild `obs`/`var` as bare
indices (`cnmf.py:396-402`) and **discard `donor_id` entirely**, which the donor-column
clause catches.

## 3. Other reference repositories (R NMF, SigMoS, SUITOR, mosaicMPI, Snakemake)

Not inspected this session — none gate S0/P0 acceptance evidence per the brief's table (design precedents, consulted when the relevant task is active: P0.4/P0.5 for SUITOR/SigMoS design precedent, workflow tasks for Snakemake). Will be filled in incrementally as those tasks become active, not pre-scaffolded now, per AGENTS.md's instruction against creating unused abstractions.
