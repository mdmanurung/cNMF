"""cnmfbench — benchmark harness for the incremental cNMF improvements programme.

Named to avoid any collision with the installed `cnmf` package, which this harness
imports and **never modifies**. `src/cnmf/**` is byte-identical to the pinned upstream
revision `5dbc5baaa0b9079b55bce554d801caa235a50457` and stays that way: features A, B
and C arrive as harness-side switches, not as edits to the algorithm.

The rules this package implements are frozen in `docs/planning/PROTOCOL.md`
(v1.2 — see D045; the sha256 recorded in `ablation_plan.yaml` is authoritative).
Where a docstring cites a section number it means that file.
"""

PROTOCOL_VERSION = "1.2"
HASH_CONVENTION_VERSION = 1
METRIC_DEFINITION_VERSION = 2

# Pinned upstream, per PROTOCOL.md header and DECISIONS.md D002.
UPSTREAM_CNMF_SHA = "5dbc5baaa0b9079b55bce554d801caa235a50457"

__all__ = [
    "PROTOCOL_VERSION",
    "HASH_CONVENTION_VERSION",
    "METRIC_DEFINITION_VERSION",
    "UPSTREAM_CNMF_SHA",
]
