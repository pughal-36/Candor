"""
Candor — Deterministic exact-match pass (Phase 3).

Matches bank statement rows to Razorpay settlements + internal orders using
domain-grounded accounting rules — no LLM involved:

  1. UTR pattern extraction & normalization: UTR tokens (UTR followed by digits)
     are extracted via regex pattern matching (re.search(r"UTR\d+", narration))
     and normalized (uppercase, stripped whitespace) before comparison.
  2. Generic fee arithmetic verification: gross_amount - fee == amount per row.
  3. Reference match required: Never match on net amount alone without UTR match.
  4. Subset-sum combinatorial layer: Resolves many-to-one settlements where
     gross_amount equals the sum of multiple unmatched orders within date window.
  5. Bridge reconstruction: Reconstructs exact arithmetic for all matches.
"""
import itertools
import logging
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from app.core.supabase import supabase

logger = logging.getLogger(__name__)

_AMOUNT_TOLERANCE = Decimal("1.00")   # INR 1 rounding allowance
_DATE_WINDOW_DAYS = 3                 # T+1 / T+2 / T+3 settlement cycle allowance


def extract_utr_from_narration(narration: Optional[str]) -> str:
    """Extract UTR token (UTR followed by digits) from free-text narration using regex pattern match."""
    if not narration:
        return ""
    match = re.search(r"UTR\d+", str(narration), re.IGNORECASE)
    if match:
        return match.group(0).strip().upper()
    return ""


def _normalize_ref(ref_str: Optional[str]) -> str:
    """Normalize UTR / reference number by stripping non-alphanumeric chars and uppercasing."""
    if not ref_str:
        return ""
    utr = extract_utr_from_narration(ref_str)
    if utr:
        return utr
    return re.sub(r"[^A-Za-z0-9]", "", ref_str).upper()


def _amounts_match(a: float, b: float, tolerance: Decimal = _AMOUNT_TOLERANCE) -> bool:
    return abs(Decimal(str(a)) - Decimal(str(b))) <= tolerance


def _is_settlement_arithmetic_valid(s: dict) -> bool:
    """Verify gross_amount - fee == amount using the actual fee value in that row."""
    try:
        gross = Decimal(str(s.get("gross_amount", 0)))
        fee = Decimal(str(s.get("fee", 0)))
        net = Decimal(str(s.get("amount", 0)))
        return abs((gross - fee) - net) <= Decimal("0.01")
    except Exception:
        return False


def build_bridge_summary(
    gross_amount: float,
    fee: float,
    net_amount: float,
    bank_amount: float,
    orders: list[dict],
) -> str:
    """Construct exact reconstructed arithmetic bridge summary."""
    gross_dec = Decimal(str(gross_amount))
    fee_dec = Decimal(str(fee))
    net_dec = Decimal(str(net_amount))
    bank_dec = Decimal(str(bank_amount))

    if len(orders) > 1:
        order_parts = [
            f"Order {o.get('order_id', o.get('id', ''))} (₹{Decimal(str(o['amount'])):,.2f})"
            for o in orders
        ]
        order_sum_str = " + ".join(order_parts)
        orders_prefix = f"{order_sum_str} = ₹{gross_dec:,.2f} gross. "
    elif len(orders) == 1:
        orders_prefix = f"Order {orders[0].get('order_id', orders[0].get('id', ''))} (₹{gross_dec:,.2f} gross) → "
    else:
        orders_prefix = ""

    bridge = (
        f"{orders_prefix}₹{gross_dec:,.2f} gross − ₹{fee_dec:,.2f} (fee) = ₹{net_dec:,.2f} net "
        f"→ matches bank credit of ₹{bank_dec:,.2f}"
    )
    return bridge


def _subset_sum_search(
    target_gross: Decimal,
    candidate_orders: list[dict],
    max_pool: int = 20,
    max_k: int = 5,
) -> list[list[dict]]:
    """
    Search for combinations of candidate orders (bounded at max_pool) whose sum equals target_gross.
    Returns list of matching order subsets.
    """
    pool = candidate_orders[:max_pool]
    valid_subsets = []
    for r in range(2, min(len(pool) + 1, max_k + 1)):
        for combo in itertools.combinations(pool, r):
            combo_sum = sum(Decimal(str(o["amount"])) for o in combo)
            if abs(combo_sum - target_gross) <= Decimal("0.01"):
                valid_subsets.append(list(combo))
    return valid_subsets


