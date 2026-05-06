"""Search filing metadata and text for a company."""
from __future__ import annotations

import time

from sqlalchemy import or_, select

from core.tools._runtime import log_tool_call, session_scope
from core.tools.schemas import DateRange, FilingOut, FilingSearchIn
from core.types.sqlalchemy_models import Document


def search_filings(payload: FilingSearchIn, session=None) -> list[FilingOut]:
    started = time.time()
    with session_scope(session) as db:
        stmt = select(Document).where(
            or_(
                Document.filing_title.ilike(f"%{payload.query}%"),
                Document.document_type.ilike(f"%{payload.query}%"),
                Document.document_subtype.ilike(f"%{payload.query}%"),
                Document.raw_text.ilike(f"%{payload.query}%"),
                Document.parsed_text.ilike(f"%{payload.query}%"),
            )
        )
        if payload.company_id is not None:
            stmt = stmt.where(Document.company_id == payload.company_id)
        if payload.date_range:
            if payload.date_range.start_date:
                stmt = stmt.where(Document.filed_at >= payload.date_range.start_date)
            if payload.date_range.end_date:
                stmt = stmt.where(Document.filed_at <= payload.date_range.end_date)
        records = db.scalars(stmt.order_by(Document.filed_at.desc())).all()
        result = [FilingOut.model_validate(item) for item in records]
        log_tool_call(db, "search_filings", payload.model_dump(mode="json"), [r.model_dump(mode="json") for r in result], started)
        return result
