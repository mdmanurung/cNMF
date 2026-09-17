# Pre-registration: can the benchmark resolve rank at DEVELOPMENT scale?

**Written and committed BEFORE the run.** Git history is the evidence that these criteria
preceded the result. A feasibility threshold chosen after seeing a flat curve is not a
threshold, and the whole programme's discipline is that constants are fixed before the
data is seen (PROTOCOL §2, §9; `AGENTS.md`: "Do not change thresholds after seeing
confirmation results").

**Status at time of writing: NOT RUN. No development-tier result exists.**

## The question

The skeleton measured the benchmark against its exactly-computable Poisson floor at SMOKE
scale and found thin headroom at the top of the rank curve: K=2 sat 18–22% above the floor
but `K_true` sat only ~5% above, with the K→K+1 gap comparable to that margin. The overfit
penalty scales as `d_eff / |G_inf|`, so moving from 180 genes to 2000 weakens it roughly
11-fold.

If the curve is flat at development scale, **feature A — donor-blocked predictive rank
selection — has nothing to select on**, and P0-04, P0-05 and P0-06 would be built on a
premise that does not hold. This run answers that for ~20 minutes of compute.

## What is being run

`docs/benchmarks/configs/development.yaml`, configuration `000`, scenario
`base_identifiable`, 24 donors × 200 cells × 2000 genes, `K_true = 7`, candidate ranks
`[4,5,6,7,8,9,10]`, 2 outer folds, 10 optimizer restarts.

**This is not a rank-selection run.** `delta` is null and §2 requires the selector to
refuse; `000` is in `fixed_rank_configurations` and §5.3 makes `selected_rank` null by
design. What is measured is whether a K-curve with usable structure *exists* — never which
K wins. Recording a winner would be the baseline selector under another name.

## The three criteria, fixed now

### 1. Curve structure

> `error(K_max) − error(K_true) > 3 × paired SE`

Carried verbatim from the approved P0-03 plan, so it is not being invented at the moment
of use.

**Pairing is per donor.** Each test donor contributes `L_d(K_max) − L_d(K_true)` from the
per-donor rows already written; the SE is taken across the 24 donors. Pairing within a
donor cancels the fold's gene panel and per-gene scale, so donors from different folds are
comparable **in the difference** even though their levels are not (see
`cnmfbench/analysis.py`). Donors are the independent unit under §3.5; cells are not.

Computed on `heldout_squared_prediction_error_v1`, the primary loss.

### 2. Not flat by arithmetic

> Fail if `observed(K_true)/floor < 1.02` **and** `observed(K_max)/floor < 1.02`

Both ends sitting on the irreducible Poisson floor means no selector can work whatever its
rule, because there is no signal left to select on. The floor is exact here because the
generative model is Poisson with known `Λ`.

At SMOKE the ratios were 1.05 (`K_true`) and 1.06–1.12 (`K_max`), so this test would have
passed there.

### 3. Silhouette not degenerate

> Dynamic range over the grid `> 1e-6`

PROTOCOL §1.4's threshold. Below it the degenerate branch fires and the baseline **always**
selects the smallest K, making the eventual `000` vs `100` comparison meaningless.

At SMOKE the range was 0.115 and 0.035.

## Verdict rule

**GO** if all three pass. **NO-GO** if any fails. Reported per fold and in aggregate.

## What each outcome licenses — also fixed now

Written in advance so that a remediation cannot be chosen because it flatters the result.

**GO** → proceed to P0-04, recording the floor ratios as the context every future rank
claim is read against.

**NO-GO** → the finding is that *feature A is not testable at this tier as configured*.
That is a reportable result, not a failure to conceal. Permitted responses, in order of
preference, each requiring its own decision entry:

1. Raise program separation (`lambda_separation`), tuned against **measured scaled-space
   cosine**, never a count-space formula.
2. Increase depth or donor count — strengthens the curve without touching program
   structure.
3. Narrow the candidate grid, and only if the failure is `K_max` being absurdly far from
   `K_true`.
4. **Report that the frozen §6.3 contract cannot support predictive rank selection at
   achievable scale.** A genuine result about the method, and the honest end point if 1–3
   do not work.

**Not permitted:** changing the criteria above, expanding the candidate grid after the
fact (§1.4 forbids it outright), or switching to whichever metric happens to separate the
ranks.

## Amendment, added while the run was still in flight and the result unknown

`max_optimizer_iterations: 300` (inherited from `smoke.yaml`; upstream's default is 1000)
produces `ConvergenceWarning: Maximum number of iterations 300 reached` at this scale.

**Under-converged factorizations are a recognised confound for criteria 1 and 2**: if the
fits have not converged, a higher K cannot express its extra capacity, the curve flattens
for a numerical reason rather than a scientific one, and the run would report NO-GO when
the benchmark is in fact capable.

Declared now, before the verdict is known, so that acting on it afterwards is not fishing:

> If criterion 1 or criterion 2 fails, a re-run at `max_optimizer_iterations: 1000`
> (upstream's default) is a **permitted diagnostic** to rule out under-convergence. It
> does not change any criterion or threshold. If the verdict flips, the reported finding
> is that the original setting was too low — not that the benchmark passed on a second
> attempt. If criterion 3 fails, this does not apply; a degenerate silhouette curve is not
> a convergence artifact.

Convergence is a property of the fit, not of the benchmark, and ruling it out is part of
measuring the benchmark honestly.

## Results

Appended after the run, in `p0-03_development_feasibility.tsv`. This file is not edited
again except to link that result.
