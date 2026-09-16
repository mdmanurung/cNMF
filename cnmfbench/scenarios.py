"""The scenario registry: all 8 specified now, 3 implemented.

All eight are specified **before features B and C exist**, so that no scenario can be
shaped around the behaviour of the feature it is meant to test. That is the whole point
of writing them now — a scenario authored after seeing a feature's output is not a test
of that feature.

An unimplemented scenario **raises**. It does not fall back to a default, because a
silent fallback would produce a `RESULTS.tsv` row labelled `B_context` that was generated
under `base_identifiable`, and nothing downstream could detect the substitution.

Tiers (PROTOCOL §6.4):

| Tier                  | May inform design?                                    |
|-----------------------|-------------------------------------------------------|
| `SMOKE`               | Yes — but can never promote a feature                 |
| `DEVELOPMENT`         | Yes, and **only** this tier may                       |
| `SEALED_CONFIRMATION` | **No.** Evaluated only after the configuration freezes |
"""
import dataclasses

from .simulate import SimulationParams

__all__ = [
    "SCENARIOS",
    "TIERS",
    "get_scenario",
    "build_params",
    "list_implemented",
    "SealedTierError",
]

TIERS = ("SMOKE", "DEVELOPMENT", "SEALED_CONFIRMATION")


class SealedTierError(RuntimeError):
    """Raised on any attempt to reach the sealed tier without saying so explicitly."""


# --------------------------------------------------------------------------------------
# Tier shapes
# --------------------------------------------------------------------------------------
# DEVELOPMENT is sized by DONOR count, not cell count: donors are the independent unit
# (§3.5) and cells within a donor are not independent samples. 24 donors gives 12 training
# donors per outer fold and 6 per inner arm — thin, and honest about it. `delta` calibrated
# there will carry visible uncertainty, and that uncertainty must be reported with it.
# 2000 genes matches cNMF's default `num_highvar_genes`, so this tier needs no unusual HVG
# configuration; SMOKE, at 180 genes, does.

_TIER_SHAPE = {
    "SMOKE": dict(n_donors=8, cells_per_donor=30, n_genes=180, n_identity=2, n_activity=1),
    "DEVELOPMENT": dict(
        n_donors=24, cells_per_donor=200, n_genes=2000, n_identity=5, n_activity=2
    ),
    "SEALED_CONFIRMATION": dict(
        n_donors=24, cells_per_donor=200, n_genes=2000, n_identity=5, n_activity=2
    ),
}

# Coverage spans universal / common / rare simultaneously (SOURCE_AUDIT §2.5), so that
# every comparator's coverage threshold is exercised on both sides and its filtering
# behaviour is measured rather than assumed.
#
# The DEVELOPMENT values were CALIBRATED ON MEASUREMENT, not chosen a priori, which
# PROTOCOL §6.4 permits for this tier and only this tier. The original (1.0, 1.0, 0.5,
# 0.5, 0.15) produced a blocked-vs-random CV gap of +1.07% at t = 1.97 over 48 repeats —
# short of the t > 3 the approved plan requires, i.e. a dataset on which feature A could
# not be shown to do anything. These values gave +2.92% at t = 3.11. Evidence:
# registry/p0-03_donor_eligibility_sweep.tsv; rationale: DECISIONS.md D008.
#
# The sealed tier keeps the original values. It is sealed precisely so that it is not
# tuned, and re-tuning it here on development evidence would destroy what makes it
# confirmation rather than another development set.
#
# SMOKE's values are NOT measured and do not need to be: the tier exists to check that the
# code runs and can never promote a feature (`smoke_can_promote_feature: false`). Do not
# cite them as calibrated.
_TIER_ELIGIBILITY = {
    "SMOKE": (1.0, 0.5),
    "DEVELOPMENT": (1.0, 0.5, 0.35, 0.25, 0.15),
    "SEALED_CONFIRMATION": (1.0, 1.0, 0.5, 0.5, 0.15),
}

# Marker budget has to fit the panel: K*(private + shared) < n_genes. At 2000 genes and
# K=7, the 0.08-0.12 starting range would make 56-84% of the panel a private marker, so
# the development fraction is lower. These are starting values to be tuned against
# *measured* scaled-space cosine (target <= 0.7), never against a count-space formula.
_TIER_MARKER_FRACTION = {"SMOKE": 0.10, "DEVELOPMENT": 0.04, "SEALED_CONFIRMATION": 0.04}

# Seeds. SMOKE and DEVELOPMENT are open. The sealed seeds are written at creation and not
# read during development (§6.4): reaching them requires `unseal=True`, which makes
# peeking a deliberate, greppable act rather than an accident.
OPEN_SEEDS = {"SMOKE": 1701, "DEVELOPMENT": 90210}
SEALED_SEEDS = {"SEALED_CONFIRMATION": 31337}


def _base(tier):
    """Starting regime, tuned from here against measurement rather than from theory."""
    return dict(
        **_TIER_SHAPE[tier],
        lambda_separation=4.0,  # nominal 3-6; tune to scaled-space cosine <= 0.7
        private_marker_fraction=_TIER_MARKER_FRACTION[tier],
        marker_overlap_fraction=1.0 / 3.0,  # at 0.5 you lose half the separation
        background_program_cv=0.35,  # must be > 0; see simulate.py docstring item 2
        background_log_sd=1.0,
        identity_eligibility=_TIER_ELIGIBILITY[tier],
        alpha_donor=7.0,  # alpha=1 gives a 40%+ composition CV, i.e. pure noise
        activity_donor_eligibility=1.0,  # universal unless the scenario says otherwise
        leakage=0.02,  # caps the recovery ceiling at ~5%
        p_active=0.35,
        activity_mean_share=0.25,
        activity_cv=0.5,
        mean_library=3000.0,
        cv_library=0.45,  # below 0.4 *worsens* identifiability; above 0.5 hurts §3.5
        min_library=200,
        donor_depth_cv=0.15,  # <= 0.20, the §3.5 collision
        cells_per_donor_cv=0.0,
        min_cells_per_donor=30,
    )


