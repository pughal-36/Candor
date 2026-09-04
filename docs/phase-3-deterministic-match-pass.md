# Phase 3 — Deterministic Match Pass

## Objective
Implement an exact, zero-LLM matching pass that resolves high-confidence matches using exact reference numbers, net amounts, and order gross amounts within tight tolerance windows.

## What was built
- `backend/app/matching/deterministic.py`:
  - Matches `bank_row.extracted_reference == settlement.reference_number`.
  - Enforces `|bank_row.amount - settlement.amount| <= ₹1.00`.
  - Enforces `settlement.gross_amount == order.amount` (within ₹1.00 tolerance).
  - Enforces date proximity (`|order.date - settlement.date| <= 1 day`).
  - Separates normal statement rows from `low_ocr_confidence` rows (which automatically bypass exact matching).

## Key decisions and why
- **Deterministic First**: Resolves clean e-commerce transactions instantly without LLM latency or API cost.
- **Strict Guardrails**: Exact matching strictly requires matching reference numbers and amount tolerances. Any variance is passed downstream.

## How to verify it
Run automated unit tests:
```powershell
.venv\Scripts\pytest tests/test_deterministic.py -v
```
All 9 unit tests pass, verifying exact matches, tolerance boundaries, and reference mismatches.

## Known limitations / deferred work
- Hardcoded date window of 1 day between order creation and gateway settlement payout.

## Depends on / feeds into
Consumes extracted statement rows from Phase 2. Feeds unmatched rows to Phase 4 (Agent fuzzy match pass).
