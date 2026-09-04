"""
Candor — Reporting layer (Phase 7).

Computes match rate %, breakdown by match type, and processing time.
Numbers are computed from live DB state, not cached counters — so they
always reflect the actual outcome of the pipeline, not an approximation.
"""
import logging

from app.core.supabase import supabase

logger = logging.getLogger(__name__)


from datetime import datetime

def record_batch_report(batch_id: str, processing_time_seconds: float) -> dict:
    """Compute stats, log them, and return the stats dict."""
    stats = compute_stats(batch_id, processing_time_seconds)
    logger.info(
        "Batch %s — total: %d | exact: %d | agent: %d | exceptions: %d | "
        "match_rate: %.1f%% | time: %.2fs",
        batch_id,
        stats["total_bank_rows"],
        stats["exact_matches"],
        stats["agent_accepted_matches"],
        stats["exceptions"],
        stats["match_rate_pct"],
        stats["processing_time_seconds"],
    )
    return stats


def compute_stats(batch_id: str, processing_time_seconds: float = 0.0) -> dict:
    """
    Compute match statistics for a completed batch from live DB data.

    match_rate_pct = (exact + agent_accepted) / total_bank_rows * 100
    """
    if processing_time_seconds <= 0.0:
        batch_res = (
            supabase.table("batches")
            .select("created_at, completed_at")
            .eq("id", batch_id)
            .execute()
        )
        if batch_res.data and batch_res.data[0].get("created_at") and batch_res.data[0].get("completed_at"):
            try:
                t0 = datetime.fromisoformat(batch_res.data[0]["created_at"].replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(batch_res.data[0]["completed_at"].replace("Z", "+00:00"))
                processing_time_seconds = max(0.1, (t1 - t0).total_seconds())
            except Exception as err:
                logger.warning("Error calculating batch duration: %s", err)

    matches = (
        supabase.table("matches")
        .select("match_type")
        .eq("batch_id", batch_id)
        .execute()
    ).data or []

    exact = sum(1 for m in matches if m["match_type"] in ("exact", "subset_sum"))
    agent = sum(1 for m in matches if m["match_type"] == "agent_accepted")

    # Pending/unresolved exceptions — exact same logic as the Exception Ledger tab source of truth
    from app.api.routes.batches import get_exceptions
    try:
        active_exceptions = get_exceptions(batch_id)
        exceptions_count: int = len([e for e in active_exceptions if not e.get("resolution")])
    except Exception as exc_err:
        logger.warning("Error fetching active exceptions count: %s", exc_err)
        exceptions_count = 0

    bank_rows_result = (
        supabase.table("bank_statement")
        .select("id", count="exact")
        .eq("batch_id", batch_id)
        .execute()
    )
    total: int = bank_rows_result.count or 0

    matched = exact + agent
    rate = round((matched / total * 100), 1) if total > 0 else 0.0

    return {
        "total_bank_rows":          total,
        "exact_matches":            exact,
        "agent_accepted_matches":   agent,
        "exceptions":               exceptions_count,
        "match_rate_pct":           rate,
        "processing_time_seconds":  round(processing_time_seconds, 2),
    }

