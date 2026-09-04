"""
Candor — Internal Merchant Orders CSV Ingestion & Validation.

Parses uploaded Internal Orders CSV files, validates columns and data types,
and inserts validated records into internal_orders.
"""
import csv
import io
import logging
from datetime import datetime
from typing import Optional

from app.core.supabase import supabase

logger = logging.getLogger(__name__)

# Mandatory header variations supported
_REQUIRED_COLUMNS = {
    "order_id": ["order_id", "order_number", "invoice_number", "id"],
    "amount":   ["amount", "order_amount", "total", "gross_amount"],
}

def ingest_orders(batch_id: str, csv_bytes: bytes, user_id: Optional[str] = None) -> list[dict]:
    """
    Parse and validate an Internal Orders CSV file.
    Returns list of inserted database records.
    Raises ValueError with a clear, human-readable message on validation error.
    """
    logger.info("[INGEST ORDERS] Parsing CSV for batch %s | size: %d bytes", batch_id, len(csv_bytes))

    if not csv_bytes or not csv_bytes.strip():
        raise ValueError("Uploaded internal orders file is empty. Please select a valid CSV file.")

    try:
        content = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = csv_bytes.decode("latin-1")
        except Exception:
            raise ValueError("Orders CSV file must be UTF-8 or Latin-1 encoded plain text.")

    stream = io.StringIO(content)
    reader = csv.DictReader(stream)

    if not reader.fieldnames:
        raise ValueError("Internal orders CSV header line is missing or malformed.")

    # Standardize header names
    field_map = {name.strip().lower().replace(" ", "_"): name for name in reader.fieldnames if name}

    # Validate required columns
    missing_fields = []
    for col_key, alt_names in _REQUIRED_COLUMNS.items():
        if not any(alt in field_map for alt in alt_names):
            missing_fields.append(f"'{col_key}' (accepted column names: {', '.join(alt_names)})")

    if missing_fields:
        raise ValueError(
            f"Invalid Internal Orders CSV format: Missing required columns {'; '.join(missing_fields)}. "
            f"Found columns: {', '.join(reader.fieldnames[:8])}."
        )

    # Determine column mapping
    order_col    = next(field_map[c] for c in _REQUIRED_COLUMNS["order_id"] if c in field_map)
    amount_col   = next(field_map[c] for c in _REQUIRED_COLUMNS["amount"] if c in field_map)
    customer_col = next((field_map[c] for c in ["customer", "customer_name", "client", "buyer"] if c in field_map), None)
    date_col     = next((field_map[c] for c in ["date", "order_date", "created_at"] if c in field_map), None)

    records_to_insert = []
    row_count = 0

    for i, row in enumerate(reader, start=2):
        if not any(v.strip() for v in row.values() if v):
            continue

        row_count += 1
        order_id_val = (row.get(order_col) or "").strip()
        amt_str      = (row.get(amount_col) or "").strip()

        if not order_id_val:
            raise ValueError(f"Row {i}: Order ID is empty.")

        if not amt_str:
            raise ValueError(f"Row {i}: Order amount is empty.")

        try:
            cleaned_amt = amt_str.replace("₹", "").replace("$", "").replace(",", "").strip()
            amount = float(cleaned_amt)
        except ValueError:
            raise ValueError(f"Row {i}: Invalid order amount '{amt_str}'. Must be a valid number.")

        customer = (row.get(customer_col) or f"Customer {row_count}").strip()
        date_str = (row.get(date_col) or "").strip()
        parsed_date = _parse_date(date_str)

        rec = {
            "order_id": order_id_val,
            "amount": amount,
            "customer": customer,
            "date": parsed_date,
        }
        if user_id:
            rec["user_id"] = user_id

        records_to_insert.append(rec)

    if not records_to_insert:
        raise ValueError("Orders CSV file contains no data rows.")

    res = supabase.table("internal_orders").upsert(records_to_insert, on_conflict="order_id").execute()
    inserted = res.data or records_to_insert
    logger.info("[INGEST ORDERS] Successfully inserted/updated %d rows for batch %s", len(inserted), batch_id)
    return inserted


def _parse_date(date_str: str) -> str:
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
