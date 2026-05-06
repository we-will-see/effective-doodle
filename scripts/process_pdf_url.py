#!/usr/bin/env python3
"""Process BSE PDF from direct URL.

Usage:
    python scripts/process_pdf_url.py <pdf_url> [--company <bse_code>]
    
Example:
    python scripts/process_pdf_url.py "https://www.bseindia.com/xml-data/corpfiling/AttachHis/38808228-ee50-4d49-94ba-d2543fb21b6f.pdf" --company 540222
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.types.sqlalchemy_models import Base, Company, Document, ParsedVersion
from core.utils.fingerprint import content_hash as compute_fingerprint
from extraction.pdf.text import extract_text_from_pdf
from extraction.tables.camelot import extract_tables_from_pdf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """Process BSE PDF from URL."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.raw_storage = Path("/data/raw/bse")
    
    def download_pdf(self, url: str, output_path: Path) -> bool:
        """Download PDF from URL."""
        try:
            logger.info(f"Downloading: {url}")
            response = requests.get(url, timeout=60, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            response.raise_for_status()
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            
            logger.info(f"Saved {len(response.content)} bytes to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def extract_content(self, pdf_path: Path) -> dict:
        """Extract text and tables from PDF."""
        logger.info(f"Extracting: {pdf_path}")
        
        # Extract text
        text_result = extract_text_from_pdf(pdf_path)
        
        # Extract tables
        table_result = extract_tables_from_pdf(pdf_path, flavor="auto")
        
        # Build parsed text
        parsed_text_parts = [text_result.full_text]
        
        # Add table summaries
        for idx, table in enumerate(table_result.tables):
            table_text = f"\n\n--- Table {idx + 1} (Page {table['page']}) ---\n"
            for row in table['data'][:20]:  # Limit rows
                table_text += " | ".join(str(cell)[:50] for cell in row) + "\n"
            parsed_text_parts.append(table_text)
        
        parsed_text = "".join(parsed_text_parts)
        
        confidence = (text_result.confidence_score + table_result.avg_quality) / 2
        
        return {
            "full_text": text_result.full_text,
            "parsed_text": parsed_text,
            "pages": text_result.page_count,
            "tables": table_result.table_count,
            "text_confidence": text_result.confidence_score,
            "table_confidence": table_result.avg_quality,
            "total_confidence": confidence,
        }
    
    def classify_filing(self, content: dict) -> dict:
        """Classify the filing type."""
        text_lower = content["full_text"].lower()
        
        # Simple classification based on keywords
        doc_type = "exchange_filing"
        sub_type = None
        
        if "quarterly" in text_lower or "q1" in text_lower or "q2" in text_lower or "q3" in text_lower:
            doc_type = "results"
            sub_type = "quarterly_results"
        elif "annual" in text_lower or "year ended" in text_lower:
            doc_type = "results"
            sub_type = "annual_report"
        elif "board meeting" in text_lower:
            doc_type = "board_meeting"
        elif "dividend" in text_lower or "bonus" in text_lower:
            doc_type = "corporate_action"
        elif "agm" in text_lower or "egm" in text_lower:
            doc_type = "shareholder_meeting"
        elif "sensex" in text_lower or "index" in text_lower:
            doc_type = "index_related"
        
        # Extract headline (first line or first 100 chars)
        lines = [l.strip() for l in content["full_text"].split('\n') if l.strip()]
        headline = lines[0][:150] if lines else "Unknown"
        
        return {
            "document_type": doc_type,
            "document_subtype": sub_type,
            "headline": headline,
            "confidence": content["total_confidence"],
        }
    
    def process(self, pdf_url: str, company_bse_code: str = None) -> dict:
        """Process PDF from URL."""
        
        # Extract filename from URL
        url_path = urlparse(pdf_url).path
        filename = Path(url_path).name
        if not filename.endswith('.pdf'):
            filename = f"{uuid4()}.pdf"
        
        # Determine company
        company = None
        if company_bse_code:
            company = self.db.query(Company).filter(
                Company.bse_code == company_bse_code
            ).first()
        
        if not company:
            # Default to Cohance
            company = self.db.query(Company).filter(
                Company.bse_code == "543064"
            ).first()
        
        if not company:
            logger.error("Company not found in database")
            return {"error": "Company not found"}
        
        # Storage path
        company_dir = self.raw_storage / company.bse_code / datetime.now().strftime("%Y/%m/%d")
        pdf_path = company_dir / filename
        
        # Download
        if not self.download_pdf(pdf_url, pdf_path):
            return {"error": "Download failed"}
        
        # Compute fingerprint
        content = pdf_path.read_bytes()
        fingerprint = compute_fingerprint(content)
        
        # Check for duplicates
        existing = self.db.query(Document).filter(
            Document.content_hash == fingerprint
        ).first()
        
        if existing:
            logger.info(f"Duplicate detected: {existing.source_id}")
            return {"error": "Duplicate filing", "document_id": str(existing.id)}
        
        # Extract content
        extraction = self.extract_content(pdf_path)
        
        # Classify
        classification = self.classify_filing(extraction)
        
        # Create Document record
        doc = Document(
            id=uuid4(),
            company_id=company.id,
            source="bse",
            source_id="manual_" + str(uuid4())[:8],
            content_hash=fingerprint,
            document_type=classification["document_type"],
            document_subtype=classification["document_subtype"],
            filing_title=classification["headline"][:200] or "Untitled Filing",
            filed_at=datetime.now(timezone.utc),
            filesystem_path=str(pdf_path),
            extraction_status="extracted",
            classification_status="classified",
        )
        self.db.add(doc)
        
        # Create ParsedVersion
        parsed = ParsedVersion(
            id=uuid4(),
            document_id=doc.id,
            parser_name="manual_pdf_processor",
            parser_version="1.0",
            parsed_text=extraction["parsed_text"][:500000],
            parsed_at=datetime.now(timezone.utc),
            extraction_confidence=extraction["total_confidence"],
        )
        self.db.add(parsed)
        
        self.db.commit()
        
        logger.info(f"Processed: {classification['headline'][:60]}")
        logger.info(f"Type: {classification['document_type']}/{classification['document_subtype']}")
        logger.info(f"Confidence: {extraction['total_confidence']:.2f}")
        
        return {
            "document_id": str(doc.id),
            "company": company.display_name,
            "type": classification["document_type"],
            "subtype": classification["document_subtype"],
            "headline": classification["headline"],
            "pages": extraction["pages"],
            "tables": extraction["tables"],
            "confidence": extraction["total_confidence"],
            "path": str(pdf_path),
        }


def main():
    parser = argparse.ArgumentParser(description="Process BSE PDF from URL")
    parser.add_argument("url", help="PDF URL")
    parser.add_argument("--company", "-c", help="BSE company code")
    parser.add_argument("--db", default="postgresql+psycopg://agentos:agentos@localhost/agentos",
                       help="Database URL")
    
    args = parser.parse_args()
    
    # Setup DB
    engine = create_engine(args.db)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        processor = PDFProcessor(db)
        result = processor.process(args.url, args.company)
        
        if "error" in result:
            print(f"\n❌ Error: {result['error']}")
            sys.exit(1)
        else:
            print(f"\n✅ Processed successfully!")
            print(f"Document ID: {result['document_id']}")
            print(f"Company: {result['company']}")
            print(f"Type: {result['type']}/{result['subtype']}")
            print(f"Pages: {result['pages']}, Tables: {result['tables']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Saved to: {result['path']}")
            
    except Exception as e:
        logger.exception("Processing failed")
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
