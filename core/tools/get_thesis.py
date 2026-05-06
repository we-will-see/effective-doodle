"""Fetch the active thesis metadata for a company."""
from __future__ import annotations

import time

from sqlalchemy import select

from core.tools._runtime import ensure_company_exists, log_tool_call, session_scope
from core.tools.schemas import CompanyQueryIn, ThesisOut
from core.types.sqlalchemy_models import ThesisMeta


def get_thesis(payload: CompanyQueryIn, session=None) -> ThesisOut:
    started = time.time()
    with session_scope(session) as db:
        ensure_company_exists(db, payload.company_id)
        thesis = db.scalar(
            select(ThesisMeta).where(ThesisMeta.company_id == payload.company_id, ThesisMeta.status == "active")
        )
        if thesis is None:
            raise LookupError(f"active thesis not found for company: {payload.company_id}")
        result = ThesisOut.model_validate(thesis)
        log_tool_call(db, "get_thesis", payload.model_dump(mode="json"), result.model_dump(mode="json"), started)
        return result
