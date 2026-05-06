"""Fetch corporate actions for a company."""
from __future__ import annotations

import time

from sqlalchemy import select

from core.tools._runtime import ensure_company_exists, log_tool_call, session_scope
from core.tools.schemas import CorporateActionOut, CorporateActionQueryIn
from core.types.sqlalchemy_models import CorporateAction


def get_corporate_actions(payload: CorporateActionQueryIn, session=None) -> list[CorporateActionOut]:
    started = time.time()
    with session_scope(session) as db:
        ensure_company_exists(db, payload.company_id)
        stmt = select(CorporateAction).where(CorporateAction.company_id == payload.company_id)
        if payload.date_range:
            if payload.date_range.start_date:
                stmt = stmt.where(CorporateAction.effective_date >= payload.date_range.start_date)
            if payload.date_range.end_date:
                stmt = stmt.where(CorporateAction.effective_date <= payload.date_range.end_date)
        records = db.scalars(stmt.order_by(CorporateAction.effective_date.desc())).all()
        result = [CorporateActionOut.model_validate(item) for item in records]
        log_tool_call(db, "get_corporate_actions", payload.model_dump(mode="json"), [r.model_dump(mode="json") for r in result], started)
        return result
