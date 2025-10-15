"""Servicekit - async SQLAlchemy database library with FastAPI integration."""

# Core framework
from servicekit.core import (
    Base,
    BaseManager,
    BaseRepository,
    Database,
    Entity,
    EntityIn,
    EntityOut,
    Manager,
    Repository,
    SqliteDatabase,
    SqliteDatabaseBuilder,
    ULIDType,
)

# Artifact feature
from servicekit.modules.artifact import (
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
from servicekit.modules.config import (
    BaseConfig,
    Config,
    ConfigIn,
    ConfigManager,
    ConfigOut,
    ConfigRepository,
)

# Task feature
from servicekit.modules.task import Task, TaskIn, TaskManager, TaskOut, TaskRepository

__version__ = "0.1.0"

__all__ = [
    # Core framework
    "Database",
    "SqliteDatabase",
    "SqliteDatabaseBuilder",
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
    # Version
    "__version__",
]
