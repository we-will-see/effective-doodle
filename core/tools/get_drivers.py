"""Fetch company drivers."""
from __future__ import annotations

import time

from sqlalchemy import select

from core.tools._runtime import ensure_company_exists, log_tool_call, session_scope
from core.tools.schemas import CompanyQueryIn, DriverOut
from core.types.sqlalchemy_models import Driver


def get_drivers(payload: CompanyQueryIn, session=None) -> list[DriverOut]:
    started = time.time()
    with session_scope(session) as db:
        ensure_company_exists(db, payload.company_id)
        records = db.scalars(
            select(Driver).where(Driver.company_id == payload.company_id, Driver.is_active.is_(True)).order_by(Driver.created_at.desc())
        ).all()
        result = [DriverOut.model_validate(item) for item in records]
        log_tool_call(db, "get_drivers", payload.model_dump(mode="json"), [r.model_dump(mode="json") for r in result], started)
        return result
