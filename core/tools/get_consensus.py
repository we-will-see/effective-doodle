"""Fetch Visible Alpha consensus snapshots."""
from __future__ import annotations

import time

from sqlalchemy import select

from core.tools._runtime import ensure_company_exists, log_tool_call, session_scope
from core.tools.schemas import ConsensusOut, ConsensusQueryIn
from core.types.sqlalchemy_models import ConsensusPull


def get_consensus(payload: ConsensusQueryIn, session=None) -> list[ConsensusOut]:
    started = time.time()
    with session_scope(session) as db:
        ensure_company_exists(db, payload.company_id)
        records = db.scalars(
            select(ConsensusPull).where(ConsensusPull.company_id == payload.company_id).order_by(ConsensusPull.pulled_at.desc())
        ).all()
        if payload.period_label:
            records = [
                record
                for record in records
                if payload.period_label in str(record.raw_payload.get("period_label", ""))
                or payload.period_label in str(record.raw_payload)
            ]
        result = [ConsensusOut.model_validate(item) for item in records]
        log_tool_call(db, "get_consensus", payload.model_dump(mode="json"), [r.model_dump(mode="json") for r in result], started)
        return result
