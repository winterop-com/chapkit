"""ML module placeholder - functionality moved to chapkit package.

This stub exists only for backwards compatibility and type checking.
The actual ML implementation is in the chapkit package.
"""

from typing import Any, Protocol, runtime_checkable

__all__ = ["MLManager", "MLRouter", "ModelRunnerProtocol"]


@runtime_checkable
class ModelRunnerProtocol(Protocol):
    """Protocol for ML model runners (stub)."""

    pass


class MLManager:
    """ML manager stub - use chapkit package for ML functionality."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize ML manager stub."""
        raise NotImplementedError(
            "ML functionality has been moved to the chapkit package. Please install and use chapkit for ML operations."
        )


class MLRouter:
    """ML router stub - use chapkit package for ML functionality."""

    @staticmethod
    def create(*args: Any, **kwargs: Any) -> Any:
        """Create ML router stub."""
        raise NotImplementedError(
            "ML functionality has been moved to the chapkit package. Please install and use chapkit for ML operations."
        )
