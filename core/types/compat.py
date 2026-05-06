"""Database compatibility layer for PostgreSQL vs SQLite testing."""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Detect if we're running with SQLite (for tests)
_uses_sqlite = os.environ.get("TEST_DATABASE_URL", "").startswith("sqlite")

# Import types with fallback
if TYPE_CHECKING:
    from sqlalchemy.dialects.postgresql import JSONB as _JSONB, UUID as _UUID
    from sqlalchemy.types import TypeEngine
else:
    try:
        from sqlalchemy.dialects.postgresql import JSONB as _JSONB, UUID as _UUID
    except ImportError:
        _JSONB = None
        _UUID = None


class JSONB:
    """Compatibility wrapper for JSONB type."""
    
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        
    def __call__(self):
        # Return appropriate type based on dialect
        from sqlalchemy.types import JSON
        if _uses_sqlite:
            return JSON()
        return _JSONB(*self._args, **self._kwargs)


class UUID:
    """Compatibility wrapper for UUID type."""
    
    def __init__(self, as_uuid: bool = True):
        self.as_uuid = as_uuid
        
    def __call__(self):
        from sqlalchemy.types import String
        if _uses_sqlite:
            return String(36)
        return _UUID(as_uuid=self.as_uuid)


def get_schema(base_name: str) -> dict:
    """Return schema dictionary or empty dict for SQLite."""
    if _uses_sqlite:
        return {}
    return {"schema": base_name}


def get_server_default(default_name: str):
    """Return appropriate server default based on dialect."""
    if _uses_sqlite:
        if default_name == "now":
            return func.current_timestamp()
        if default_name == "gen_random_uuid":
            return None  # SQLite generates UUIDs in Python
        return text(f"'{default_name}'")
    return text(f"{default_name}()")


def fk(table: str, schema: str | None = None) -> str:
    """Return foreign key reference, optionally stripping schema for SQLite."""
    if _uses_sqlite:
        return table.lstrip(f"{schema}.") if schema else table
    return f"{schema}.{table}" if schema else table


# Re-export replaced symbols
from decimal import Decimal as _Decimal
from typing import Any as _Any
from typing import Optional as _Optional

__all__ = [
    "UUID",
    "JSONB",
    "get_schema",
    "get_server_default",
    "fk",
]
