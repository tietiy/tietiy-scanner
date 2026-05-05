"""pytest configuration for shadow_ops tests.

Registers custom markers used by tests in this directory.
"""


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "network: marks tests that require network access (yfinance / external APIs). "
        "Skip with `pytest -m \"not network\"`.",
    )
