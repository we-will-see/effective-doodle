-- Role-based grants from 04-data-model.md §3.1

GRANT USAGE ON SCHEMA coverage, filings, ingestion_raw, ops TO
  ingestion_filings_role, extraction_role, orchestrator_role,
  approval_processor_role, web_role;

GRANT SELECT ON ALL TABLES IN SCHEMA coverage, filings, ingestion_raw, ops TO
  ingestion_filings_role, extraction_role, orchestrator_role,
  approval_processor_role, web_role;

GRANT INSERT ON ALL TABLES IN SCHEMA filings TO ingestion_filings_role;
GRANT INSERT ON ALL TABLES IN SCHEMA ingestion_raw TO ingestion_filings_role;

GRANT UPDATE (parsed_text, parsed_tables, extraction_status, extracted_at)
  ON filings.documents TO extraction_role;

GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA ops TO orchestrator_role;

GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA coverage TO approval_processor_role;
GRANT INSERT, UPDATE ON ops.review_queue TO approval_processor_role;

GRANT INSERT ON ops.review_queue TO web_role;
