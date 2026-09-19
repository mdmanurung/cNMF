# Pre-registration v2: a replacement for feasibility criterion 2

**This document postdates the data that motivated it.** That is stated first because it is
the most important thing about it. Criterion 2 v1 was pre-registered at `f1e86fa`, failed at
`48718d7`, and the argument that it was mis-specified was written by the same person who had
just watched it fail. No amount of soundness in that argument repairs the ordering.

Two consequences follow, and both are binding:

1. **This criterion does not revise the v1 verdict.** `p0-03_development_feasibility.tsv`
   records NO-GO and keeps recording NO-GO. A re-scored old run is not a result.
2. **This criterion has no evidential force on the run that motivated it.** It may only be
   evaluated on a *fresh* run at a seed committed below, before that run exists.

## What was wrong with v1

> v1: fail if `observed(K_true)/floor < 1.02` **and** `observed(K_max)/floor < 1.02`

`K_true` and `K_max` both lie on the **overfit** side of the loss minimum, where the curve is
nearly flat by construction — adding capacity past `K_true` costs little. The rule therefore
measured a span that is *supposed* to be small and never looked at the underfit side, where
the benchmark's dynamic range actually lives. Measured at DEVELOPMENT: the grid spans
`1.137 → 1.016` (outer_0) and `1.166 → 1.010` (outer_1), while the `K_true → K_max` span the
rule inspected is 0.004 and 0.004.

It passed at SMOKE only because that grid's `K_max = 4` sat on the *underfit* side of a
`K_true = 3` curve. The same sentence tested a different quantity at the two tiers, which is
what makes it a defect rather than a threshold that happened to be strict.

## The replacement

> **Criterion 2′ — underfit span.** `error(K_min) − error(K_true) > 3 × paired SE`,
> paired per donor, on `heldout_squared_prediction_error_v1`, where `K_min` is the smallest
> rank in the pre-registered grid.

Three properties, each deliberate:

- **It tests the span v1 ignored.** `K_min → K_true` is the descent, not the plateau.
- **Its constant is not invented here.** `3 × paired SE` is carried verbatim from the
  approved P0-03 plan, the same constant criterion 1 uses. A magnitude threshold on the
  floor ratio would have to be a number chosen after seeing 0.121 and 0.156, which is
  exactly the failure this document exists to avoid.
- **It reports no winner.** It is a magnitude on a named span, using `K_true` only as the
  simulation's known validation label. It does not compute an argmin, and
  `test_verdict_never_reports_which_rank_won` stays intact: recording which K minimises the
  curve on an A-OFF row would be the baseline selector under another name (§2 requires the
  selector to refuse while `delta` is null; §5.3 makes `selected_rank` null by design here).

Criteria 1 and 3 are **unchanged** and carry over verbatim.

### Stated in advance: this criterion is expected to pass

Given the curve already observed, criterion 2′ will almost certainly pass on a comparable
dataset. Saying so now rather than presenting it afterwards as a success: on *this* benchmark
it has little discriminating power, and its value is as a guard for future tiers, other
scenarios and real data, where a genuinely flat descent is possible. A criterion that is easy
to pass on the data that inspired it is weak evidence, and it is labelled weak here rather
than quoted later as if it were strong.

## The seed, committed before the run exists

The replacement run is `p0-03-dev-criterion-v2`, identical to `development.yaml` except:

```yaml
seed: 31337          # split/optimizer; development.yaml used 90210
panel_seed: 20260919 # development.yaml used 20260918
```

`scenarios.seed_for("DEVELOPMENT")` still governs the simulation, so the dataset is the same
generative process at a new split and a new panel. Committing these values here, before the
run, is what makes the run a test rather than a search: a seed chosen after a first attempt
failed would be a different experiment wearing the same name.

**If this run is executed more than once, every attempt is reported**, including ones whose
verdict is inconvenient. A discarded attempt is a fabricated result.

## What the v1 remediation menu got wrong, recorded for the v1.1 amendment

v1 listed four permitted responses to NO-GO. Against the curve actually observed:

| v1 option | Why it does not apply |
|---|---|
| 1. Raise `lambda_separation` | Strengthens a benchmark already resolving rank correctly |
| 2. More depth or donors | Same |
| 3. Narrow the grid | Same; `K_max` is not absurdly placed |
| 4. Report that §6.3 cannot support predictive rank selection | Would be a **false report** given a curve that minimises at `K_true` in both folds |

None of the four is correct, because all four assume the *benchmark* failed. The v1 menu had
no branch for **the instrument being wrong**. That branch — "the criterion was mis-specified;
record the verdict, argue the defect, pre-register a replacement, test it on a fresh seed" —
is what this document is, and it belongs in the v1.1 amendment as a standing option for every
future pre-registration.

## Status

**NOT RUN.** No result exists for criterion 2′. Results append below and this file is not
otherwise edited.

## Results

Attempt 1 (2026-09-19, killed by session timeout, no rows — see above) is not
an evaluation. Attempt 2 below is the evaluation.

Attempt 2 (2026-09-19, run `p0-03-dev-criterion-v2`, config
`development_criterion_v2.yaml`: seed 31337, panel_seed 20260919): exit 0,
638 results / 16 experiments, all `ok_provisional`. Same dataset as v1
(manifest `31b4cf0b…` — same generative process, new split and panel, as
committed). Evaluated in place; not merged into tracked TSVs.

| fold | C1 (Kmax−Ktrue > 3×SE) | C2′ (Kmin−Ktrue > 3×SE) | C3 (sil range > 1e-6) |
|---|---|---|---|
| outer_0 | PASS (t=10.54) | **FAIL** (mean 74.49, 3×SE 104.17, t=2.15) | PASS (0.316) |
| outer_1 | PASS (t=16.50) | PASS (mean 40.70, 3×SE 37.17, t=3.28) | PASS (0.251) |

**Verdict: NO-GO** (rule: NO-GO if any fails). The v1 verdict stands unrevised
and so does this one — recorded, not overridden.

What the failure is made of (donor table read off the run's per-donor rows):
every one of the 24 test donors has K_min worse than K_true (diffs +3.4 to
+333.6, unanimous direction), but three outer_0 donors carry most of the mass
(+333.6, +283.1, +181.9) and inflate the SE past the 3× bar. This is variance,
not absence: the loss curves minimise at K_true in both folds, silhouette
ranges are 0.25–0.32, and criterion 1 passes at t>10 in both folds. The
instrument (paired t with n=12 against heterogeneous donor magnitudes) is
stricter than the signal's unanimity warrants — stated as an observation, not
as a revision, and not as a third criterion: re-replacing the replacement
would be exactly what §6.7 exists to prevent from happening quietly.

What it licenses: P1 runs regardless (A is measured, not gated, by this);
P1-04 must carry "benchmark may be unresolving at n=12/fold" as the live
alternative to any null A result on `base_identifiable`.
