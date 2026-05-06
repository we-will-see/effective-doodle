"""Table extraction using camelot-py.

S-02: Deterministic table extraction with structural integrity scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import camelot

logger = logging.getLogger(__name__)


@dataclass
class TableExtractionResult:
    """Result of table extraction."""
    
    tables: list[dict[str, Any]]
    """List of extracted tables with metadata."""
    
    table_count: int
    """Total tables found."""
    
    extraction_time_ms: float
    """Time taken."""
    
    avg_quality: float
    """Average quality score across tables."""


@dataclass
class ExtractedTable:
    """Single extracted table."""
    
    page: int
    """1-indexed page number."""
    
    index: int
    """Table index on this page."""
    
    data: list[list[str]]
    """Table data as 2D list."""
    
    dataframe: Any
    """Pandas DataFrame."""
    
    bbox: tuple[float, float, float, float]
    """(x0, y0, x1, y1) bounding box."""
    
    accuracy: float
    """Camelot parsing accuracy."""
    
    whitespace: float
    ""% of empty cells."""
    
    quality_score: float
    """Calculated quality score (0-1)."""


def extract_tables_from_pdf(
    pdf_path: Path | str,
    pages: Optional[str] = None,
    flavor: str = "auto",
    process_background: bool = False,
) -> TableExtractionResult:
    """Extract tables from PDF using camelot.
    
    Args:
        pdf_path: Path to PDF
        pages: Page range string (e.g., "1-5" or "1,3,5"), None for all
        flavor: "lattice" (for ruled tables), "stream" (for whitespace-separated), 
                or "auto" (try both and pick best)
        process_background: Include background lines (for lattice)
    
    Returns:
        TableExtractionResult with tables and metadata
        
    Raises:
        FileNotFoundError: If PDF doesn't exist
        RuntimeError: If extraction fails
    """
    import time
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    start_time = time.time()
    
    try:
        tables_data = []
        
        if flavor == "auto":
            # Try lattice first, then stream, combine results
            lattice_tables = _extract_with_flavor(
                pdf_path, "lattice", pages, process_background
            )
            stream_tables = _extract_with_flavor(
                pdf_path, "stream", pages, process_background
            )
            
            # Merge and deduplicate by bbox overlap
            tables_data = _merge_tables(lattice_tables, stream_tables)
        else:
            tables_data = _extract_with_flavor(
                pdf_path, flavor, pages, process_background
            )
        
        elapsed_ms = (time.time() - start_time) * 1000
        avg_quality = sum(t["quality_score"] for t in tables_data) / max(len(tables_data), 1)
        
        logger.info(
            f"Extracted {len(tables_data)} tables from {pdf_path} "
            f"in {elapsed_ms:.0f}ms, avg_quality={avg_quality:.2f}"
        )
        
        return TableExtractionResult(
            tables=tables_data,
            table_count=len(tables_data),
            extraction_time_ms=elapsed_ms,
            avg_quality=avg_quality,
        )
        
    except Exception as e:
        logger.error(f"Failed to extract tables from {pdf_path}: {e}")
        raise RuntimeError(f"Table extraction failed: {e}")


def _extract_with_flavor(
    pdf_path: Path,
    flavor: str,
    pages: Optional[str],
    process_background: bool,
) -> list[dict[str, Any]]:
    """Extract tables with specified flavor."""
    
    kwargs = {
        "flavor": flavor,
    }
    if pages:
        kwargs["pages"] = pages
    if flavor == "lattice":
        kwargs["process_background"] = process_background
    
    tables = camelot.read_pdf(str(pdf_path), **kwargs)
    
    results = []
    for idx, table in enumerate(tables):
        # Calculate quality metrics
        df = table.df
        total_cells = df.shape[0] * df.shape[1]
        empty_cells = (df == "").sum().sum()
        whitespace = empty_cells / total_cells if total_cells > 0 else 0
        
        # Quality score combines parsing accuracy and cell fill rate
        accuracy = table.parsing_report.get("accuracy", 50) / 100
        fill_rate = 1 - whitespace
        quality_score = (accuracy * 0.6) + (fill_rate * 0.4)
        
        table_data = {
            "page": table.page,
            "index": idx,
            "data": df.values.tolist(),
            "dataframe": df,
            "bbox": table._bbox,  # (x0, y0, x1, y1)
            "accuracy": accuracy,
            "whitespace": whitespace,
            "quality_score": quality_score,
            "flavor": flavor,
        }
        results.append(table_data)
    
    return results


def _merge_tables(
    lattice_tables: list[dict],
    stream_tables: list[dict],
    overlap_threshold: float = 0.7,
) -> list[dict]:
    """Merge tables from lattice and stream, deduplicating overlaps."""
    
    def bbox_overlap(bbox1, bbox2):
        """Calculate IoU of two bounding boxes."""
        x0_1, y0_1, x1_1, y1_1 = bbox1
        x0_2, y0_2, x1_2, y1_2 = bbox2
        
        # Intersection
        xi0 = max(x0_1, x0_2)
        yi0 = max(y0_1, y0_2)
        xi1 = min(x1_1, x1_2)
        yi1 = min(y1_1, y1_2)
        
        if xi1 <= xi0 or yi1 <= yi0:
            return 0.0
        
        intersection = (xi1 - xi0) * (yi1 - yi0)
        
        # Union
        area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
        area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0
    
    # Start with lattice results (usually higher quality for ruled tables)
    merged = list(lattice_tables)
    
    # Add stream results if they don't significantly overlap with existing
    for stream_table in stream_tables:
        is_duplicate = False
        for existing in merged:
            if stream_table["page"] != existing["page"]:
                continue
            overlap = bbox_overlap(stream_table["bbox"], existing["bbox"])
            if overlap > overlap_threshold:
                is_duplicate = True
                # Keep the higher quality one
                if stream_table["quality_score"] > existing["quality_score"]:
                    merged.remove(existing)
                    merged.append(stream_table)
                break
        
        if not is_duplicate:
            merged.append(stream_table)
    
    # Sort by page, then vertical position
    merged.sort(key=lambda t: (t["page"], -t["bbox"][3]))  # Top to bottom
    
    return merged
