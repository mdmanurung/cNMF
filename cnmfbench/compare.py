"""Artifact comparison, and the two obligations D004 placed on P0-04.

D004 chose relative Frobenius error at `1e-5` over upstream's absolute SSE budget, and
marked itself **PROVISIONAL** with two things due "at P0-04, not after":

> (i) confirm or revise the 1e-5 value against corruption sensitivity, and (ii) set the
> absolute floor for all-zero/near-zero artifacts **before** the first such artifact
> appears, since choosing it afterwards would be choosing it against a known case.

Both are discharged here. (ii) is the one with a deadline attached: no near-zero artifact has
appeared yet, so the floor below is being set against *no* known case, which is the only
condition under which choosing it is honest. Written now rather than when it is first needed.

**The floor: `1e-12` on the Frobenius norm.** An artifact whose entire norm is below it is
numerically zero for every quantity this pipeline produces — spectra rows sum to 1, usages
are O(1), counts are O(1e3) — and the value sits ~1e4 above float64 epsilon (2.2e-16), far
enough to be robust to accumulation and far below anything that could carry signal. When the
reference is at or below the floor, the comparison switches from relative to **absolute**
Frobenius error against the same floor, because a relative error is undefined there and
"undefined" must not read as "passed".
"""
import dataclasses

import numpy as np

__all__ = [
    "RELATIVE_TOLERANCE",
    "NEAR_ZERO_FLOOR",
    "Comparison",
    "compare_artifacts",
]

# D004's value, confirmed rather than revised at P0-04. See `test_compare.py`, which measures
# the separation this claim rests on.
RELATIVE_TOLERANCE = 1e-5

# D004 obligation (ii), set before any near-zero artifact exists. See module docstring.
NEAR_ZERO_FLOOR = 1e-12


@dataclasses.dataclass(frozen=True)
class Comparison:
    relative_frobenius: float  # nan when the near-zero branch was used
    absolute_frobenius: float
    bitwise_identical: bool
    near_zero_branch: bool
    agrees: bool


def compare_artifacts(reference, test):
    """Compare two arrays under D004's rule.

    Bitwise identity is reported separately from agreement, because D004 requires it: several
    artifacts in this pipeline *are* bitwise identical (`norm_counts`, `consensus_spectra`),
    and collapsing that into a tolerance pass would discard the stronger claim.

    This is a **same-environment** tolerance. D004 makes no bitwise claim across BLAS
    implementations, library versions, thread counts or platforms, and neither does this.
    """
    reference = np.asarray(reference, dtype=float)
    test = np.asarray(test, dtype=float)
    if reference.shape != test.shape:
        raise ValueError(
            f"shapes differ: {reference.shape} vs {test.shape}. A shape change is a "
            "structural difference, not a numerical one, so it is not given a tolerance."
        )
    if not np.all(np.isfinite(reference)) or not np.all(np.isfinite(test)):
        raise ValueError("non-finite entries present; comparison is undefined")

    absolute = float(np.linalg.norm(reference - test))
    bitwise = bool(np.array_equal(reference, test))
    ref_norm = float(np.linalg.norm(reference))

    if ref_norm <= NEAR_ZERO_FLOOR:
        # Relative error is undefined here. Falling back to absolute keeps the check live;
        # returning "agrees" on a division by zero would make the near-zero case the easiest
        # one to pass, which is backwards.
        return Comparison(
            relative_frobenius=float("nan"), absolute_frobenius=absolute,
            bitwise_identical=bitwise, near_zero_branch=True,
            agrees=bool(absolute <= NEAR_ZERO_FLOOR),
        )

    relative = absolute / ref_norm
    return Comparison(
        relative_frobenius=relative, absolute_frobenius=absolute,
        bitwise_identical=bitwise, near_zero_branch=False,
        agrees=bool(relative <= RELATIVE_TOLERANCE),
    )
