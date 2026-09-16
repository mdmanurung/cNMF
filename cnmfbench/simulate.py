"""P0-03: the donor-structured simulator.

Generates synthetic scRNA-seq counts with **known** programs and **real** donor
structure, so that every downstream metric is scored against a ground truth rather than
against another method's output. Implements PROTOCOL §6; written before the schema layer
by decision D006.

Model, in one line: `X ~ Poisson(U V)`, with donor structure carried entirely in `U`.

Why donor structure lives in the usages and not the spectra: PROTOCOL §6.3 fixes a
single global `K_true x n_genes` truth matrix. Donor-specific spectra would need a
protocol amendment, so they are out of scope — and they are not needed, because the
effect feature A must detect is a *composition* effect.

THE ONE DESIGN DECISION THAT MAKES OR BREAKS THIS FILE
------------------------------------------------------
A first draft drew each donor's composition as `pi_d ~ Dirichlet(alpha * pi_global)`.
Under that model **donor-blocked validation equals random splitting in expectation**,
and feature A would have had nothing to detect. The argument: held-out usages come from
per-cell NNLS against a frozen `V` (§3.3), which is independent across cells, so a
cell's conditional risk depends on its latent state and on `V-hat`, never on which donor
it came from. Donor identity enters only through `pi_d`, and `E[pi_d] = pi_global`, so
the two expectations coincide. Donor blocking would change only the variance. Worse, a
Dirichlet with `alpha > 0` plus a leakage floor gives *every* donor full support on
*every* program, so the usage cone — which is what NMF actually recovers — is identical
for every donor subset, and `V-hat` barely moves with the training set.

The fix is `identity_eligibility`: a per-donor Bernoulli(q_k) mask applied to **identity**
programs before the Dirichlet. A donor's usage cone becomes a strict *sub-cone*, which is
the only change that makes `V-hat` genuinely training-set-dependent. Applying it only to
activity programs would just be scenario `B_context` under another name.

`q_k` spans coverage rather than sitting at one end of it (SOURCE_AUDIT §2.5): published
practice filters programs by donor coverage at thresholds that vary widely — Gavish et
al. require support from >=2 tumours, the BCC/GeneNMF paper drops any meta-program below
40% sample coverage. A dataset of *only* rare programs would be discarded wholesale by a
comparator configured as published, which would look like a failure of the method rather
than of the setting, and the unfairness would be invisible in the result. So each dataset
carries universal (`q ~ 1.0`), common (`q ~ 0.5`) and rare (`q ~ 0.15`) programs at once.

FOUR THINGS THAT LOOK LIKE TUNING BUT ARE CORRECTNESS
-----------------------------------------------------
1. `lambda_separation` must be tuned against **scaled-space** cosine, not count-space.
   The engine divides by per-gene std, and because `s_g ~ mu_g` here, that division acts
   as a per-gene *mean* normalisation: the shared background cancels, amplifying it
   relative to the discriminative direction. True-spectra cosine measured 0.74 in count
   space against 0.94 in scaled space on the drafted parameters. The attenuation
   saturates in lambda, so raising lambda alone cannot escape it. Use
   `diagnostics.scaled_space_cosine`; never a count-space formula.
2. `background_program_cv` must be > 0. With equal marker mass across programs, a
   background gene has zero across-program variance, so Fano ~ 1 by construction. Two
   bad consequences at once: the std division inflates background genes relative to
   markers, and cNMF's Fano-based HVG selection becomes a *perfect oracle* for the marker
   genes, making the gene panel unrealistically easy and the result externally invalid.
3. Every program needs >= 1 private marker, checked structurally *and* by numerical rank
   before a single count is drawn. Spectra rank is fixed by marker-set combinatorics and
   **no value of lambda repairs a deficiency**: `M1={a,b}, M2={c,d}, M3={a,c}, M4={b,d}`
   gives `M1+M2 = M3+M4`, rank 3 not 4.
4. `donor_depth_cv` stays small. PROTOCOL §3.5 (`equal_donor_mean`) weights donors
   equally while squared error scales with depth^2, so a 2x depth spread contributes a 4x
   term that swamps any feature-A effect. §3.5 is frozen; this parameter is not.

Recorded so a later "optimisation" cannot silently invalidate the benchmark: the
observation **must stay Poisson with `L_c` as an expectation parameter**, never a
multinomial with a fixed realised total. Under Poisson, inference-panel and
validation-panel counts are conditionally independent given `Lambda`; under a multinomial
they are negatively correlated, which biases every held-out score.
"""
import dataclasses
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import PROTOCOL_VERSION
from .contract import ContractViolation, check_dataset
from .hashing import parameter_hash

