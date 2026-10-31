"""Classify existing tests without changing their implementation."""
import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("integration") is None:
            item.add_marker(pytest.mark.unit)
