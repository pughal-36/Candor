"""
GET  /config/threshold  — read the current confidence threshold
PATCH /config/threshold — update it (reflected immediately in the pipeline)

The threshold is stored in the `config` DB table so changes persist
across restarts and are visible in the UI. This satisfies the
non-negotiable in the build prompt: threshold must be visible and
tunable, not a hidden value baked into a prompt string.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.supabase import supabase
from app.core.config import settings
from app.models.schemas import ThresholdResponse, ThresholdUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

_KEY = "confidence_threshold"


@router.get("/config/threshold", response_model=ThresholdResponse)
def get_threshold() -> ThresholdResponse:
    """Return the current confidence threshold from the database."""
    result = supabase.table("config").select("value,description").eq("key", _KEY).execute()
    if not result.data:
        return ThresholdResponse(
            value=settings.confidence_threshold,
            description="Default threshold from environment variable.",
        )
    row = result.data[0]
    return ThresholdResponse(value=float(row["value"]), description=row["description"] or "")


@router.patch("/config/threshold", response_model=ThresholdResponse)
def update_threshold(body: ThresholdUpdate) -> ThresholdResponse:
    """
    Update the confidence threshold.
    The pipeline always reads the threshold from the DB at runtime,
    so this change takes effect on the next batch immediately.
    """
    supabase.table("config").upsert({
        "key": _KEY,
        "value": str(body.value),
        "description": (
            "Minimum confidence score (0–1) for the LLM fuzzy-match pass to "
            "auto-accept a match. Anything below routes to the exception ledger."
        ),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    logger.info("Confidence threshold updated to %.0f%%", body.value * 100)
    return ThresholdResponse(
        value=body.value,
        description="Confidence threshold updated. Takes effect on the next batch.",
    )