def run_deterministic_pass(
    batch_id: str,
    custom_settlements: Optional[list[dict]] = None,
    custom_orders: Optional[list[dict]] = None,
) -> dict:
    """
    Run domain-grounded exact-match and subset-sum logic for bank_statement rows in a batch.

    Returns:
        matched                  — list of match records with bridge_summary
        unmatched_bank_rows      — rows that need the agent (or exception)
        unmatched_settlements    — settlement dicts with no bank match yet
        unmatched_orders         — order dicts with no match yet
        ambiguous_subsets        — subset-sum candidates requiring agent reasoning
    """
    bank_rows = (
        supabase.table("bank_statement")
        .select("*")
        .eq("batch_id", batch_id)
        .execute()
    ).data or []

    if custom_settlements is not None:
        settlements = custom_settlements
    else:
        settlements = (supabase.table("razorpay_settlements").select("*").execute()).data or []

    if custom_orders is not None:
        orders = custom_orders
    else:
        orders = (supabase.table("internal_orders").select("*").execute()).data or []

    # 1. Build Normalized Reference Index for Settlements
    settlement_by_norm_ref: dict[str, dict] = {}
    for s in settlements:
        raw_ref = s.get("reference_number")
        norm_ref = _normalize_ref(raw_ref)
        if norm_ref:
            settlement_by_norm_ref[norm_ref] = s

    matched: list[dict] = []
    used_settlement_ids: set[str] = set()
    used_order_ids: set[str] = set()
    used_bank_row_ids: set[str] = set()
    ambiguous_subsets: list[dict] = []

    normal_rows = [r for r in bank_rows if not r.get("low_ocr_confidence")]
    ocr_rows    = [r for r in bank_rows if r.get("low_ocr_confidence")]

    for row in normal_rows:
        narration = row.get("narration", "")
        raw_ref = row.get("extracted_reference") or narration
        bank_utr = extract_utr_from_narration(narration) or _normalize_ref(raw_ref)

        # REQUIRE reference number match — never match on amount alone
        matching_settlement: Optional[dict] = None
        if bank_utr:
            for s_norm_ref, s in settlement_by_norm_ref.items():
                if s["id"] in used_settlement_ids:
                    continue
                # Match extracted UTR token or normalized reference string
                if (bank_utr == s_norm_ref) or (len(bank_utr) >= 8 and (bank_utr in s_norm_ref or s_norm_ref in bank_utr)):
                    if _amounts_match(row["amount"], s["amount"]):
                        # Verify generic fee arithmetic balance on settlement row
                        if _is_settlement_arithmetic_valid(s):
                            matching_settlement = s
                            break

        if not matching_settlement:
            continue

        # Get settlement gross amount for order matching
        s_gross = Decimal(str(matching_settlement.get("gross_amount") or (matching_settlement["amount"] + matching_settlement.get("fee", 0.0))))

        try:
            s_date = date.fromisoformat(str(matching_settlement["date"]))
        except ValueError:
            s_date = date.today()

        # Find eligible unmatched orders within date window (order.date <= settlement.date <= order.date + 3)
        eligible_orders: list[dict] = []
        for o in orders:
            if o["id"] in used_order_ids:
                continue
            try:
                o_date = date.fromisoformat(str(o["date"]))
            except ValueError:
                o_date = s_date
            days_diff = (s_date - o_date).days
            if -1 <= days_diff <= _DATE_WINDOW_DAYS:
                eligible_orders.append(o)

        # Step A: Check 1:1 single order gross_amount match
        single_order_match: Optional[dict] = None
        for o in eligible_orders:
            o_amt = Decimal(str(o["amount"]))
            if abs(o_amt - s_gross) <= Decimal("0.01"):
                single_order_match = o
                break

        if single_order_match:
            bridge = build_bridge_summary(
                gross_amount=float(s_gross),
                fee=float(matching_settlement.get("fee", 0.0)),
                net_amount=float(matching_settlement.get("amount", 0.0)),
                bank_amount=float(row.get("amount", 0.0)),
                orders=[single_order_match],
            )
            matched.append({
                "bank_row_id":   row["id"],
                "settlement_id": matching_settlement["id"],
                "order_id":      single_order_match["id"],
                "order_ids":     [single_order_match["id"]],
                "match_type":    "exact",
                "confidence":    1.0,
                "bridge_summary": bridge,
            })
            used_settlement_ids.add(matching_settlement["id"])
            used_order_ids.add(single_order_match["id"])
            used_bank_row_ids.add(row["id"])
            logger.info("Deterministic 1:1 match: bank_row=%s settlement=%s order=%s", row["id"], matching_settlement["id"], single_order_match["id"])
            continue

        # Step B: Subset-Sum layer for many-to-one settlements (Requirement 1.3)
        matching_subsets = _subset_sum_search(s_gross, eligible_orders, max_pool=20)
        if len(matching_subsets) == 1:
            subset_orders = matching_subsets[0]
            bridge = build_bridge_summary(
                gross_amount=float(s_gross),
                fee=float(matching_settlement.get("fee", 0.0)),
                net_amount=float(matching_settlement.get("amount", 0.0)),
                bank_amount=float(row.get("amount", 0.0)),
                orders=subset_orders,
            )
            matched.append({
                "bank_row_id":   row["id"],
                "settlement_id": matching_settlement["id"],
                "order_id":      subset_orders[0]["id"],
                "order_ids":     [o["id"] for o in subset_orders],
                "match_type":    "subset_sum",
                "confidence":    1.0,
                "bridge_summary": bridge,
            })
            used_settlement_ids.add(matching_settlement["id"])
            for o in subset_orders:
                used_order_ids.add(o["id"])
            used_bank_row_ids.add(row["id"])
            logger.info("Deterministic subset-sum match: bank_row=%s settlement=%s orders=%d", row["id"], matching_settlement["id"], len(subset_orders))
            continue
        elif len(matching_subsets) > 1:
            # Multiple subsets sum to target — pass candidate pool to agent for reasoning
            ambiguous_subsets.append({
                "bank_row": row,
                "settlement": matching_settlement,
                "eligible_orders": eligible_orders[:20],
                "subsets": matching_subsets,
            })

    unmatched_bank_rows = [r for r in normal_rows if r["id"] not in used_bank_row_ids] + ocr_rows
    unmatched_settlements = [s for s in settlements if s["id"] not in used_settlement_ids]
    unmatched_orders = [o for o in orders if o["id"] not in used_order_ids]

    logger.info(
        "Deterministic pass — matched: %d | unmatched bank rows: %d | unmatched settlements: %d | ambiguous subsets: %d",
        len(matched), len(unmatched_bank_rows) - len(ocr_rows), len(unmatched_settlements), len(ambiguous_subsets),
    )

    return {
        "matched": matched,
        "unmatched_bank_rows": unmatched_bank_rows,
        "unmatched_settlements": unmatched_settlements,
        "unmatched_orders": unmatched_orders,
        "ambiguous_subsets": ambiguous_subsets,
    }

