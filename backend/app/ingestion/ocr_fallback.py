"""
Candor — OCR fallback using Tesseract + pdf2image.

Used when the PDF has no usable text layer (scanned / photographed bank
statements). Every row extracted via this path is tagged with
low_ocr_confidence=True — this is surfaced in the UI and used by the
matching pipeline to route these rows directly to the exception ledger
rather than the agent pass.

Requirements (must be installed separately from pip):
  - Tesseract: https://github.com/tesseract-ocr/tesseract
  - Poppler (for pdf2image): https://poppler.freedesktop.org/

Run `tesseract --version` to confirm Tesseract is on PATH.
"""
import logging

from app.ingestion.pdf_parser import extract_date, extract_reference, _AMOUNT_RE

logger = logging.getLogger(__name__)

_DPI = 300  # Higher DPI improves OCR accuracy on small bank statement fonts

try:
    import pytesseract
    from PIL import Image
    import pdf2image as _pdf2image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False
    logger.warning(
        "OCR dependencies not installed (pytesseract / pdf2image / Pillow). "
        "Scanned PDFs will not be processable. "
        "Install them and ensure Tesseract is on PATH."
    )


def extract_via_ocr(pdf_path: str) -> list[dict]:
    """
    Render each PDF page as an image and extract text via Tesseract.

    All returned rows have low_ocr_confidence=True — this flag is
    intentionally surfaced to users, not hidden.

    Returns an empty list if OCR dependencies are unavailable or if
    rendering fails.
    """
    if not _OCR_AVAILABLE:
        logger.error("OCR unavailable — cannot process scanned PDF: %s", pdf_path)
        return []

    try:
        images = _pdf2image.convert_from_path(pdf_path, dpi=_DPI)
    except Exception as exc:
        logger.error("pdf2image failed to render '%s': %s", pdf_path, exc)
        return []

    rows: list[dict] = []
    for page_num, image in enumerate(images, start=1):
        try:
            page_rows = _ocr_page(image, page_num)
            rows.extend(page_rows)
        except Exception as exc:
            logger.warning("OCR failed on page %d: %s", page_num, exc)

    valid = [r for r in rows if r.get("narration") and r.get("amount") and r.get("date")]
    logger.info("OCR extraction: %d raw rows → %d valid (all low_ocr_confidence=True)", len(rows), len(valid))
    return valid


def _ocr_page(image: "Image.Image", page_num: int) -> list[dict]:
    """Run Tesseract on one rendered page image and parse the lines."""
    # PSM 6: assume a single uniform block — reasonable for tabular statements
    config = r"--oem 3 --psm 6"
    text: str = pytesseract.image_to_string(image, config=config, lang="eng")

    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        amounts = _AMOUNT_RE.findall(line)
        if not amounts:
            continue

        parsed_date = extract_date(line)
        if parsed_date is None:
            continue

        try:
            if len(amounts) >= 2:
                amount = float(amounts[-2].replace(",", ""))
            else:
                amount = float(amounts[0].replace(",", ""))
        except ValueError:
            continue

        if amount < 1.0:
            continue

        rows.append({
            "narration": line,
            "amount": amount,
            "date": parsed_date.isoformat(),
            "extracted_reference": extract_reference(line),
            "low_ocr_confidence": True,
        })

    return rows
