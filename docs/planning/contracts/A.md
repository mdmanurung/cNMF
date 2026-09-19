# Feature contract — A (donor-blocked predictive rank selection)

Status: FROZEN at P1-01 (v1.1 amendment) — hypothesis, endpoints, margins and pairing fixed below; changing any of them after seeing an A-ON row creates a new protocol version
Protocol version/hash: v1.1, `cc5241076a6c3e5f98b7575f0b09b12337c119e6ddaea685514692ebc9d42ec9`
Code/environment revision: harness `e277e5a`, upstream `5dbc5baaa0b9079b55bce554d801caa235a50457` (`src/cnmf/**` unmodified)
Evidence tier: NONE for adoption. DEVELOPMENT evidence exists and informs design only.

## Why this file exists now

`PROGRESS.md` carried an obligation due **before P1**:

> Feature A's hypothesis text must be restated before P1 to say "measures generalisation to
> unseen donors, which random-cell CV overestimates", never anything about per-donor leakage.
> Writing it the old way would be claiming a mechanism this session measured and did not find.

This file discharges it. The original framing — that random-cell CV leaks information *within*
a donor and donor-blocking removes that leak — was measured directly and **not found**, so it
must not survive into P1 in any document A's result will be read against.

## Hypothesis and scope

**Scientific failure addressed.** Random-cell cross-validation estimates how well a factor
bank predicts *held-out cells from donors it has already seen*. That is not the quantity a
user of cNMF cares about: they care whether programs learned on their cohort transfer to a
donor the model has never seen. Random-cell CV **overestimates** that transfer, so a rank
chosen to optimise it can be too high.

**Exact intervention, in one sentence.** Choose the factorization rank by minimising held-out
predictive error measured on donors excluded from training, instead of on cells excluded from
training.

**The mechanism, stated as measured and not as assumed.** Three arms were compared under the
frozen §6.3 contract (`registry/p0-03_donor_eligibility_sweep.tsv`, D008):

| contrast | result | reading |
|---|---|---|
| leakage at **fixed** donor count | **t = −0.37** | no per-donor leakage effect detected |
| donor **count** | **t = +4.30** | the effect is donor count |
| blocked vs random, as originally posed | +2.92%, t = 3.11 | real, but confounds the two above |

So the gap A is meant to close is **not** intra-donor leakage. It is that an estimate built on
more donors, each contributing less, generalises differently from one built on fewer donors
each contributing more — and donor-blocked evaluation is what makes that difference visible.
Any claim in P1 that A "removes leakage" contradicts this measurement.

**A concrete mechanism, from the DEVELOPMENT feasibility run.** In fold `outer_0`,
`n_training_carriers_per_identity_program = [12, 3, 3, 4, 1]`: one identity program is carried
by a **single** training donor. A program seen in one donor cannot be distinguished from that
donor's idiosyncrasy by any amount of cell-level resampling — every random-cell split still
has it in training. Only a donor-blocked split can ever place it entirely out of sample. This
is the sharpest available statement of what A measures that random-cell CV cannot, and it is
an observation from a committed run, not a construction.

**Everything deliberately held constant.** The cNMF algorithm, its loss, its normalization,
and its final refit. A changes *which cells are scored*, never how the factorization is
computed. B and C are OFF in every comparison that isolates A.

**Target scenario and expected direction.** `base_identifiable`. A-ON should select a rank at
or below A-OFF's, and should not lose program recovery to do it.

**Safeguard scenarios.** A scenario where donors are exchangeable, in which A should cost
nothing and change nothing: if A moves the answer where there is no donor structure, it is
adding variance rather than removing bias.

**Out-of-scope claims.** A says nothing about per-donor leakage; nothing about whether cNMF's
programs are biologically correct; nothing about real data until P0-08 provides it. A does not
claim that donor-blocked error is *lower* — it should generally be **higher**, because it
estimates a harder quantity honestly.

## Comparison

- Treatment configuration: `100`
- Matched control configuration: `000`
- Full-data upstream anchor: `arm: upstream_full_data`
- Fixed-rank comparisons: every `candidate_rank` in the frozen grid
- Selected-rank comparisons: **blocked until `delta` is set** (PROTOCOL §2; the selector must refuse while it is null)
- Sampling, split and factor-bank pairing rules: same dataset realisation, same outer folds, same panel seed; A changes only the *inner* evaluation
- Appropriate independent evaluation unit: **donor** (§3.5), never cell

## Frozen endpoints and margins

| Role | Metric and exact definition | Direction | Decision margin | Evidence used to set margin |
|---|---|---|---|---|
| Primary | `heldout_squared_prediction_error_v1`, equal-donor mean | Lower | **30** (training-scale units) | 3× donor-level SE (10.45, n=48 donor-rows) at K_true=7 in DEVELOPMENT 000 controls (`p04-dev-000m`, both folds); mean 422, so the margin is ~7% — a gain smaller than this is indistinguishable from donor noise |
| Safeguard: program recovery | `program_recovery_cosine_v1`, reported beside its matched null | Higher | **max harm 0.01** | ~12× the experiment-level SE (0.0008) at K_true in the same controls — but n=2 folds makes that SE a thin basis, stated here; 0.01 is small against the 0.15 fit–null gap (0.983 vs 0.83) |
| Safeguard: rare/context-specific recovery | NOT_SET — no rare-program metric exists yet | Higher | **NOT_SET** | — (blocks adoption on this safeguard until defined; P1-04 may close INCONCLUSIVE on it rather than force a metric into existence under deadline) |
| Safeguard: prediction | `usage_error_v1` | Lower | **max harm 0.05** | 3× experiment-level SE (0.0106 → 0.032) at K_true in the same controls, rounded up; mean 0.41 |
| Safeguard: cost/failures | `wall_seconds_v1`, `failed_fits_v1` | Lower | **25× the paired 000 total wall** | Relative cap (hardware-independent): the inner loop adds ~28 fits (≈10–20× the outer fit), so 25× bounds A's price with headroom; failures counted, never averaged away |

**No scientific adoption decision may be issued while the rare-recovery row reads NOT_SET**, except an INCONCLUSIVE close that states exactly this. All other margins above are frozen with the v1.1 amendment on development controls, before any A-ON row exists.

**Margins frozen at P1-01 above**, on development controls, before any A-ON row exists. The rare-recovery exception is stated in the table, not waived here.

## Known obstacle, recorded before P1 rather than discovered during it

The DEVELOPMENT feasibility gate returned **NO-GO** (`registry/p0-03_development_feasibility.tsv`,
D012). The criterion that failed is mis-specified and a replacement is pre-registered for a
fresh seed, but as of this writing **no run has demonstrated that the benchmark resolves rank
under a criterion fixed in advance of it**. The loss curve does minimise at `K_true` in both
folds, and under-convergence has been ruled out as an explanation, so the prospects are good —
but that is an observation, not a passed gate.

A's primary endpoint is a *rank selection* claim. It should not be run for adoption until a
pre-registered feasibility criterion has passed on a seed it did not motivate.

Second obstacle: donor count and per-donor depth are **not separable** at the 24-donor
DEVELOPMENT tier. If that separation matters for interpreting A's result, the tier needs more
donors — a P1 decision with a compute cost, not something reanalysis can fix.