__all__ = [
    "SimulationParams",
    "SimulatedDataset",
    "simulate",
    "build_spectra",
    "build_marker_sets",
]


@dataclass(frozen=True)
class SimulationParams:
    """One frozen parameter set. Frozen because a scenario's definition must not drift
    between the session that specified it and the session that runs it."""

    # --- size ---
    n_donors: int
    cells_per_donor: int
    n_genes: int
    n_identity: int
    n_activity: int

    # --- spectra ---
    lambda_separation: float
    private_marker_fraction: float
    marker_overlap_fraction: float
    background_program_cv: float
    background_log_sd: float

    # --- donor structure ---
    identity_eligibility: tuple  # q_k, one per identity program
    alpha_donor: float
    activity_donor_eligibility: float  # 1.0 = universal; < 1 is scenario B_context

    # --- usages ---
    leakage: float
    p_active: float
    activity_mean_share: float
    activity_cv: float

    # --- depth ---
    mean_library: float
    cv_library: float
    min_library: int
    donor_depth_cv: float
    cells_per_donor_cv: float
    min_cells_per_donor: int

    # --- guarantees ---
    min_expected_gene_counts: float = 20.0
    observation_model: str = "poisson"

    @property
    def k_true(self):
        return self.n_identity + self.n_activity

    def __post_init__(self):
        if self.observation_model != "poisson":
            raise ValueError(
                "PROTOCOL §6.5 fixes the simulator's observation model to poisson. A "
                "negative-binomial *solver* is a deferred feature and must not be "
                "introduced implicitly; overdispersion here comes from the lognormal "
                "library and activity magnitudes, not from changing the draw."
            )
        if len(self.identity_eligibility) != self.n_identity:
            raise ValueError(
                f"identity_eligibility has {len(self.identity_eligibility)} entries for "
                f"{self.n_identity} identity programs"
            )
        if not all(0.0 < q <= 1.0 for q in self.identity_eligibility):
            raise ValueError("identity_eligibility entries must lie in (0, 1]")
        if not 0.0 <= self.marker_overlap_fraction <= 1.0 / 3.0:
            # Above 1/3 you lose half the separation lambda bought.
            raise ValueError("marker_overlap_fraction must lie in [0, 1/3]")
        if self.leakage > 0.02:
            raise ValueError(
                "leakage > 0.02: a leakage floor eps permits a mixing ambiguity of order "
                "eps*K in the recovered spectra regardless of lambda, sample size or "
                "optimizer. That is program_recovery_cosine_v1's analytic ceiling."
            )
        if self.donor_depth_cv > 0.20:
            raise ValueError(
                "donor_depth_cv > 0.20 collides with frozen PROTOCOL §3.5 "
                "(equal_donor_mean): squared error scales with depth^2, so a depth "
                "spread contributes a term that swamps any feature-A effect."
            )
        if self.background_program_cv <= 0.0:
            raise ValueError(
                "background_program_cv must be > 0, else Fano-based HVG selection "
                "becomes a perfect oracle for the marker genes (see module docstring)."
            )
        if self.min_cells_per_donor < 30:
            raise ValueError(
                "min_cells_per_donor < 30: equal_donor_mean (§3.5) gives a 5-cell donor "
                "the same weight as a 500-cell donor."
            )

    def as_dict(self):
        """Canonical-JSON-ready parameter mapping for the §6.6 manifest hash."""
        d = dataclasses.asdict(self)
        d["identity_eligibility"] = list(d["identity_eligibility"])
        return d


