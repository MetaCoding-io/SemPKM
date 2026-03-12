"""Shared pytest fixtures for SemPKM backend tests.

SECRET_KEY is set before any app imports to prevent _get_secret_key()
from writing files to disk during test collection.
"""

import os

# Must be set before any app.* imports to satisfy settings validation
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"

import pytest  # noqa: E402

from app.auth import tokens  # noqa: E402


@pytest.fixture(autouse=True)
def reset_serializer():
    """Reset the token serializer singleton after each test.

    Prevents one test's serializer state from leaking into another.
    """
    yield
    tokens._serializer = None


@pytest.fixture
def tmp_key_dir(tmp_path):
    """Provide a temporary directory for token file operations."""
    return tmp_path
