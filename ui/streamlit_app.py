from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import streamlit as st

from ui.pages.queue_list import render_queue_list
from ui.pages.queue_review import render_queue_review


@dataclass
class DemoQueueItem:
    id: str
    tier: int
    priority: int
    state: str
    summary: str
    created_at: datetime
    confidence_score: float
    verify_flags: list[str]
    proposed_payload: dict[str, Any]
    source_provenance: Any = None


def require_ssh_access() -> None:
    st.set_page_config(page_title="AgentOS Review Queue", layout="wide")
    st.session_state.setdefault("ssh_authenticated", True)
    if not st.session_state["ssh_authenticated"]:
        st.stop()


def load_daily_briefing() -> dict[str, Any]:
    return {
        "queue_depth": 14,
        "tier_2_bundles": 6,
        "tier_3_items": 2,
        "stale_items": 1,
        "projected_clearance_minutes": 42,
        "notes": [
            "Tier 2 bundle depth is within the 5 minute review target.",
            "One Tier 3 item is stale and should be handled first.",
        ],
    }


def load_queue_items() -> list[DemoQueueItem]:
    now = datetime.now(timezone.utc)
    return [
        DemoQueueItem(
            id="rq-001",
            tier=2,
            priority=98,
            state="pending",
            summary="LAURUS 4QFY26 classification bundle",
            created_at=now - timedelta(hours=3),
            confidence_score=0.91,
            verify_flags=["[VERIFY] page mismatch", "[VERIFY] numeric delta"],
            proposed_payload={"target_table": "coverage.financials", "rows": 23},
        ),
        DemoQueueItem(
            id="rq-002",
            tier=3,
            priority=84,
            state="under_review",
            summary="Estimate revision for EBITDA",
            created_at=now - timedelta(days=2),
            confidence_score=0.77,
            verify_flags=["[VERIFY] threshold crossed"],
            proposed_payload={"metric": "ebitda", "value": 182.5, "unit": "crore"},
        ),
    ]


def render_daily_briefing_sidebar(briefing: dict[str, Any]) -> None:
    st.sidebar.header("Daily Briefing")
    st.sidebar.metric("Queue depth", briefing["queue_depth"])
    st.sidebar.metric("Tier 2 bundles", briefing["tier_2_bundles"])
    st.sidebar.metric("Tier 3 items", briefing["tier_3_items"])
    st.sidebar.metric("Projected clear", f"{briefing['projected_clearance_minutes']} min")
    st.sidebar.caption("SSH tunnel access is the intended authentication boundary.")
    for note in briefing["notes"]:
        st.sidebar.write(f"- {note}")


def main() -> None:
    require_ssh_access()
    st.title("AgentOS Review Queue")
    st.caption("Primary analyst review surface for Tier 2 bundles and Tier 3 line items.")

    briefing = load_daily_briefing()
    render_daily_briefing_sidebar(briefing)

    items = load_queue_items()
    selected = render_queue_list(items)

    selected_item = next((item for item in items if str(item.id) == selected["id"]), items[0] if items else None)

    if selected_item:
        st.divider()
        render_queue_review(selected_item)


if __name__ == "__main__":
    main()