@dataclass
class SimulatedDataset:
    """What one realisation produces. `adata` carries the counts and donor labels;
    truth is stored alongside per §6.3, never inside the counts."""

    adata: "object"  # anndata.AnnData, imported lazily so the module imports without it
    true_spectra: np.ndarray  # K_true x n_genes, rows sum to 1, var.index order
    true_usages: np.ndarray  # n_cells x K_true, obs.index order
    expected_counts: np.ndarray  # Lambda = U V, additive to the §6.3 minimum
    marker_sets: list  # list of index arrays, one per program
    donor_eligibility: np.ndarray  # n_donors x n_identity boolean
    manifest: dict

    @property
    def dataset_manifest_hash(self):
        return self.manifest["dataset_manifest_hash"]


def build_marker_sets(params, rng):
    """Private block per program plus a block shared with the cyclic neighbour.

    Program k owns `P_k` (private, size p) and `S_k` (shared, size s) where `S_k` also
    belongs to program k+1. So `M_k = P_k | S_k | S_{k-1}`, giving an overlap fraction of
    `2s / (p + 2s)`. Inverting for a target overlap `o`: `s = o*p / (2*(1-o))`.

    The private block is what guarantees rank: with >= 1 private marker per program the
    marker indicator matrix cannot be rank-deficient by the `M1+M2 = M3+M4` mechanism.
    """
    k = params.k_true
    p = max(1, int(round(params.private_marker_fraction * params.n_genes)))
    o = params.marker_overlap_fraction
    s = 0 if o == 0 else int(round(o * p / (2.0 * (1.0 - o))))

    needed = k * (p + s)
    if needed >= params.n_genes:
        raise ValueError(
            f"marker budget {needed} genes (K={k}, private={p}, shared={s}) leaves no "
            f"background genes out of {params.n_genes}. Lower private_marker_fraction."
        )

    order = rng.permutation(params.n_genes)
    private = [order[i * p : (i + 1) * p] for i in range(k)]
    base = k * p
    shared = [order[base + i * s : base + (i + 1) * s] for i in range(k)]

    marker_sets = []
    for i in range(k):
        parts = [private[i], shared[i], shared[(i - 1) % k]]
        marker_sets.append(np.unique(np.concatenate(parts)) if s else private[i])
    return marker_sets, private


def build_spectra(params, rng):
    """`V_kg  ∝  b_g * exp(sigma * zeta_kg) * (1 + lambda * 1[g in M_k])`, rows normalised.

    Three ingredients, each load-bearing:

    - `b_g`, a shared background profile, so programs **overlap** rather than being
      disjoint. A perfectly separable toy is explicitly not the test
      (`IMPLEMENTATION_PROMPT.md:129`).
    - `exp(sigma * zeta_kg)`, per-(program, gene) variation, so background genes have
      non-zero across-program variance. Without it, Fano-based HVG selection is a perfect
      oracle for the markers (module docstring, item 2).
    - `1 + lambda * 1[g in M_k]`, the discriminative direction that `lambda` scales.

    `b_g` is floored so that no gene's expected total falls low enough to give an all-zero
    column, which would make `gene_fano = gene_var/gene_mean` NaN (`cnmf.py:144`). The
    floor is applied before normalisation and re-checked on the realised `Lambda`.
    """
    g = params.n_genes
    marker_sets, private = build_marker_sets(params, rng)

    b = np.exp(rng.normal(0.0, params.background_log_sd, size=g))
    b /= b.sum()

    # Floor: a gene's expected total is roughly (total library) * b_g, so requiring
    # b_g >= min_expected / total_library keeps every column comfortably non-empty.
    total_library = params.mean_library * params.n_donors * params.cells_per_donor
    b_floor = params.min_expected_gene_counts / max(total_library, 1.0)
    b = np.maximum(b, b_floor)
    b /= b.sum()

    zeta = rng.normal(0.0, params.background_program_cv, size=(params.k_true, g))
    v = b[None, :] * np.exp(zeta)

    for k, markers in enumerate(marker_sets):
        v[k, markers] *= 1.0 + params.lambda_separation

    v /= v.sum(axis=1, keepdims=True)

    # Rank check before a single count is drawn. No value of lambda repairs a deficiency.
    #
    # The tolerance is relative and deliberately loose — 1e-8 of the largest singular
    # value, many orders above machine epsilon. `np.linalg.matrix_rank`'s default would
    # call a spectra matrix with condition number 1e12 "full rank", but such a matrix is
    # degenerate for NMF in every way that matters: the near-null direction is
    # unrecoverable from noisy counts, so the benchmark would be scoring a program the
    # data cannot carry.
    singular = np.linalg.svd(v, compute_uv=False)
    rank = int((singular > 1e-8 * singular[0]).sum())
    if rank != params.k_true:
        raise ContractViolation(
            f"true spectra have effective rank {rank}, expected {params.k_true} "
            f"(condition number {singular[0] / singular[-1]:.3e}). The marker-set design "
            "is degenerate; give every program a private marker."
        )
    for k, block in enumerate(private):
        if len(block) == 0:
            raise ContractViolation(f"program {k} has no private marker")

    return v, marker_sets, b


