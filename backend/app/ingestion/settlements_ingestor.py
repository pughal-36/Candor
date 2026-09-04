"""
Candor — Razorpay Settlements CSV Ingestion & Validation.

Parses uploaded Razorpay CSV export files, validates columns and data types,
and inserts validated records into razorpay_settlements.
"""
import csv
import io
import logging
from datetime import datetime
from typing import Optional

from app.core.supabase import supabase

logger = logging.getLogger(__name__)

# Mandatory header variations supported (flexible CSV export parsing)
_REQUIRED_COLUMNS = {
    "amount": ["amount", "net_amount", "settlement_amount", "payout_amount"],
    "reference_number": ["reference_number", "utr", "utr_number", "reference", "rrn"],
}

def ingest_settlements(batch_id: str, csv_bytes: bytes, user_id: Optional[str] = None) -> list[dict]:
    """
    Parse and validate a Razorpay Settlements CSV file.
    Returns list of inserted database records.
    Raises ValueError with a clear, human-readable message on validation error.
    """
    logger.info("[INGEST SETTLEMENTS] Parsing CSV for batch %s | size: %d bytes", batch_id, len(csv_bytes))

    if not csv_bytes or not csv_bytes.strip():
        raise ValueError("Uploaded settlements file is empty. Please select a valid Razorpay CSV export.")

    try:
        content = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = csv_bytes.decode("latin-1")
        except Exception:
            raise ValueError("Settlements CSV file must be UTF-8 or Latin-1 encoded plain text.")

    stream = io.StringIO(content)
    reader = csv.DictReader(stream)

    if not reader.fieldnames:
        raise ValueError("Settlements CSV header line is missing or malformed.")

    # Standardize header names
    field_map = {name.strip().lower().replace(" ", "_"): name for name in reader.fieldnames if name}

    # Validate required columns
    missing_fields = []
    for col_key, alt_names in _REQUIRED_COLUMNS.items():
        if not any(alt in field_map for alt in alt_names):
            missing_fields.append(f"'{col_key}' (accepted column names: {', '.join(alt_names)})")

    if missing_fields:
        raise ValueError(
            f"Invalid Razorpay CSV format: Missing required columns {'; '.join(missing_fields)}. "
            f"Found columns: {', '.join(reader.fieldnames[:8])}."
        )

    # Determine column mapping
    payout_col = next((field_map[c] for c in ["payout_id", "settlement_id", "id"] if c in field_map), None)
    amount_col = next(field_map[c] for c in _REQUIRED_COLUMNS["amount"] if c in field_map)
    ref_col    = next(field_map[c] for c in _REQUIRED_COLUMNS["reference_number"] if c in field_map)
    fee_col    = next((field_map[c] for c in ["fee", "fees", "razorpay_fee"] if c in field_map), None)
    gross_col  = next((field_map[c] for c in ["gross_amount", "gross", "order_amount"] if c in field_map), None)
    date_col   = next((field_map[c] for c in ["date", "settlement_date", "payout_date", "created_at"] if c in field_map), None)

    records_to_insert = []
    row_count = 0

    for i, row in enumerate(reader, start=2):
        # Skip empty rows
        if not any(v.strip() for v in row.values() if v):
            continue

        row_count += 1
        ref_val = (row.get(ref_col) or "").strip()
        amt_str = (row.get(amount_col) or "").strip()

        if not amt_str:
            raise ValueError(f"Row {i}: Settlement amount is empty.")

        try:
            # Clean currency symbols / commas
            cleaned_amt = amt_str.replace("₹", "").replace("$", "").replace(",", "").strip()
            amount = float(cleaned_amt)
        except ValueError:
            raise ValueError(f"Row {i}: Invalid settlement amount '{amt_str}'. Must be a valid number.")

        fee = 0.0
        if fee_col and row.get(fee_col):
            try:
                fee = float(row[fee_col].replace("₹", "").replace(",", "").strip())
            except ValueError:
                fee = 0.0

        gross_amount = amount + fee
        if gross_col and row.get(gross_col):
            try:
                gross_amount = float(row[gross_col].replace("₹", "").replace(",", "").strip())
            except ValueError:
                pass

        payout_id = (row.get(payout_col) or f"setl_upload_{batch_id[:8]}_{row_count}").strip()
        date_str = (row.get(date_col) or "").strip()
        parsed_date = _parse_date(date_str, i)

        rec = {
            "payout_id": payout_id,
            "amount": amount,
            "fee": fee,
            "gross_amount": gross_amount,
            "date": parsed_date,
            "reference_number": ref_val,
        }
        if user_id:
            rec["user_id"] = user_id

        records_to_insert.append(rec)

    if not records_to_insert:
        raise ValueError("Settlements CSV file contains no data rows.")

    res = supabase.table("razorpay_settlements").upsert(records_to_insert, on_conflict="payout_id").execute()
    inserted = res.data or records_to_insert
    logger.info("[INGEST SETTLEMENTS] Successfully inserted/updated %d rows for batch %s", len(inserted), batch_id)
    return inserted


def _parse_date(date_str: str, row_idx: int) -> str:
    """Parse date string into ISO YYYY-MM-DD format."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")

    clean_str = date_str.split("T")[0].split(" ")[0].strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return datetime.now().strftime("%Y-%m-%d")
