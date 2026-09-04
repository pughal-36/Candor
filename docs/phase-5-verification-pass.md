# Phase 5 — Verification Pass

## Objective
Implement an independent, deterministic verification gate that validates every match proposed by the LLM agent before it can be written to the `matches` table.

## What was built
- `backend/app/matching/verification.py`:
  - **Check 1 (ID Existence)**: Verifies that cited `settlement_id` and `order_id` exist in the database. Prevents hallucinated IDs.
  - **Check 2 (Amount Arithmetic)**: Validates `settlement.amount + settlement.fee == order.amount` (within ₹2.00 tolerance). Prevents mathematically incorrect matches.

## Key decisions and why
- **Zero Trust in LLM Output**: Even if Gemini returns a 99% confidence score, if the cited IDs do not exist or arithmetic fails, the match is rejected and routed to the exception ledger.

## How to verify it
Run automated unit tests:
```powershell
.venv\Scripts\pytest tests/test_verification.py -v
```
All 6 unit tests pass, verifying ID rejection, arithmetic mismatch rejection (e.g. ₹9,400 + ₹300 != ₹10,000), and clean match acceptance.

## Known limitations / deferred work
- Tolerance set to ₹2.00 to account for standard gateway fee rounding.

## Depends on / feeds into
Receives agent proposed matches from Phase 4. Accepted matches go to `matches` table; rejected proposals feed Phase 6 (Exception ledger).
