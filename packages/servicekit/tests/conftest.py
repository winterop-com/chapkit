"""Test configuration and shared fixtures."""

from servicekit import BaseConfig


class DemoConfig(BaseConfig):
    """Concrete config schema for testing."""

    x: int
    y: int
    z: int
    tags: list[str]
