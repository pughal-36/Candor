"""
Candor — Exception ledger writer (Phase 6).

Every unresolved transaction must land here with a REASON — not just an
absence of a match. The reasons are machine-readable (reason_code) and
human-readable (reason). This is the main value of Candor: honest
accounting of what couldn't be resolved and why.

reason_code values (must match the DB CHECK constraint):
  below_threshold   — agent confidence < threshold
  verification_failed — agent match failed the arithmetic/ID check
  low_ocr_confidence  — bank row extracted via OCR with low confidence
  no_candidate      — agent couldn't produce valid structured output
  no_bank_row       — settlement has no corresponding bank credit found
  no_settlement     — bank credit has no corresponding settlement found
"""
import logging
from typing import Optional

from app.core.supabase import supabase

logger = logging.getLogger(__name__)

_VALID_REASON_CODES = {
    "below_threshold",
    "verification_failed",
    "low_ocr_confidence",
    "no_candidate",
    "no_bank_row",
    "no_settlement",
}


def add_exception(
    batch_id: str,
    reason_code: str,
    reason: str,
    bank_row_id: Optional[str] = None,
    settlement_id: Optional[str] = None,
    order_id: Optional[str] = None,
    agent_candidate_settlement_id: Optional[str] = None,
    agent_candidate_order_id: Optional[str] = None,
    agent_confidence: Optional[float] = None,
    agent_reasoning: Optional[str] = None,
    first_seen_batch_id: Optional[str] = None,
) -> None:
    """
    Insert one entry into the exception ledger.
    Tracks first_seen_batch_id for continuous aging analysis across reconciliation runs.
    """
    if reason_code not in _VALID_REASON_CODES:
        raise ValueError(f"Invalid reason_code '{reason_code}'. Must be one of {_VALID_REASON_CODES}.")

    # Check for existing unresolved exception for this bank_row to carry forward first_seen_batch_id
    effective_first_seen = first_seen_batch_id or batch_id
    if bank_row_id:
        existing = (
            supabase.table("exceptions")
            .select("first_seen_batch_id, batch_id")
            .eq("bank_row_id", bank_row_id)
            .is_("resolution", "null")
            .execute()
        )
        if existing.data:
            effective_first_seen = existing.data[0].get("first_seen_batch_id") or existing.data[0].get("batch_id") or effective_first_seen

    record = {
        "batch_id":                       batch_id,
        "first_seen_batch_id":            effective_first_seen,
        "reason_code":                    reason_code,
        "reason":                         reason,
        "bank_row_id":                    bank_row_id,
        "settlement_id":                  settlement_id,
        "order_id":                       order_id,
        "agent_candidate_settlement_id":  agent_candidate_settlement_id,
        "agent_candidate_order_id":       agent_candidate_order_id,
        "agent_confidence":               agent_confidence,
        "agent_reasoning":                agent_reasoning,
    }
    # Strip None values — Supabase insert with None on FK columns can cause type errors
    record = {k: v for k, v in record.items() if v is not None}

    supabase.table("exceptions").insert(record).execute()
    logger.info(
        "Exception: batch=%s first_seen=%s reason_code=%s bank_row=%s",
        batch_id, effective_first_seen, reason_code, bank_row_id,
    )