def _draw_donor_eligibility(params, rng):
    """Bernoulli(q_k) identity eligibility per donor — the §2.1 fix.

    Two repairs applied to the raw draw, both of which turn an uninformative dataset into
    a hard one rather than a broken one:

    - every donor keeps at least one eligible identity program, else it has no
      composition to draw at all
    - every program is eligible in at least one donor, else it is absent from the dataset
      entirely and `program_recovery_cosine_v1` would score a program that was never
      generated

    Calibrate toward *weakly represented, not absent*: a program absent from every
    training donor makes the fold uninformative rather than hard.
    """
    q = np.asarray(params.identity_eligibility, dtype=float)
    mask = rng.random((params.n_donors, params.n_identity)) < q[None, :]

    for d in range(params.n_donors):
        if not mask[d].any():
            mask[d, int(np.argmax(q))] = True
    for k in range(params.n_identity):
        if not mask[:, k].any():
            mask[rng.integers(params.n_donors), k] = True
    return mask


def _draw_usages(params, rng, eligibility, cells_per_donor, donor_depth):
    """Per-cell usages. Donor structure enters here and only here.

    A cell picks one identity from its donor's composition and carries continuous
    leakage on the others. Note that the *magnitude* of the dominant identity is not
    drawn separately: with a single dominant component, any magnitude is absorbed by the
    library rescaling below, so jittering it would change nothing. The variation that
    survives is which identity, how much leakage, and how much activity — which is the
    variation that matters.
    """
    n_cells = int(cells_per_donor.sum())
    k_id, k_act = params.n_identity, params.n_activity
    u = np.zeros((n_cells, params.k_true))

    pi_global = np.full(k_id, 1.0 / k_id)
    activity_eligible = (
        rng.random((params.n_donors, k_act)) < params.activity_donor_eligibility
        if k_act
        else np.zeros((params.n_donors, 0), dtype=bool)
    )

    donor_ids = []
    row = 0
    for d in range(params.n_donors):
        elig = eligibility[d]
        alpha = params.alpha_donor * pi_global[elig]
        pi_d = np.zeros(k_id)
        pi_d[elig] = rng.dirichlet(alpha)

        n_d = int(cells_per_donor[d])
        choice = rng.choice(k_id, size=n_d, p=pi_d)

        block = np.zeros((n_d, params.k_true))
        # Continuous leakage, not a constant floor: a constant would make every cell's
        # off-program usage identical and easier to subtract than real mixing.
        block[:, :k_id] = params.leakage * rng.exponential(1.0, size=(n_d, k_id))
        block[np.arange(n_d), choice] = 1.0

        for a in range(k_act):
            if not activity_eligible[d, a]:
                continue
            present = rng.random(n_d) < params.p_active
            sigma = np.sqrt(np.log1p(params.activity_cv**2))
            mag = params.activity_mean_share * np.exp(
                rng.normal(-0.5 * sigma**2, sigma, size=n_d)
            )
            block[:, k_id + a] = np.where(present, mag, 0.0)

        u[row : row + n_d] = block
        donor_ids.extend([f"donor_{d:03d}"] * n_d)
        row += n_d

    # Library sizes. Poisson expectation parameter, never a realised multinomial total.
    sigma_l = np.sqrt(np.log1p(params.cv_library**2))
    depth = np.repeat(donor_depth, cells_per_donor)
    lib = depth * params.mean_library * np.exp(rng.normal(-0.5 * sigma_l**2, sigma_l, n_cells))
    lib = np.maximum(lib, params.min_library)

    u *= (lib / u.sum(axis=1))[:, None]
    return u, donor_ids


