"""Extraction pipeline listener.

S-02: Listens for documents with extraction_status='pending',
runs pdfplumber + camelot, stores results, updates status.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from extraction.pdf.text import extract_text_from_pdf
from extraction.tables.camelot import extract_tables_from_pdf

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """Pipeline for extracting content from pending documents.
    
    - Listens for documents with extraction_status='pending'
    - Runs pdfplumber for text
    - Runs camelot for tables  
    - Stores parsed versions
    - Updates source_provenance with bounding boxes
    - Updates document status
    """
    
    def __init__(self):
        self.processed_count = 0
        self.failed_count = 0
    
    def get_pending_documents(self, db_session: Session, limit: int = 10) -> list[Any]:
        """Fetch documents awaiting extraction.
        
        Args:
            db_session: Database session
            limit: Max documents to fetch
            
        Returns:
            List of Document ORM objects
        """
        from core.types.sqlalchemy_models import Document
        
        docs = db_session.query(Document).filter(
            Document.extraction_status == "pending"
        ).order_by(
            Document.filed_at.asc()
        ).limit(limit).all()
        
        return docs
    
    def process_document(self, document: Any, db_session: Session) -> dict[str, Any]:
        """Process a single document.
        
        Args:
            document: Document ORM object
            db_session: Database session
            
        Returns:
            Result summary
        """
        from core.types.sqlalchemy_models import ParsedVersion, SourceProvenance
        from core.utils.fingerprint import compute_fingerprint
        
        doc_path = Path(document.filesystem_path)
        if not doc_path.exists():
            logger.error(f"Document file not found: {doc_path}")
            document.extraction_status = "extraction_failed"
            return {
                "document_id": str(document.id),
                "status": "failed",
                "error": "File not found",
            }
        
        logger.info(f"Processing document {document.id}: {document.filing_title}")
        
        try:
            # Extract text
            text_result = extract_text_from_pdf(doc_path)
            
            # Extract tables
            table_result = extract_tables_from_pdf(doc_path, flavor="auto")
            
            # Build parsed_text (concatenate text + table summaries)
            parsed_text_parts = [text_result.full_text]
            
            # Add table summaries to parsed_text
            for idx, table in enumerate(table_result.tables):
                table_text = f"\n\n--- Table {idx + 1} (Page {table['page']}) ---\n"
                # Convert table data to text representation
                for row in table['data'][:20]:  # Limit rows
                    table_text += " | ".join(str(cell)[:50] for cell in row) + "\n"
                parsed_text_parts.append(table_text)
            
            parsed_text = "".join(parsed_text_parts)
            
            # Compute content hash for parsed version
            parsed_fingerprint = compute_fingerprint(parsed_text.encode())
            
            # Create parsed version record
            parser_version = f"pdfplumber+camelot-1.0"
            extraction_confidence = (text_result.confidence_score + table_result.avg_quality) / 2
            
            parsed_version = ParsedVersion(
                document_id=document.id,
                parser_name="agentos-extraction-pipeline",
                parser_version=parser_version,
                parsed_text=parsed_text[:500000],  # Limit storage
                parsed_tables={
                    "table_count": table_result.table_count,
                    "tables": [
                        {
                            "page": t["page"],
                            "bbox": t["bbox"],
                            "accuracy": t["accuracy"],
                            "quality_score": t["quality_score"],
                            "shape": [len(t["data"]), len(t["data"][0]) if t["data"] else 0],
                            "sample": t["data"][:3] if t["data"] else [],  # First 3 rows
                        }
                        for t in table_result.tables
                    ]
                },
                extraction_confidence=extraction_confidence,
                is_current=True,
            )
            db_session.add(parsed_version)
            
            # Create source provenance for extracted facts
            # This is a placeholder - real implementation would map specific cells
            for page in text_result.pages:
                if page["char_count"] > 0:
                    prov = SourceProvenance(
                        source_type="bse_filing",
                        source_id=document.source_id,
                        document_path=str(doc_path),
                        page_number=page["page_num"],
                        raw_text=page["text"][:10000],  # Limit
                        extracted_by="pdfplumber",
                        extracted_at=datetime.now(timezone.utc),
                    )
                    db_session.add(prov)
            
            # Update document
            document.parsed_text = parsed_text[:500000]  # Store summary
            document.parsed_tables = {
                "version_id": str(parsed_version.id),
                "table_count": table_result.table_count,
                "text_confidence": text_result.confidence_score,
                "table_confidence": table_result.avg_quality,
            }
            document.extraction_status = "extracted"
            document.extracted_at = datetime.now(timezone.utc)
            
            db_session.commit()
            
            self.processed_count += 1
            
            logger.info(
                f"Document {document.id} processed: "
                f"{text_result.page_count} pages, "
                f"{table_result.table_count} tables, "
                f"confidence={extraction_confidence:.2f}"
            )
            
            return {
                "document_id": str(document.id),
                "status": "success",
                "pages": text_result.page_count,
                "tables": table_result.table_count,
                "confidence": extraction_confidence,
            }
            
        except Exception as e:
            logger.error(f"Extraction failed for {document.id}: {e}")
            document.extraction_status = "extraction_failed"
            
            # Create alert
            from core.types.sqlalchemy_models import Alert
            alert = Alert(
                alert_type="extraction_failed",
                severity="warning",
                message=f"Extraction failed for document {document.id}: {e}",
                source_component="extraction_pipeline",
                source_id=str(document.id),
            )
            db_session.add(alert)
            
            db_session.commit()
            self.failed_count += 1
            
            return {
                "document_id": str(document.id),
                "status": "failed",
                "error": str(e),
            }
    
    def run_cycle(self, db_session: Session, batch_size: int = 10) -> dict[str, Any]:
        """Run one extraction cycle.
        
        Args:
            db_session: Database session
            batch_size: Max documents to process
            
        Returns:
            Cycle summary
        """
        pending = self.get_pending_documents(db_session, limit=batch_size)
        
        if not pending:
            return {"processed": 0, "message": "No pending documents"}
        
        results = []
        for doc in pending:
            result = self.process_document(doc, db_session)
            results.append(result)
        
        success_count = sum(1 for r in results if r["status"] == "success")
        fail_count = sum(1 for r in results if r["status"] == "failed")
        
        return {
            "total": len(results),
            "success": success_count,
            "failed": fail_count,
            "details": results,
        }


def run_extraction_pipeline(
    db_session: Session,
    batch_size: int = 10,
    single_cycle: bool = False,
) -> dict[str, Any]:
    """Run the extraction pipeline.
    
    Args:
        db_session: Database session
        batch_size: Documents per cycle
        single_cycle: Run once (True) or loop forever (False)
        
    Returns:
        Result summary
    """
    import time
    
    pipeline = ExtractionPipeline()
    
    if single_cycle:
        return pipeline.run_cycle(db_session, batch_size)
    
    # Continuous mode (for daemon use)
    logger.info("Starting extraction pipeline in continuous mode")
    
    while True:
        try:
            result = pipeline.run_cycle(db_session, batch_size)
            
            if result["processed"] == 0:
                # No work, sleep
                logger.debug("No pending documents, sleeping 60s")
                time.sleep(60)
            else:
                logger.info(f"Cycle complete: {result['success']} success, {result['failed']} failed")
                
        except Exception as e:
            logger.error(f"Pipeline cycle failed: {e}")
            time.sleep(60)


if __name__ == "__main__":
    # Manual run
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    doc_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.types.sqlalchemy_models import Base
    
    db_url = "postgresql://localhost/agentos"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    pipeline = ExtractionPipeline()
    
    if doc_id:
        # Process specific document
        from core.types.sqlalchemy_models import Document
        doc = db.query(Document).filter_by(id=doc_id).first()
        if doc:
            result = pipeline.process_document(doc, db)
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Document {doc_id} not found")
    else:
        # Process all pending
        result = pipeline.run_cycle(db, batch_size=5)
        print(json.dumps(result, indent=2, default=str))
