"""Reuse the host application's Qt project fixtures."""

from manuskript.tests.conftest import (  # noqa: F401
    MW,
    MWEmptyProject,
    MWSampleProject,
    closeProjectAfterTests,
)
