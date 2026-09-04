"""
Candor — Text-layer PDF extraction using pdfplumber.

Primary ingestion path for digitally-generated bank statement PDFs
(most Indian bank e-statements have a text layer).

Strategy per page:
  1. Try pdfplumber table extraction (banks format statements as tables)
  2. If no tables found on a page, try raw text line parsing
  3. Extract UTR/NEFT/IMPS reference numbers from narration strings via regex

Returns an empty list if no usable text layer is detected — the caller
(statement_ingestor) then triggers the OCR fallback.
"""
import logging
import re
from datetime import datetime, date
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Regex patterns
# ----------------------------------------------------------------

# Indian payment reference formats (UTR, NEFT, IMPS)
_REFERENCE_PATTERNS = [
    r'UTR\d{10,22}',           # UTR + 10-22 digits
    r'[A-Z]{4}\d{12}',         # NEFT: 4 alpha + 12 digits
    r'IMPS\d{12}',             # IMPS
    r'\b\d{16,22}\b',          # Generic long numeric ref
]
_REF_RE = re.compile('|'.join(_REFERENCE_PATTERNS))

# Amount: digits with optional commas, mandatory two decimal places
_AMOUNT_RE = re.compile(r'\b[\d,]+\.\d{2}\b')

# Date formats common in Indian bank statements
_DATE_FORMATS = (
    "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
    "%d %b %Y", "%d %B %Y", "%Y-%m-%d",
)
_DATE_RE = re.compile(
    r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{2}\s+\w{3}\s+\d{4}|\d{4}-\d{2}-\d{2})\b'
)


# ----------------------------------------------------------------
# Public API
# ----------------------------------------------------------------

def extract_from_text_layer(pdf_path: str) -> list[dict]:
    """
    Extract bank statement rows from a PDF that has a text layer.
    Returns an empty list if the PDF has no usable text — caller must
    fall back to OCR in that case.
    """
    rows: list[dict] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                rows.extend(_extract_page_rows(page))
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return []

    valid = [r for r in rows if r.get("narration") and r.get("amount") and r.get("date")]

    # Deduplicate extracted rows by (date, narration, amount)
    unique_valid = []
    seen = set()
    for r in valid:
        key = (r["date"], r["narration"].strip(), float(r["amount"]))
        if key not in seen:
            seen.add(key)
            unique_valid.append(r)

    logger.debug("Text-layer: %d raw rows → %d valid unique", len(rows), len(unique_valid))
    return unique_valid


# ----------------------------------------------------------------
# Per-page extraction
# ----------------------------------------------------------------

def _extract_page_rows(page) -> list[dict]:
    """Try table extraction first; fall back to line-by-line text parsing."""
    rows: list[dict] = []

    # Attempt 1: structured table detection
    for table in page.extract_tables() or []:
        for row in table:
            parsed = _parse_table_row(row)
            if parsed:
                rows.append(parsed)

    if rows:
        return rows

    # Attempt 2: raw text lines
    text = page.extract_text() or ""
    if not text.strip():
        return []  # no text layer on this page

    for line in text.splitlines():
        parsed = _parse_text_line(line.strip())
        if parsed:
            rows.append(parsed)

    return rows


def _parse_table_row(row: list) -> Optional[dict]:
    if not row or len(row) < 3:
        return None

    cells = [str(c or "").strip() for c in row]
    full_text = " ".join(cells)

    amount = _pick_amount(cells)
    if amount is None:
        return None

    parsed_date = extract_date(full_text)
    if parsed_date is None:
        return None

    narration = _pick_narration(cells)
    if not narration:
        return None

    return {
        "narration": narration,
        "amount": amount,
        "date": parsed_date.isoformat(),
        "extracted_reference": extract_reference(narration),
    }


def _parse_text_line(line: str) -> Optional[dict]:
    if not line:
        return None

    amounts = _AMOUNT_RE.findall(line)
    if not amounts:
        return None

    parsed_date = extract_date(line)
    if parsed_date is None:
        return None

    # In Indian bank statements: [Date] [Narration] [Credit] [Running Balance]
    # Balance is the last amount (amounts[-1]); Credit precedes Balance (amounts[-2])
    try:
        if len(amounts) >= 2:
            amount = float(amounts[-2].replace(",", ""))
        else:
            amount = float(amounts[0].replace(",", ""))
    except ValueError:
        return None

    if amount < 1.0:
        return None

    return {
        "narration": re.sub(r'\s+', ' ', line),
        "amount": amount,
        "date": parsed_date.isoformat(),
        "extracted_reference": extract_reference(line),
    }


# ----------------------------------------------------------------
# Helpers (also imported by ocr_fallback)
# ----------------------------------------------------------------

def _pick_amount(cells: list[str]) -> Optional[float]:
    """
    Find a transaction credit/deposit amount in a row's cells.
    Bank statements put running Balance in the rightmost column,
    and Credit / Deposit in the column preceding Balance.
    """
    amount_vals: list[float] = []
    for cell in cells:
        nums = _AMOUNT_RE.findall(cell)
        if nums:
            try:
                val = float(nums[0].replace(",", ""))
                if val >= 1.0:
                    amount_vals.append(val)
            except ValueError:
                continue

    if not amount_vals:
        return None

    # If both Credit/Debit and Balance columns are present, credit is the second to last
    if len(amount_vals) >= 2:
        return amount_vals[-2]

    return amount_vals[0]


def _pick_narration(cells: list[str]) -> str:
    """Use the longest non-numeric cell as the narration."""
    candidates = [c for c in cells if c and not _AMOUNT_RE.fullmatch(c) and len(c) > 5]
    return max(candidates, key=len, default="")


def extract_date(text: str) -> Optional[date]:
    """Extract the first recognisable date from a string."""
    match = _DATE_RE.search(text)
    if not match:
        return None
    raw = match.group(0).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def extract_reference(narration: str) -> Optional[str]:
    """Extract a payment reference number (UTR/NEFT/IMPS) from a narration."""
    match = _REF_RE.search(narration)
    return match.group(0) if match else None
