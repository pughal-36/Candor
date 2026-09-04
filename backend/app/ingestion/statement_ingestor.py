"""
Candor — Bank statement ingestion orchestrator.

Coordinates:
  1. Try pdfplumber text-layer extraction
  2. Fall back to Tesseract OCR if no text layer is found
  3. Write rows to bank_statement table with low_ocr_confidence flag
  4. Update batch status: pending → parsing → (caller takes over)
"""
import logging
import os
import tempfile

from app.core.supabase import supabase
from app.ingestion.pdf_parser import extract_from_text_layer
from app.ingestion.ocr_fallback import extract_via_ocr

logger = logging.getLogger(__name__)


def ingest_statement(batch_id: str, pdf_bytes: bytes) -> int:
    """
    Parse a bank statement PDF and persist rows to bank_statement.

    Returns the number of rows inserted.
    Raises RuntimeError if no rows could be extracted at all.
    """
    logger.info("[UPLOAD TRACE] Starting ingestion for batch %s | PDF size: %d bytes", batch_id, len(pdf_bytes))
    _set_status(batch_id, "parsing")

    # Write bytes to a temp file (both pdfplumber and pdf2image need a path)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        os.write(tmp_fd, pdf_bytes)
        os.close(tmp_fd)

        rows, used_ocr = _parse(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not rows:
        logger.error("[UPLOAD TRACE] Ingestion failed for batch %s: 0 rows extracted", batch_id)
        raise RuntimeError(
            "No rows could be extracted from the uploaded PDF. "
            "Ensure the file is a bank statement (text layer or scannable image)."
        )

    # Clear any previously ingested rows for this batch to ensure clean re-runs
    supabase.table("bank_statement").delete().eq("batch_id", batch_id).execute()

    records = [
        {
            "batch_id": batch_id,
            "narration": r["narration"],
            "amount": float(r["amount"]),
            "date": r["date"],
            "extracted_reference": r.get("extracted_reference"),
            "low_ocr_confidence": r.get("low_ocr_confidence", used_ocr),
        }
        for r in rows
    ]

    # Deduplicate records by (date, narration, amount)
    unique_records = []
    seen = set()
    for rec in records:
        key = (rec["date"], rec["narration"].strip(), float(rec["amount"]))
        if key not in seen:
            seen.add(key)
            unique_records.append(rec)

    if unique_records:
        supabase.table("bank_statement").insert(unique_records).execute()

    logger.info(
        "[UPLOAD TRACE] Persisted %d unique rows to bank_statement table for batch %s (used_ocr=%s)",
        len(unique_records), batch_id, used_ocr,
    )
    return len(unique_records)


def _parse(pdf_path: str) -> tuple[list[dict], bool]:
    """
    Try text-layer extraction first; fall back to OCR if it yields nothing.
    Returns (rows, used_ocr).
    """
    logger.info("[UPLOAD TRACE] Attempting pdfplumber text-layer extraction on %s", pdf_path)
    rows = extract_from_text_layer(pdf_path)
    if rows:
        logger.info("[UPLOAD TRACE] Text-layer extraction successful: %d rows found", len(rows))
        return rows, False

    logger.info("[UPLOAD TRACE] No text layer detected — switching to Tesseract OCR fallback")
    rows = extract_via_ocr(pdf_path)
    logger.info("[UPLOAD TRACE] OCR extraction complete: %d rows found", len(rows))
    return rows, True


def _set_status(batch_id: str, status: str) -> None:
    supabase.table("batches").update({"status": status}).eq("id", batch_id).execute()

