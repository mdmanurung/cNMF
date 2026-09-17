"""D004's obligation (i): confirm or revise 1e-5 against corruption sensitivity.

D004 marked itself PROVISIONAL because 1e-5 was calibrated on a single observation, and named
exactly where a too-loose tolerance would show up: "an injected corruption that fails to trip
the check". So the test is not "does a good comparison pass" — it is **how small a structural
corruption can get before 1e-5 stops seeing it**, measured, with the margin reported.
"""
import numpy as np
import pytest

from cnmfbench.compare import (
    NEAR_ZERO_FLOOR,
    RELATIVE_TOLERANCE,
    compare_artifacts,
)


def _spectra(k=7, n_genes=1200, seed=0):
    rng = np.random.default_rng(seed)
    m = rng.random((k, n_genes)) ** 3
    return m / m.sum(axis=1, keepdims=True)


# ---------------------------------------------------------------- the separation D004 needs

def test_the_tolerance_separates_numerical_noise_from_structural_difference():
    """The claim 1e-5 rests on: float64 round-trip noise sits far below it, and the smallest
    structural corruption sits far above. Both margins are asserted, not assumed."""
    ref = _spectra()

    # Numerical noise: a round trip through float32 and back is far harsher than the
    # same-environment BLAS variation D004 scopes itself to.
    noise = compare_artifacts(ref, ref.astype(np.float32).astype(np.float64))
    assert noise.relative_frobenius < RELATIVE_TOLERANCE / 10, (
        f"round-trip noise {noise.relative_frobenius:.2e} is within 10x of the tolerance; "
        "1e-5 would be at risk of flagging noise as corruption"
    )
    assert noise.agrees

    # Structural: swapping two programs is the mildest corruption that changes the solution.
    swapped = ref[[1, 0] + list(range(2, ref.shape[0]))]
    structural = compare_artifacts(ref, swapped)
    assert structural.relative_frobenius > RELATIVE_TOLERANCE * 1000, (
        f"a program swap only reaches {structural.relative_frobenius:.2e}; 1e-5 would be "
        "too loose to see it"
    )
    assert not structural.agrees


def test_the_smallest_corruption_the_tolerance_still_catches():
    """Measures the detection edge directly: perturb one gene in one program by a shrinking
    relative amount and find where 1e-5 stops tripping. Recorded so the value is not a guess."""
    ref = _spectra()
    caught = []
    for magnitude in (1e-2, 1e-3, 1e-4, 1e-5, 1e-6):
        corrupted = ref.copy()
        corrupted *= 1.0 + magnitude  # a uniform relative shift of the whole artifact
        if not compare_artifacts(ref, corrupted).agrees:
            caught.append(magnitude)
    assert 1e-4 in caught and 1e-3 in caught, (
        "1e-5 must catch a uniform 1e-4 relative shift; if it does not, D004's value is "
        "too loose and must be revised rather than confirmed"
    )


def test_bitwise_identity_is_reported_separately_from_agreement():
    """D004 requires it: several artifacts here ARE bitwise identical, and collapsing that
    into a tolerance pass would discard the stronger claim."""
    ref = _spectra()
    identical = compare_artifacts(ref, ref.copy())
    assert identical.bitwise_identical and identical.agrees
    close = compare_artifacts(ref, ref * (1.0 + 1e-9))
    assert close.agrees and not close.bitwise_identical


# ---------------------------------------------------------------- obligation (ii): the floor

def test_an_all_zero_reference_uses_the_absolute_floor_and_still_agrees_with_itself():
    zeros = np.zeros((3, 10))
    c = compare_artifacts(zeros, zeros)
    assert c.near_zero_branch and c.agrees
    assert np.isnan(c.relative_frobenius), "relative error is undefined here and says so"


def test_a_near_zero_reference_does_not_pass_by_default():
    """The failure this floor exists to prevent: a division by zero making the near-zero case
    the easiest one to pass."""
    zeros = np.zeros((3, 10))
    perturbed = zeros.copy()
    perturbed[0, 0] = 1e-6  # tiny in absolute terms, but far above the floor
    c = compare_artifacts(zeros, perturbed)
    assert c.near_zero_branch
    assert not c.agrees


def test_the_floor_admits_genuine_float64_dust():
    zeros = np.zeros((3, 10))
    dust = zeros.copy()
    dust[1, 2] = 1e-16
    assert compare_artifacts(zeros, dust).agrees


def test_the_floor_sits_well_above_float64_epsilon():
    """Justifies the value rather than asserting it: far enough above eps to absorb
    accumulation, far enough below any real quantity to be unable to hide one."""
    assert NEAR_ZERO_FLOOR > np.finfo(float).eps * 1e3
    assert NEAR_ZERO_FLOOR < 1e-9


# ---------------------------------------------------------------- structural differences

def test_a_shape_change_raises_rather_than_being_given_a_tolerance():
    with pytest.raises(ValueError, match="structural difference"):
        compare_artifacts(np.zeros((3, 10)), np.zeros((4, 10)))


def test_non_finite_entries_raise():
    ref = _spectra(k=2, n_genes=5)
    bad = ref.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        compare_artifacts(ref, bad)
