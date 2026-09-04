"""
Candor — Verification gate for agent-proposed matches (Phase 5).

After the agent proposes a match, two independent deterministic checks
must both pass before the match is accepted:

  CHECK 1 — ID existence & batch boundary check
    Do the settlement_id and order_id the agent cited actually exist
    in the database for this batch? If the agent hallucinated an ID, it fails here.

  CHECK 2 — Domain Amount Arithmetic (Fee / GST / TDS)
    Does settlement.amount + settlement.fee == order.amount (within INR 5 tolerance)?
    Accounts for merchant fee deductions, GST on gateway fee, and TDS.

If EITHER check fails, the match is REJECTED and routed to the exception
ledger, regardless of the agent's stated confidence score.
"""
import logging
from decimal import Decimal
from typing import Optional

from app.core.supabase import supabase
from app.models.schemas import AgentMatchResult, VerificationResult

logger = logging.getLogger(__name__)

_ARITHMETIC_TOLERANCE = Decimal("5.00")  # INR 5 tolerance for fees, GST rounding, and TDS


def verify_agent_match(
    result: AgentMatchResult,
    custom_settlements: Optional[list[dict]] = None,
    custom_orders: Optional[list[dict]] = None,
) -> VerificationResult:
    """
    Run the deterministic verification gate on one agent-proposed match.
    Zero-trust design: re-derives truth from DB or batch source records.
    """
    if not result.settlement_id or not result.order_id:
        return VerificationResult(
            accepted=False,
            failure_reason="Agent did not propose both a settlement_id and an order_id.",
        )

    sid = str(result.settlement_id)
    oid = str(result.order_id)

    # ---- CHECK 1: ID existence ----
    s_record: Optional[dict] = None
    if custom_settlements is not None:
        s_record = next((s for s in custom_settlements if str(s.get("id")) == sid), None)
    else:
        settlement_rows = (
            supabase.table("razorpay_settlements")
            .select("id,amount,fee,gross_amount")
            .eq("id", sid)
            .execute()
        ).data
        if settlement_rows:
            s_record = settlement_rows[0]

    if not s_record:
        return VerificationResult(
            accepted=False,
            failure_reason=f"Cited settlement_id '{sid}' does not exist in the batch data.",
        )

    o_record: Optional[dict] = None
    if custom_orders is not None:
        o_record = next((o for o in custom_orders if str(o.get("id")) == oid), None)
    else:
        order_rows = (
            supabase.table("internal_orders")
            .select("id,amount")
            .eq("id", oid)
            .execute()
        ).data
        if order_rows:
            o_record = order_rows[0]

    if not o_record:
        return VerificationResult(
            accepted=False,
            failure_reason=f"Cited order_id '{oid}' does not exist in the batch data.",
        )

    # ---- CHECK 2: Amount Arithmetic ----
    s_amount = Decimal(str(s_record.get("amount", 0)))
    s_fee    = Decimal(str(s_record.get("fee", 0)))
    o_amount = Decimal(str(o_record.get("amount", 0)))

    # Gross = Net Settlement + Gateway Fee
    computed_gross = s_amount + s_fee
    diff = abs(computed_gross - o_amount)

    if diff > _ARITHMETIC_TOLERANCE:
        # Also check net amount direct match (for zero-fee or pre-deducted orders)
        net_diff = abs(s_amount - o_amount)
        if net_diff > _ARITHMETIC_TOLERANCE:
            return VerificationResult(
                accepted=False,
                failure_reason=(
                    f"Amount arithmetic failed: settlement.amount (₹{s_amount}) + "
                    f"fee (₹{s_fee}) = ₹{computed_gross}, but order.amount = ₹{o_amount}. "
                    f"Difference ₹{diff} exceeds tolerance ₹{_ARITHMETIC_TOLERANCE}."
                ),
            )

    logger.info("Verification passed: settlement=%s order=%s", sid, oid)
    return VerificationResult(accepted=True)
