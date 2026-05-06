"""List companies or fetch a single company.

Use this tool for company metadata lookups.
"""

from __future__ import annotations

import time

from sqlalchemy import select

from core.tools._runtime import log_tool_call, session_scope
from core.tools.schemas import CompanyOut, CompanyQueryIn
from core.types.sqlalchemy_models import Company


def query_companies(
    payload: CompanyQueryIn,
    session=None,
) -> list[CompanyOut] | CompanyOut:
    started = time.time()
    with session_scope(session) as db:
        if payload.company_id is not None:
            company = db.scalar(select(Company).where(Company.id == payload.company_id))
            if company is None:
                raise LookupError(f"company not found: {payload.company_id}")
            result = CompanyOut.model_validate(company)
            log_tool_call(db, "query_companies", payload.model_dump(mode="json"), result.model_dump(mode="json"), started)
            return result
        companies = db.scalars(select(Company).order_by(Company.display_name)).all()
        result = [CompanyOut.model_validate(item) for item in companies]
        log_tool_call(db, "query_companies", payload.model_dump(mode="json"), [r.model_dump(mode="json") for r in result], started)
        return result
