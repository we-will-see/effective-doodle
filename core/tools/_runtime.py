from __future__ import annotations

import os
import time
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator, TypeVar
from uuid import UUID

from sqlalchemy import create_engine, func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.types.sqlalchemy_models import ToolCall, WorkflowRun

T = TypeVar("T")

_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = os.getenv("AGENTOS_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite:///:memory:"
        _ENGINE = create_engine(url, future=True)
    return _ENGINE


def get_session() -> Session:
    factory = sessionmaker(bind=get_engine(), future=True)
    return factory()


@contextmanager
def session_scope(session: Session | None = None) -> Iterator[Session]:
    own = session is None
    session = session or get_session()
    try:
        yield session
        if own:
            session.commit()
    except Exception:
        if own:
            session.rollback()
        raise
    finally:
        if own:
            session.close()


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def log_tool_call(
    session: Session,
    tool_name: str,
    arguments: dict[str, Any],
    result: Any,
    started_at: float,
    status: str = "ok",
    error_details: str | None = None,
) -> None:
    workflow_run_id = os.getenv("AGENTOS_WORKFLOW_RUN_ID")
    if not workflow_run_id:
        return
    workflow_run_uuid = UUID(workflow_run_id)
    call_index = session.scalar(
        select(func.coalesce(func.max(ToolCall.call_index), -1) + 1).where(
            ToolCall.workflow_run_id == workflow_run_uuid
        )
    )
    session.add(
        ToolCall(
            workflow_run_id=workflow_run_uuid,
            call_index=int(call_index or 0),
            tool_name=tool_name,
            arguments=_json_safe(arguments),
            result_summary=_json_safe(result),
            status=status,
            error_details=error_details,
            duration_ms=int((time.time() - started_at) * 1000),
        )
    )


def ensure_company_exists(session: Session, company_id: Any) -> None:
    from core.types.sqlalchemy_models import Company

    exists = session.scalar(select(Company.id).where(Company.id == company_id))
    if exists is None:
        raise LookupError(f"company not found: {company_id}")
