from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from ui.components.source_viewer import SourceArtifact, render_source_artifact


def _state_defaults(item: Any) -> dict[str, Any]:
    payload = getattr(item, "proposed_payload", {}) or {}
    if isinstance(payload, dict):
        return payload
    return {"value": payload}


def _source_artifact_for(item: Any) -> SourceArtifact:
    provenance = getattr(item, "source_provenance", None)
    source_type = getattr(provenance, "source_type", "source")
    return SourceArtifact(
        label=getattr(item, "summary", getattr(item, "write_type", "Source")),
        source_type="pdf" if "filing" in source_type else source_type,
        path=getattr(provenance, "document_path", None),
        page_number=getattr(provenance, "page_number", None),
        cell_reference=getattr(provenance, "cell_reference", None),
        bounding_box=getattr(provenance, "bounding_box", None),
        raw_text=getattr(provenance, "raw_text", None),
    )


def _apply_action(action: str, item_id: str, edits: dict[str, Any]) -> None:
    st.session_state.setdefault("queue_actions", [])
    st.session_state["queue_actions"].append(
        {
            "item_id": item_id,
            "action": action,
            "edits": edits,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    st.toast(f"{action.title()} queued for {item_id}", icon="✅" if action == "accept" else "📝")


def render_queue_review(item: Any) -> None:
    if item is None:
        st.info("Select a queue item to review.")
        return

    tier = getattr(item, "tier", 3)
    title = getattr(item, "summary", getattr(item, "write_type", "Review item"))
    st.title(f"Tier {tier} Review")
    st.subheader(title)

    metrics = st.columns(4)
    metrics[0].metric("Confidence", f"{(getattr(item, 'confidence_score', 0) or 0):.2f}")
    metrics[1].metric("State", getattr(item, "state", "pending"))
    metrics[2].metric("Staleness", f"{max(0, (datetime.now(timezone.utc) - getattr(item, 'created_at', datetime.now(timezone.utc))).days)}d")
    metrics[3].metric("Verify flags", len(getattr(item, "verify_flags", []) or []))

    if tier == 2:
        left, right = st.columns([1.05, 1.0], gap="large")
        with left:
            st.markdown("### Source")
            render_source_artifact(_source_artifact_for(item), key_prefix=f"source-{getattr(item, 'id', 'item')}")
        with right:
            st.markdown("### Proposed writes")
            payload = _state_defaults(item)
            st.json(payload, expanded=True)
            edited = st.data_editor([{"field": k, "value": v} for k, v in payload.items()], use_container_width=True, hide_index=True, key=f"tier2-edit-{getattr(item, 'id', 'item')}")
    else:
        left, right = st.columns([1.05, 1.0], gap="large")
        with left:
            st.markdown("### Source")
            render_source_artifact(_source_artifact_for(item), key_prefix=f"source-{getattr(item, 'id', 'item')}")
        with right:
            st.markdown("### Proposed item")
            payload = _state_defaults(item)
            st.json(payload, expanded=True)
            edited = st.text_area("Edit in place", value=str(payload), height=420, key=f"tier3-edit-{getattr(item, 'id', 'item')}")

    shortcut_cols = st.columns(6)
    shortcut_cols[0].button("A Accept", on_click=_apply_action, args=("accept", str(getattr(item, "id", "")), {"payload": _state_defaults(item)}))
    shortcut_cols[1].button("R Reject", on_click=_apply_action, args=("reject", str(getattr(item, "id", "")), {}))
    shortcut_cols[2].button("E Edit", on_click=_apply_action, args=("edit", str(getattr(item, "id", "")), {"edited": True}))
    shortcut_cols[3].button("S Skip", on_click=_apply_action, args=("skip", str(getattr(item, "id", "")), {}))
    shortcut_cols[4].button("1", on_click=_apply_action, args=("rating_1", str(getattr(item, "id", "")), {}))
    shortcut_cols[5].button("2", on_click=_apply_action, args=("rating_2", str(getattr(item, "id", "")), {}))

    st.button("3", on_click=_apply_action, args=("rating_3", str(getattr(item, "id", "")), {}))
    st.caption("Keyboard shortcuts are handled by the browser; buttons mirror J/K, A/R/E/S, and 1/2/3.")

