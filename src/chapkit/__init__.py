"""Chapkit - vertical slice architecture with core framework and features."""

# Core framework
from chapkit.core import (
    Base,
    BaseManager,
    BaseRepository,
    Database,
    Entity,
    EntityIn,
    EntityOut,
    Manager,
    Repository,
    ULIDType,
)

# Artifact feature
from chapkit.modules.artifact import (
    Artifact,
    ArtifactHierarchy,
    ArtifactIn,
    ArtifactManager,
    ArtifactOut,
    ArtifactRepository,
    ArtifactTreeNode,
    PandasDataFrame,
)

# Config feature
from chapkit.modules.config import (
    BaseConfig,
    Config,
    ConfigIn,
    ConfigManager,
    ConfigOut,
    ConfigRepository,
)

# Task feature
from chapkit.modules.task import Task, TaskIn, TaskManager, TaskOut, TaskRepository

__all__ = [
    # Core framework
    "Database",
    "Repository",
    "BaseRepository",
    "Manager",
    "BaseManager",
    "Base",
    "Entity",
    "ULIDType",
    "EntityIn",
    "EntityOut",
    # Config feature
    "BaseConfig",
    "Config",
    "ConfigIn",
    "ConfigOut",
    "ConfigRepository",
    "ConfigManager",
    # Artifact feature
    "Artifact",
    "ArtifactHierarchy",
    "ArtifactIn",
    "ArtifactOut",
    "ArtifactTreeNode",
    "PandasDataFrame",
    "ArtifactRepository",
    "ArtifactManager",
    # Task feature
    "Task",
    "TaskIn",
    "TaskOut",
    "TaskRepository",
    "TaskManager",
]
