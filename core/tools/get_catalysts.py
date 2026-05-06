"""Fetch upcoming or recent catalysts."""
from __future__ import annotations

import time

from sqlalchemy import select

from core.tools._runtime import ensure_company_exists, log_tool_call, session_scope
from core.tools.schemas import CatalystOut, CatalystQueryIn
from core.types.sqlalchemy_models import Catalyst


def get_catalysts(payload: CatalystQueryIn, session=None) -> list[CatalystOut]:
    started = time.time()
    with session_scope(session) as db:
        ensure_company_exists(db, payload.company_id)
        stmt = select(Catalyst).where(Catalyst.company_id == payload.company_id, Catalyst.is_active.is_(True))
        if payload.date_range:
            if payload.date_range.start_date:
                stmt = stmt.where(Catalyst.expected_date >= payload.date_range.start_date)
            if payload.date_range.end_date:
                stmt = stmt.where(Catalyst.expected_date <= payload.date_range.end_date)
        records = db.scalars(stmt.order_by(Catalyst.expected_date.asc().nulls_last())).all()
        result = [CatalystOut.model_validate(item) for item in records]
        log_tool_call(db, "get_catalysts", payload.model_dump(mode="json"), [r.model_dump(mode="json") for r in result], started)
        return result
