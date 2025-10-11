"""Task ORM model for reusable command templates."""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text

from chapkit.core.models import Entity


class Task(Entity):
    """ORM model for reusable task templates containing commands to execute."""

    __tablename__ = "tasks"

    command: Mapped[str] = mapped_column(Text, nullable=False)
