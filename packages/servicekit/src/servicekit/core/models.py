"""Base ORM classes for SQLAlchemy models."""

import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from ulid import ULID

from .types import ULIDType


class Base(AsyncAttrs, DeclarativeBase):
    """Root declarative base with async support."""


class Entity(Base):
    """Optional base with common columns for your models."""

    __abstract__ = True

    id: Mapped[ULID] = mapped_column(ULIDType, primary_key=True, default=ULID)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
