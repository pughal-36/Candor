# Phase 2 — Bank Statement Ingestion

## Objective
Extract structured bank statement rows (date, narration, credit amount, extracted reference number) from uploaded bank statement PDFs, handling digital PDFs via text parsing and scanned PDFs via an automatic OCR fallback path.

## What was built
- `backend/app/ingestion/pdf_parser.py`: Primary text-layer extraction using `pdfplumber`. Attempts structured table parsing first, falling back to line regex parsing. Extracts Indian payment reference strings (UTR, NEFT, IMPS).
- `backend/app/ingestion/ocr_fallback.py`: Secondary OCR fallback using `pdf2image` and `pytesseract`. Renders PDF pages to 300 DPI images and extracts tabular text. Flags all resulting rows with `low_ocr_confidence = True`.
- `backend/app/ingestion/statement_ingestor.py`: Ingestion orchestrator that creates batch records, runs parsing, and writes structured records to `bank_statement`.

## Key decisions and why
- **Honest OCR Flagging**: Scanned statement rows inherit `low_ocr_confidence = True`. Rather than attempting to hide OCR ambiguity, OCR-flagged rows are explicitly surfaced in the UI and routed to human review.

## How to verify it
1. Call `POST /api/v1/upload-statement` with a sample PDF.
2. Verify rows created in `bank_statement` table matching the batch ID.

## Known limitations / deferred work
- Tesseract OCR requires system binary installation (`tesseract-ocr` and `poppler-utils`). If missing on host OS, OCR mode logs an explicit error and falls back gracefully.

## Depends on / feeds into
Needed schema from Phase 1. Feeds extracted bank rows into Phase 3 (Deterministic pass) and Phase 4 (Agent pass).
