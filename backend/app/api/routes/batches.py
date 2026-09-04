"""
Batch query routes:

  GET /batch/{id}/status      — batch progress
  GET /batch/{id}/matches     — matched transactions
  GET /batch/{id}/exceptions  — exception ledger entries (sorted by confidence desc)
  GET /batch/{id}/report      — match rate / breakdown / processing time
"""
import logging

from fastapi import APIRouter, HTTPException

from app.core.supabase import supabase, safe_execute
from app.reporting.stats import compute_stats

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_batch_or_404(batch_id: str) -> dict:
    result = safe_execute(supabase.table("batches").select("*").eq("id", batch_id))
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")
    return result.data[0]


@router.get("/batch/{batch_id}/status")
def get_batch_status(batch_id: str) -> dict:
    """Return current batch status (pending / parsing / matching / done / error)."""
    return _get_batch_or_404(batch_id)


@router.get("/batch/{batch_id}/matches")
def get_matches(batch_id: str) -> list:
    """Return all matched transactions for the batch with bank statement details and bridge summaries."""
    _get_batch_or_404(batch_id)
    result = safe_execute(
        supabase.table("matches")
        .select("*, bank_statement(date, narration, amount, extracted_reference)")
        .eq("batch_id", batch_id)
        .order("created_at")
    )
    matches = []
    for item in (result.data or []):
        bs = item.get("bank_statement") or {}
        matches.append({
            "id": item["id"],
            "batch_id": item["batch_id"],
            "bank_row_id": item["bank_row_id"],
            "settlement_id": item.get("settlement_id"),
            "order_id": item.get("order_id"),
            "match_type": item["match_type"],
            "confidence": item.get("confidence") if item["match_type"] == "agent_accepted" else 1.0,
            "reasoning": item.get("reasoning"),
            "bridge_summary": item.get("reasoning"),
            "created_at": item.get("created_at"),
            "date": bs.get("date"),
            "narration": bs.get("narration"),
            "amount": bs.get("amount"),
            "extracted_reference": bs.get("extracted_reference"),
        })
    return matches


@router.get("/batch/{batch_id}/exceptions")
def get_exceptions(batch_id: str) -> list:
    """
    Return the continuous aging exception ledger.
    Carries forward unresolved exceptions from previous batches,
    excluding any items that have been successfully matched in the current batch.
    """
    _get_batch_or_404(batch_id)

    # Get matched bank_row_ids and settlement_ids for current batch
    matched_rows = safe_execute(
        supabase.table("matches").select("bank_row_id, settlement_id").eq("batch_id", batch_id)
    ).data or []
    matched_bank_ids = {m["bank_row_id"] for m in matched_rows if m.get("bank_row_id")}
    matched_settlement_ids = {m["settlement_id"] for m in matched_rows if m.get("settlement_id")}

    # Get extracted references for matched bank rows
    matched_refs = set()
    if matched_bank_ids:
        b_rows = safe_execute(
            supabase.table("bank_statement").select("extracted_reference, narration").in_("id", list(matched_bank_ids))
        ).data or []
        for r in b_rows:
            ref = r.get("extracted_reference") or r.get("narration") or ""
            if ref:
                matched_refs.add(ref.strip().upper())

    # Query current batch exceptions + any carried forward unresolved exceptions
    result = safe_execute(
        supabase.table("exceptions")
        .select("*, bank_statement(date, narration, amount, extracted_reference)")
        .or_(f"batch_id.eq.{batch_id},resolution.is.null")
        .order("created_at")
    )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    exceptions = []
    seen_ids = set()
    for item in (result.data or []):
        if item["id"] in seen_ids:
            continue

        # Skip if bank row or settlement has been matched in this batch
        if item.get("bank_row_id") in matched_bank_ids:
            continue
        if item.get("settlement_id") in matched_settlement_ids:
            continue

        bs = item.get("bank_statement") or {}
        e_ref = (bs.get("extracted_reference") or bs.get("narration") or "").strip().upper()
        if e_ref and any((m_ref in e_ref or e_ref in m_ref) for m_ref in matched_refs if len(m_ref) >= 8):
            continue

        seen_ids.add(item["id"])

        created_str = item.get("created_at")
        days_open = 0
        if created_str:
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                days_open = max(0, (now - dt).days)
            except Exception:
                days_open = 0

        exceptions.append({
            **item,
            "first_seen_batch_id": item.get("first_seen_batch_id") or item.get("batch_id"),
            "days_open": days_open,
            "date": bs.get("date"),
            "narration": bs.get("narration"),
            "amount": bs.get("amount"),
            "extracted_reference": bs.get("extracted_reference"),
        })

    # Sort by days_open descending by default (oldest unresolved first)
    exceptions.sort(key=lambda x: (x.get("resolution") is not None, -x.get("days_open", 0), -(x.get("agent_confidence") or 0)))
    return exceptions


@router.get("/batch/{batch_id}/report")
def get_report(batch_id: str) -> dict:
    """Return match rate, breakdown by type, and processing time."""
    batch = _get_batch_or_404(batch_id)
    if batch["status"] not in ("done", "error"):
        return {
            "status": batch["status"],
            "message": "Batch is still processing — check back shortly.",
        }
    return compute_stats(batch_id)