def simulate(params, scenario_id, tier, seed, simulation_replicate=0):
    """One realisation. Returns a `SimulatedDataset`; writing is the caller's job.

    `simulation_replicate` changes the **whole** draw — spectra, donor eligibility,
    compositions and counts — not just the Poisson noise on a fixed structure. Two
    replicates are independent datasets from the same generative model, which is what
    "independent realisations" has to mean for a variability estimate to be honest.
    """
    import anndata as ad

    # SeedSequence over [seed, replicate] gives independent streams without the
    # correlation hazards of seed+replicate arithmetic.
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), int(simulation_replicate)]))

    v, marker_sets, _background = build_spectra(params, rng)
    eligibility = _draw_donor_eligibility(params, rng)

    if params.cells_per_donor_cv == 0:
        cells_per_donor = np.full(params.n_donors, params.cells_per_donor, dtype=int)
    else:
        sigma = np.sqrt(np.log1p(params.cells_per_donor_cv**2))
        draw = params.cells_per_donor * np.exp(
            rng.normal(-0.5 * sigma**2, sigma, params.n_donors)
        )
        cells_per_donor = np.maximum(np.round(draw), params.min_cells_per_donor).astype(int)

    sigma_d = np.sqrt(np.log1p(params.donor_depth_cv**2)) if params.donor_depth_cv else 0.0
    donor_depth = (
        np.exp(rng.normal(-0.5 * sigma_d**2, sigma_d, params.n_donors))
        if sigma_d
        else np.ones(params.n_donors)
    )

    u, donor_ids = _draw_usages(params, rng, eligibility, cells_per_donor, donor_depth)

    lam = u @ v
    counts = rng.poisson(lam).astype(np.int32)

    n_cells = counts.shape[0]
    cell_ids = [f"cell_{i:06d}" for i in range(n_cells)]
    # Pass the plain list, never a pd.Series: a Series carries its own RangeIndex and
    # pandas aligns it against `index=cell_ids`, silently producing an all-NaN column.
    # contract.check_counts catches it, which is why that check exists.
    obs = pd.DataFrame({"donor_id": donor_ids}, index=cell_ids)
    var = pd.DataFrame(index=[f"gene_{j:05d}" for j in range(params.n_genes)])
    obs.index.name, var.index.name = None, None
    adata = ad.AnnData(X=counts, obs=obs, var=var)

    manifest = _build_manifest(params, scenario_id, tier, seed, simulation_replicate)
    dataset = SimulatedDataset(
        adata=adata,
        true_spectra=v,
        true_usages=u,
        expected_counts=lam,
        marker_sets=marker_sets,
        donor_eligibility=eligibility,
        manifest=manifest,
    )

    # The contract is checked here, not at write time, so a malformed dataset never
    # reaches disk and never reaches a metric.
    check_dataset(adata, v, u)
    return dataset


def _build_manifest(params, scenario_id, tier, seed, simulation_replicate):
    """§6.6: hash over scenario id, tier, every generative parameter, the seed, the
    replicate index and the protocol version.

    The protocol version is in the payload deliberately: two datasets generated under
    different protocol versions must not collide even if every other input matches,
    because the contract their counts satisfy is not the same contract.
    """
    payload = {
        "scenario_id": scenario_id,
        "tier": tier,
        "parameters": params.as_dict(),
        "seed": int(seed),
        "simulation_replicate": int(simulation_replicate),
        "protocol_version": PROTOCOL_VERSION,
    }
    return {**payload, "dataset_manifest_hash": parameter_hash(payload)}
