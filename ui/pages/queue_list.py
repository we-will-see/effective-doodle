from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import streamlit as st


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return None


def _staleness_days(item: Any) -> int:
    created_at = _as_datetime(getattr(item, "created_at", None))
    if not created_at:
        return 0
    return max(0, (datetime.now(timezone.utc) - created_at).days)


def render_queue_list(items: Iterable[Any]) -> Any:
    st.title("Approval Queue")
    st.caption("Queue list view for tier, priority, and staleness.")

    items = list(items)
    tiers = sorted({getattr(item, "tier", 0) for item in items if getattr(item, "tier", None) is not None})
    statuses = sorted({getattr(item, "state", "") for item in items if getattr(item, "state", None)})

    c1, c2, c3 = st.columns(3)
    selected_tiers = c1.multiselect("Tier", tiers, default=tiers)
    selected_statuses = c2.multiselect("Status", statuses, default=statuses)
    sort_by = c3.selectbox("Sort by", ["Priority", "Staleness", "Created at"])

    filtered = [
        item
        for item in items
        if (not selected_tiers or getattr(item, "tier", None) in selected_tiers)
        and (not selected_statuses or getattr(item, "state", None) in selected_statuses)
    ]

    if sort_by == "Priority":
        filtered.sort(key=lambda item: (-(getattr(item, "priority", 0) or 0), _staleness_days(item)))
    elif sort_by == "Staleness":
        filtered.sort(key=lambda item: (-_staleness_days(item), -(getattr(item, "priority", 0) or 0)))
    else:
        filtered.sort(key=lambda item: getattr(item, "created_at", datetime.min))

    rows = []
    for item in filtered:
        rows.append(
            {
                "id": str(getattr(item, "id", "")),
                "tier": getattr(item, "tier", ""),
                "priority": getattr(item, "priority", ""),
                "staleness_days": _staleness_days(item),
                "state": getattr(item, "state", ""),
                "summary": getattr(item, "summary", getattr(item, "write_type", "Untitled")),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

    if rows:
        selected = st.selectbox("Open item", rows, format_func=lambda row: f"Tier {row['tier']} · {row['summary']}")
        return selected
    st.info("No queue items match the current filters.")
    return None

