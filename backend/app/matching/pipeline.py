"""
Candor — Full reconciliation pipeline orchestrator (Phases 3–7).

Called as a FastAPI background task after statement and CSV sources have been uploaded.

Order:
  1. Deterministic exact-match pass
  2. Write exact matches to DB
  3. Agent fuzzy-match pass (only for unmatched rows)
  4. Verification gate on every agent proposal
  5. Write accepted agent matches; route failures to exception ledger
  6. OCR-flagged rows route directly to exception ledger
  7. Record processing stats, mark batch done
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.core.supabase import supabase
from app.core.config import settings
from app.matching.deterministic import run_deterministic_pass
from app.matching.agent import run_agent_match
from app.matching.verification import verify_agent_match
from app.exceptions.ledger import add_exception
from app.reporting.stats import record_batch_report

from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def run_pipeline(
    batch_id: str,
    custom_settlements: Optional[list[dict]] = None,
    custom_orders: Optional[list[dict]] = None,
) -> None:
    """Execute the full reconciliation pipeline for one uploaded batch."""
    start = time.monotonic()
    try:
        _set_status(batch_id, "matching")

        # Clear any prior matches or exceptions for this batch to ensure clean, idempotent runs
        supabase.table("matches").delete().eq("batch_id", batch_id).execute()
        supabase.table("exceptions").delete().eq("batch_id", batch_id).execute()

        # ---- Phase 3: Deterministic pass ----
        det = run_deterministic_pass(
            batch_id,
            custom_settlements=custom_settlements,
            custom_orders=custom_orders,
        )

        # Persist exact and subset-sum matches in a single bulk insert
        if det["matched"]:
            exact_records = [
                {
                    "batch_id":      batch_id,
                    "settlement_id": m["settlement_id"],
                    "bank_row_id":   m["bank_row_id"],
                    "order_id":      m["order_id"],
                    "match_type":    m["match_type"],
                    "confidence":    m.get("confidence", 1.0),
                    "reasoning":     m.get("bridge_summary"),
                }
                for m in det["matched"]
            ]
            supabase.table("matches").insert(exact_records).execute()

        # ---- Phase 4 + 5: Agent pass + verification gate (concurrent execution) ----
        threshold = _read_threshold()
        unmatched = det["unmatched_bank_rows"]

        if unmatched:
            workers = min(len(unmatched), 5)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(
                        _process_unmatched_row,
                        batch_id,
                        row,
                        threshold,
                        custom_settlements,
                        custom_orders,
                    )
                    for row in unmatched
                ]
                for future in as_completed(futures):
                    future.result()

        # ---- Phase 7: Reporting ----
        elapsed = time.monotonic() - start
        record_batch_report(batch_id, elapsed)

        _set_status(batch_id, "done", completed=True)
        logger.info("Pipeline done: batch=%s elapsed=%.2fs", batch_id, elapsed)

    except Exception as exc:
        logger.exception("Pipeline failed: batch=%s", batch_id)
        supabase.table("batches").update({
            "status":        "error",
            "error_message": str(exc),
        }).eq("id", batch_id).execute()


def _process_unmatched_row(
    batch_id: str,
    bank_row: dict,
    threshold: float,
    custom_settlements: Optional[list[dict]] = None,
    custom_orders: Optional[list[dict]] = None,
) -> None:
    """Run agent + verification on one unmatched bank statement row."""

    # OCR-flagged rows skip the agent and go straight to the exception ledger
    if bank_row.get("low_ocr_confidence"):
        add_exception(
            batch_id=batch_id,
            bank_row_id=bank_row["id"],
            reason_code="low_ocr_confidence",
            reason=(
                "Row was extracted via OCR with low confidence. "
                "The reference number may be unreliable — manual review required."
            ),
        )
        return

    # ---- Phase 4: Agent fuzzy match ----
    agent_result = run_agent_match(
        bank_row,
        custom_settlements=custom_settlements,
        custom_orders=custom_orders,
    )

    if agent_result is None:
        add_exception(
            batch_id=batch_id,
            bank_row_id=bank_row["id"],
            reason_code="no_candidate",
            reason="Agent could not produce a valid structured response for this row.",
        )
        return

    if agent_result.confidence < threshold:
        add_exception(
            batch_id=batch_id,
            bank_row_id=bank_row["id"],
            reason_code="below_threshold",
            reason=(
                f"Agent confidence {agent_result.confidence:.0%} is below the "
                f"configured threshold of {threshold:.0%}."
            ),
            agent_candidate_settlement_id=(
                str(agent_result.settlement_id) if agent_result.settlement_id else None
            ),
            agent_candidate_order_id=(
                str(agent_result.order_id) if agent_result.order_id else None
            ),
            agent_confidence=agent_result.confidence,
            agent_reasoning=agent_result.reasoning,
        )
        return

    # ---- Phase 5: Verification gate ----
    verification = verify_agent_match(
        agent_result,
        custom_settlements=custom_settlements,
        custom_orders=custom_orders,
    )

    if not verification.accepted:
        add_exception(
            batch_id=batch_id,
            bank_row_id=bank_row["id"],
            settlement_id=str(agent_result.settlement_id) if agent_result.settlement_id else None,
            order_id=str(agent_result.order_id) if agent_result.order_id else None,
            reason_code="verification_failed",
            reason=f"Verification gate rejected the agent match: {verification.failure_reason}",
            agent_candidate_settlement_id=(
                str(agent_result.settlement_id) if agent_result.settlement_id else None
            ),
            agent_candidate_order_id=(
                str(agent_result.order_id) if agent_result.order_id else None
            ),
            agent_confidence=agent_result.confidence,
            agent_reasoning=agent_result.reasoning,
        )
        return

    # Match accepted — write to matches table
    bridge = (
        f"Reconstructed Bridge: Settlement '{agent_result.settlement_id}' "
        f"and Order '{agent_result.order_id}' → matches bank credit of ₹{bank_row.get('amount', 0):,.2f}. "
        f"{agent_result.reasoning}"
    )
    supabase.table("matches").insert({
        "batch_id":      batch_id,
        "settlement_id": str(agent_result.settlement_id),
        "bank_row_id":   bank_row["id"],
        "order_id":      str(agent_result.order_id),
        "match_type":    "agent_accepted",
        "confidence":    agent_result.confidence,
        "reasoning":     bridge,
    }).execute()

    logger.info(
        "Agent match accepted: bank_row=%s settlement=%s order=%s confidence=%.0f%%",
        bank_row["id"], agent_result.settlement_id, agent_result.order_id,
        agent_result.confidence * 100,
    )


def _read_threshold() -> float:
    result = (
        supabase.table("config")
        .select("value")
        .eq("key", "confidence_threshold")
        .execute()
    )
    if result.data:
        return float(result.data[0]["value"])
    return settings.confidence_threshold


def _set_status(batch_id: str, status: str, completed: bool = False) -> None:
    update: dict = {"status": status}
    if completed:
        update["completed_at"] = datetime.now(timezone.utc).isoformat()
    supabase.table("batches").update(update).eq("id", batch_id).execute()
