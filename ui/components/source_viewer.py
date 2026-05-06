from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import streamlit as st


@dataclass(frozen=True)
class SourceArtifact:
    label: str
    source_type: str
    path: str | None = None
    page_number: int | None = None
    cell_reference: str | None = None
    bounding_box: dict[str, Any] | None = None
    raw_text: str | None = None


def _render_bbox_overlay(bounding_box: dict[str, Any] | None) -> str:
    if not bounding_box:
        return ""
    try:
        bbox = json.dumps(bounding_box, sort_keys=True)
    except TypeError:
        bbox = str(bounding_box)
    return f"<div class='bbox'>Bounding box: {bbox}</div>"


def render_pdf_viewer(
    pdf_path: str | None,
    *,
    page_number: int | None = None,
    bounding_box: dict[str, Any] | None = None,
    height: int = 860,
) -> None:
    if pdf_path:
        path = Path(pdf_path)
        if path.exists():
            data = path.read_bytes()
            encoded = base64.b64encode(data).decode("ascii")
            st.components.v1.html(
                f"""
                <div style="border:1px solid #2a2f3a;border-radius:10px;padding:0.5rem">
                  <embed src="data:application/pdf;base64,{encoded}#page={page_number or 1}"
                         type="application/pdf"
                         width="100%"
                         height="{height}px" />
                  {_render_bbox_overlay(bounding_box)}
                </div>
                """,
                height=height,
                scrolling=True,
            )
            return
    st.info("PDF preview unavailable. Provide a local file path to enable inline rendering.")
    if bounding_box:
        st.caption(f"Bounding box: {bounding_box}")


def render_table_image(image_path: str | None, caption: str | None = None) -> None:
    if image_path and Path(image_path).exists():
        st.image(image_path, caption=caption or "Table image", use_container_width=True)
        return
    st.info("Table image unavailable.")


def render_excel_grid(data: Sequence[dict[str, Any]] | None, *, key: str = "excel-grid") -> None:
    if not data:
        st.info("No Excel grid data available.")
        return
    st.dataframe(data, use_container_width=True, hide_index=True, key=key)


def render_source_artifact(artifact: SourceArtifact, *, key_prefix: str = "source") -> None:
    st.markdown(f"### {artifact.label}")
    st.caption(f"{artifact.source_type}{f' · page {artifact.page_number}' if artifact.page_number else ''}")
    if artifact.source_type in {"pdf", "filing_pdf"}:
        render_pdf_viewer(
            artifact.path,
            page_number=artifact.page_number,
            bounding_box=artifact.bounding_box,
        )
    elif artifact.source_type in {"table_image", "screenshot"}:
        render_table_image(artifact.path, caption=artifact.label)
    elif artifact.source_type in {"excel", "xlsx"}:
        grid = None
        if artifact.raw_text:
            try:
                parsed = json.loads(artifact.raw_text)
                if isinstance(parsed, list):
                    grid = parsed
            except json.JSONDecodeError:
                grid = None
        render_excel_grid(grid, key=f"{key_prefix}-excel-grid")
    else:
        if artifact.raw_text:
            st.text_area("Source text", artifact.raw_text, height=420, key=f"{key_prefix}-raw")
        else:
            st.info("No source artifact data to display.")

