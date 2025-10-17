"""Global registry for Python task functions."""

from collections.abc import Callable
from typing import Any


class TaskRegistry:
    """Global registry for Python task functions."""

    _registry: dict[str, Callable[..., Any]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a task function with support for type-based dependency injection.

        Task functions can receive parameters from two sources:
        1. User parameters: Provided via task.parameters (primitives, dicts, lists)
        2. Framework injections: Automatically injected based on type hints

        Injectable framework types:
        - AsyncSession: SQLAlchemy async database session
        - Database: chapkit Database instance
        - ArtifactManager: Artifact management service
        - JobScheduler: Job scheduling service

        Parameters are matched by type hints. User parameters must use primitive types
        or generic types (str, int, dict, pd.DataFrame, etc.). Framework types are
        automatically injected if present in the function signature.

        Usage:
            @TaskRegistry.register("my_task")
            async def my_task(
                input_text: str,  # From task.parameters
                session: AsyncSession,  # Injected by framework
            ) -> dict:
                # Use session for database operations
                return {"status": "success"}

            @TaskRegistry.register("data_task")
            def process_data(
                data: pd.DataFrame,  # From task.parameters
                artifact_manager: ArtifactManager,  # Injected by framework
            ) -> dict:
                # Process data and save artifacts
                return {"processed": len(data)}
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if name in cls._registry:
                raise ValueError(f"Task '{name}' already registered")
            cls._registry[name] = func
            return func

        return decorator

    @classmethod
    def register_function(cls, name: str, func: Callable[..., Any]) -> None:
        """Imperatively register a task function.

        Usage:
            TaskRegistry.register_function("my_task", my_task_function)
        """
        if name in cls._registry:
            raise ValueError(f"Task '{name}' already registered")
        cls._registry[name] = func

    @classmethod
    def get(cls, name: str) -> Callable[..., Any]:
        """Retrieve a registered task function."""
        if name not in cls._registry:
            raise KeyError(f"Task '{name}' not found in registry")
        return cls._registry[name]

    @classmethod
    def list_all(cls) -> list[str]:
        """List all registered task names."""
        return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered tasks (useful for testing)."""
        cls._registry.clear()
