"""Query financial records by company, period, metric, or type."""
from __future__ import annotations

import time

from sqlalchemy import select

from core.tools._runtime import ensure_company_exists, log_tool_call, session_scope
from core.tools.schemas import FinancialOut, FinancialQueryIn
from core.types.sqlalchemy_models import Financial


def query_financials(payload: FinancialQueryIn, session=None) -> list[FinancialOut]:
    started = time.time()
    with session_scope(session) as db:
        ensure_company_exists(db, payload.company_id)
        stmt = select(Financial).where(Financial.company_id == payload.company_id, Financial.is_active.is_(True))
        if payload.period_label:
            stmt = stmt.where(Financial.period_label == payload.period_label)
        if payload.metric:
            stmt = stmt.where(Financial.metric == payload.metric)
        if payload.type:
            stmt = stmt.where(Financial.type == payload.type)
        records = db.scalars(stmt.order_by(Financial.period_end_date.desc(), Financial.metric)).all()
        result = [FinancialOut.model_validate(item) for item in records]
        log_tool_call(db, "query_financials", payload.model_dump(mode="json"), [r.model_dump(mode="json") for r in result], started)
        return result
