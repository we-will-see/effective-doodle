"""PDF text extraction using pdfplumber.

S-02: Deterministic text extraction with page boundaries and bounding boxes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class ExtractedText:
    """Result of text extraction from a PDF."""
    
    full_text: str
    """Complete extracted text with page separator markers."""
    
    pages: list[dict[str, Any]]
    """Per-page text with metadata: [{"page_num": int, "text": str, "bbox": (x0, y0, x1, y1)}]."""
    
    page_count: int
    """Total number of pages processed."""
    
    extraction_time_ms: float
    """Time taken for extraction."""
    
    char_count: int
    """Total character count."""
    
    confidence_score: float
    """Heuristic confidence based on extraction quality."""


def extract_text_from_pdf(
    pdf_path: Path | str,
    page_numbers: Optional[list[int]] = None,
) -> ExtractedText:
    """Extract text from a PDF file using pdfplumber.
    
    Args:
        pdf_path: Path to PDF file
        page_numbers: Optional list of specific pages to extract (1-indexed)
                     If None, extracts all pages
    
    Returns:
        ExtractedText with full text and per-page metadata
    
    Raises:
        FileNotFoundError: If PDF doesn't exist
        RuntimeError: If extraction fails
    """
    import time
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    start_time = time.time()
    
    pages_data = []
    full_text_parts = []
    total_chars = 0
    quality_issues = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            actual_page_count = len(pdf.pages)
            
            # Determine which pages to process
            if page_numbers is None:
                pages_to_process = range(len(pdf.pages))
            else:
                pages_to_process = [n - 1 for n in page_numbers if 1 <= n <= len(pdf.pages)]
            
            for idx in pages_to_process:
                page = pdf.pages[idx]
                page_num = idx + 1  # 1-indexed for output
                
                # Extract text from this page
                page_text = page.extract_text()
                page_text = page_text or ""  # Handle None
                
                # Get page bounding box
                page_bbox = page.bbox  # (x0, y0, x1, y1)
                
                # Quality checks
                if len(page_text.strip()) == 0:
                    quality_issues.append(f"Page {page_num}: empty or no extractable text")
                elif len(page_text) < 100:
                    quality_issues.append(f"Page {page_num}: very short text ({len(page_text)} chars)")
                
                page_data = {
                    "page_num": page_num,
                    "text": page_text,
                    "bbox": page_bbox,
                    "char_count": len(page_text),
                    "word_count": len(page_text.split()),
                }
                pages_data.append(page_data)
                
                # Add to full text with page marker
                if page_text.strip():
                    full_text_parts.append(f"\n--- Page {page_num} ---\n")
                    full_text_parts.append(page_text)
                
                total_chars += len(page_text)
        
        full_text = "".join(full_text_parts)
        
        # Calculate confidence score
        confidence = _calculate_text_confidence(
            page_count=len(pages_data),
            empty_pages=sum(1 for p in pages_data if p["char_count"] == 0),
            total_chars=total_chars,
            quality_issues=quality_issues,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Extracted text from {pdf_path}: {len(pages_data)} pages, "
            f"{total_chars} chars in {elapsed_ms:.0f}ms, confidence={confidence:.2f}"
        )
        
        if quality_issues:
            logger.warning(f"Quality issues: {quality_issues}")
        
        return ExtractedText(
            full_text=full_text,
            pages=pages_data,
            page_count=len(pages_data),
            extraction_time_ms=elapsed_ms,
            char_count=total_chars,
            confidence_score=confidence,
        )
        
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        raise RuntimeError(f"Text extraction failed: {e}")


def _calculate_text_confidence(
    page_count: int,
    empty_pages: int,
    total_chars: int,
    quality_issues: list[str],
) -> float:
    """Calculate heuristic confidence score (0.0-1.0).
    
    Based on:
    - Ratio of empty pages
    - Total character count relative to expected
    - Number of quality issues
    """
    if page_count == 0:
        return 0.0
    
    # Start with perfect score
    confidence = 1.0
    
    # Penalize empty pages
    empty_ratio = empty_pages / page_count
    confidence -= empty_ratio * 0.5
    
    # Penalize for quality issues
    confidence -= len(quality_issues) * 0.05
    
    # Check if total text seems reasonable (at least 100 chars per page on average)
    expected_min_chars = page_count * 100
    if total_chars < expected_min_chars:
        confidence -= 0.3
    
    return max(0.0, min(1.0, confidence))


def extract_text_from_region(
    pdf_path: Path | str,
    page_number: int,
    bbox: tuple[float, float, float, float],
) -> str:
    """Extract text from a specific region/bounding box.
    
    Args:
        pdf_path: Path to PDF
        page_number: 1-indexed page number
        bbox: (x0, y0, x1, y1) bounding box in PDF coordinates
    
    Returns:
        Extracted text from that region
    """
    pdf_path = Path(pdf_path)
    
    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            raise ValueError(f"Invalid page number: {page_number}")
        
        page = pdf.pages[page_number - 1]
        
        # Crop to bbox and extract
        cropped = page.within_bbox(bbox)
        text = cropped.extract_text() or ""
        
        return text
