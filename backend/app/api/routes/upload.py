"""
POST /upload-batch and POST /upload-statement

Accepts user-uploaded Bank Statement PDF, Razorpay Settlements CSV, and Internal Orders CSV.
Validates file structure, parses data into Supabase, and executes the reconciliation pipeline.
"""
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.core.supabase import supabase, upload_file_to_storage
from app.ingestion.statement_ingestor import ingest_statement
from app.ingestion.settlements_ingestor import ingest_settlements
from app.ingestion.orders_ingestor import ingest_orders
from app.matching.pipeline import run_pipeline
from app.models.schemas import UploadResponse

router = APIRouter()
logger = logging.getLogger(__name__)

_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/upload-batch", response_model=UploadResponse, status_code=202)
async def upload_batch(
    background_tasks: BackgroundTasks,
    statement_file: UploadFile = File(..., description="PDF Bank Statement"),
    settlements_file: Optional[UploadFile] = File(None, description="Razorpay Settlements CSV"),
    orders_file: Optional[UploadFile] = File(None, description="Internal Orders CSV"),
    user_id: Optional[str] = Form(None),
) -> UploadResponse:
    """
    Accept 3 user-provided files (PDF bank statement, Razorpay settlements CSV, internal orders CSV),
    validate formats, ingest into DB, and start reconciliation pipeline.
    """
    logger.info("[UPLOAD BATCH] Received batch request | user_id=%s", user_id)

    # 1. Validate PDF statement
    stmt_filename = statement_file.filename or "statement.pdf"
    if not _is_pdf(statement_file, stmt_filename):
        raise HTTPException(status_code=400, detail="Bank statement must be a valid PDF file (.pdf).")

    pdf_bytes = await statement_file.read()
    if not pdf_bytes or len(pdf_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="Bank statement PDF is empty or exceeds the 20 MB limit.")

    # 2. Read settlements CSV if provided
    settlement_bytes: Optional[bytes] = None
    if settlements_file and settlements_file.filename:
        if not settlements_file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Razorpay settlements file must be a CSV file (.csv).")
        settlement_bytes = await settlements_file.read()

    # 3. Read orders CSV if provided
    order_bytes: Optional[bytes] = None
    if orders_file and orders_file.filename:
        if not orders_file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Internal orders file must be a CSV file (.csv).")
        order_bytes = await orders_file.read()

    # 4. Create batch record in DB
    try:
        batch_rec = {
            "filename": stmt_filename,
            "status": "pending",
        }
        if user_id:
            batch_rec["user_id"] = user_id

        result = supabase.table("batches").insert(batch_rec).execute()
        batch_id: str = result.data[0]["id"]
        logger.info("[UPLOAD BATCH] Created batch record | batch_id=%s", batch_id)
    except Exception as exc:
        logger.exception("Failed creating batch record: %s", exc)
        raise HTTPException(status_code=500, detail=f"Database error creating batch: {exc}")

    # Write PDF to storage
    try:
        storage_path = f"batches/{batch_id}/{stmt_filename}"
        upload_file_to_storage("statements", storage_path, pdf_bytes, statement_file.content_type or "application/pdf")
    except Exception as exc:
        logger.warning("Supabase Storage upload warning: %s", exc)

    # 5. Ingest files & Queue pipeline
    background_tasks.add_task(
        _process_multi_source_batch,
        batch_id=batch_id,
        pdf_bytes=pdf_bytes,
        settlement_bytes=settlement_bytes,
        order_bytes=order_bytes,
        user_id=user_id,
    )

    return UploadResponse(batch_id=batch_id, status="pending")


@router.post("/upload-statement", response_model=UploadResponse, status_code=202)
async def upload_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    """Legacy single PDF statement upload route."""
    return await upload_batch(
        background_tasks=background_tasks,
        statement_file=file,
        settlements_file=None,
        orders_file=None,
        user_id=None,
    )


def _process_multi_source_batch(
    batch_id: str,
    pdf_bytes: bytes,
    settlement_bytes: Optional[bytes] = None,
    order_bytes: Optional[bytes] = None,
    user_id: Optional[str] = None,
) -> None:
    """Background task: ingest statement + settlements + orders then run pipeline."""
    try:
        logger.info("[BATCH PROCESS] Step 1: Parsing Bank Statement PDF for batch %s", batch_id)
        ingest_statement(batch_id, pdf_bytes)

        settlements_data = None
        if settlement_bytes:
            logger.info("[BATCH PROCESS] Step 2: Ingesting Razorpay Settlements CSV for batch %s", batch_id)
            settlements_data = ingest_settlements(batch_id, settlement_bytes, user_id=user_id)

        orders_data = None
        if order_bytes:
            logger.info("[BATCH PROCESS] Step 3: Ingesting Internal Orders CSV for batch %s", batch_id)
            orders_data = ingest_orders(batch_id, order_bytes, user_id=user_id)

        logger.info("[BATCH PROCESS] Step 4: Running reconciliation pipeline for batch %s", batch_id)
        run_pipeline(batch_id, custom_settlements=settlements_data, custom_orders=orders_data)
        logger.info("[BATCH PROCESS] Reconciliation pipeline completed for batch %s", batch_id)

    except ValueError as val_err:
        logger.warning("[BATCH PROCESS] Validation error for batch %s: %s", batch_id, val_err)
        supabase.table("batches").update({
            "status": "error",
            "error_message": str(val_err),
        }).eq("id", batch_id).execute()

    except Exception as exc:
        logger.exception("[BATCH PROCESS] Pipeline execution failed for batch %s: %s", batch_id, exc)
        supabase.table("batches").update({
            "status": "error",
            "error_message": f"Pipeline error: {str(exc)}",
        }).eq("id", batch_id).execute()


def _is_pdf(file: UploadFile, filename: str) -> bool:
    return bool(
        (file.content_type and "pdf" in file.content_type.lower())
        or file.content_type in ("application/pdf", "application/octet-stream", "application/x-pdf")
        or filename.lower().endswith(".pdf")
    )
