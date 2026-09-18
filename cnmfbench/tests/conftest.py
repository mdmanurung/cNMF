"""Harness-side pytest configuration.

The marker is registered here rather than in `pyproject.toml` because that file is
upstream's and must stay byte-identical to `5dbc5ba` — it is one of the four paths the
standing check `git diff 5dbc5ba..HEAD -- src/ tests/ setup.py pyproject.toml` requires to
come back empty.
"""


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: needs one or more real cNMF fits. Deselect with -m 'not slow'.",
    )
