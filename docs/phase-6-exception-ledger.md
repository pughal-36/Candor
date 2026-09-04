# Phase 6 — Exception Ledger

## Objective
Persist every unresolved transaction into a structured Exception Ledger with explicit machine-readable reason codes, human-readable explanations, agent candidate suggestions, and human review resolution endpoints.

## What was built
- `backend/app/exceptions/ledger.py`: Handles exception recording with reason codes (`below_threshold`, `verification_failed`, `low_ocr_confidence`, `no_candidate`, `no_bank_row`, `no_settlement`).
- `backend/app/api/routes/exceptions_route.py`: `PATCH /api/v1/exception/{id}` for human reviewer action (`accepted`, `rejected`, `unmatched`).

## Key decisions and why
- **No Silent Drops**: Every transaction that fails exact matching, agent confidence, or verification MUST have a record in `exceptions` with a clear reason.

## How to verify it
Query `exceptions` table after running a batch, or test resolution endpoint:
```powershell
# PATCH resolution test
curl -X PATCH http://localhost:8000/api/v1/exception/<id> -H "Content-Type: application/json" -d '{"resolution": "accepted"}'
```

## Known limitations / deferred work
- Manual resolution records reviewer identity (`resolved_by`) and timestamp (`resolved_at`).

## Depends on / feeds into
Receives failed/unmatched items from Phase 2, 4, and 5. Feeds data into Phase 7 (Reporting) and Phase 8 (Frontend UI).
