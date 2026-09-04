"""
PATCH /exception/{id}

Human resolution of an exception ledger entry.
Accepted resolution values: 'accepted' | 'rejected' | 'unmatched'
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.supabase import supabase
from app.models.schemas import ExceptionResolution

router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/exception/{exception_id}")
def resolve_exception(exception_id: str, body: ExceptionResolution) -> dict:
    """Mark an exception as resolved by a human reviewer."""
    existing = supabase.table("exceptions").select("id").eq("id", exception_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail=f"Exception '{exception_id}' not found.")

    update = {
        "resolution": body.resolution,
        "resolved_by": body.resolved_by,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    # Drop None values — resolved_by is optional
    update = {k: v for k, v in update.items() if v is not None}

    updated = supabase.table("exceptions").update(update).eq("id", exception_id).execute()
    logger.info("Exception %s resolved as '%s' by '%s'", exception_id, body.resolution, body.resolved_by)
    return updated.data[0]