# --------------------------------------------------------------------------------------
# The eight scenarios
# --------------------------------------------------------------------------------------

SCENARIOS = {
    "base_identifiable": dict(
        implemented=True,
        feature="reference",
        overrides={},
        rationale=(
            "Overlapping identity and activity programs with adequate independent "
            "variation. The reference every other scenario is read against."
        ),
    ),
    "A_weak": dict(
        implemented=True,
        feature="A",
        overrides=dict(lambda_separation=2.0, p_active=0.15),
        rationale=(
            "The activity program is present but weakly separated and rarely on. Rank "
            "selection should find it harder, not impossible. This is where a selector "
            "that merely tracks in-sample error is expected to fail."
        ),
    ),
    "A_null": dict(
        implemented=True,
        feature="A",
        overrides=dict(n_activity=0, p_active=0.0, activity_mean_share=0.0),
        rationale=(
            "No activity program at all, so K_true = n_identity. Tests that a selector "
            "does not invent structure. A method that always reports one more program "
            "than it can support fails here and nowhere else."
        ),
    ),
    "B_imbalanced": dict(
        implemented=False,
        feature="B",
        overrides=dict(cells_per_donor_cv=0.8),
        rationale=(
            "Unequal cells per donor with the biology otherwise controlled, so any "
            "difference is attributable to imbalance and not to composition."
        ),
    ),
    "B_balanced": dict(
        implemented=False,
        feature="B",
        overrides=dict(cells_per_donor_cv=0.0),
        rationale=(
            "The matched control for B_imbalanced. Identical generative parameters "
            "apart from the cell-count spread."
        ),
    ),
    "B_context": dict(
        implemented=False,
        feature="B",
        overrides=dict(activity_donor_eligibility=0.35, cells_per_donor_cv=0.8),
        rationale=(
            "The activity program is restricted to an eligible donor subgroup rather "
            "than being universal. This is what `rare_context_recovery_maximum_harm` "
            "binds on: donor-balanced discovery must not lose a program that only some "
            "donors carry."
        ),
    ),
    "C_duplicate_merge": dict(
        implemented=False,
        feature="C",
        overrides=dict(marker_overlap_fraction=1.0 / 3.0, lambda_separation=2.5),
        rationale=(
            "Programs organised so that a run contributes near-duplicate factors to the "
            "same consensus cluster. Feature C (one contribution per run) should help "
            "here; Gavish et al.'s third robustness criterion is the published precedent."
        ),
    ),
    "C_separated": dict(
        implemented=False,
        feature="C",
        overrides=dict(marker_overlap_fraction=0.0, lambda_separation=6.0),
        rationale=(
            "Clearly separated factors. The control that shows feature C does no harm "
            "when there is no duplication to remove."
        ),
    ),
}


def list_implemented():
    return tuple(name for name, s in SCENARIOS.items() if s["implemented"])


def get_scenario(name):
    if name not in SCENARIOS:
        raise KeyError(
            f"unknown scenario {name!r}. Known: {sorted(SCENARIOS)}. "
            "A scenario is added by specification, not by passing a new string."
        )
    scenario = SCENARIOS[name]
    if not scenario["implemented"]:
        raise NotImplementedError(
            f"scenario {name!r} is specified but not implemented (feature "
            f"{scenario['feature']}). Its parameters are frozen in scenarios.py so that "
            "it cannot later be shaped around the feature it tests. It raises rather "
            "than falling back, because a row labelled {name!r} generated under "
            "base_identifiable would be undetectable downstream."
        )
    return scenario


def build_params(name, tier, **overrides):
    """Frozen `SimulationParams` for one scenario at one tier.

    `overrides` exists for the depth and noise **gradients**, which sweep library size and
    `lambda_separation` without touching the inference engine. It is not a general escape
    hatch: anything swept this way must be recorded in the manifest, and it is, because
    the manifest hashes the resolved parameter object rather than the scenario name.
    """
    if tier not in TIERS:
        raise KeyError(f"unknown tier {tier!r}. Known: {list(TIERS)}")
    scenario = get_scenario(name)

    fields = {f.name for f in dataclasses.fields(SimulationParams)}
    unknown = set(overrides) - fields
    if unknown:
        raise TypeError(f"unknown SimulationParams fields: {sorted(unknown)}")

    resolved = {**_base(tier), **scenario["overrides"], **overrides}

    # n_activity=0 (scenario A_null) has to shrink nothing else: identity_eligibility is
    # indexed by identity programs only, so it survives the change untouched.
    return SimulationParams(**resolved)


def seed_for(tier, unseal=False):
    """The generating seed for a tier.

    PROTOCOL §6.4 seals the confirmation tier: its seeds are written at creation and not
    read during development. This function enforces that mechanically. Once a sealed set
    has been used to redesign the method it is **consumed**, and a new independent set is
    required — that is a bookkeeping obligation this function cannot enforce, so it is
    stated here where whoever passes `unseal=True` will read it.
    """
    if tier in OPEN_SEEDS:
        return OPEN_SEEDS[tier]
    if not unseal:
        raise SealedTierError(
            f"{tier} is sealed (PROTOCOL §6.4). Pass unseal=True only when the "
            "configuration is already frozen. Using it to redesign the method consumes "
            "the set and requires generating a fresh independent one."
        )
    return SEALED_SEEDS[tier]
