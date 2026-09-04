# Phase 7 — Reporting Layer

## Objective
Compute live reconciliation statistics for each uploaded batch, including match rate percentage, breakdown by match type (exact vs. agent), total exceptions, and total pipeline processing execution time.

## What was built
- `backend/app/reporting/stats.py`: `compute_stats()` queries live DB counts from `matches`, `exceptions`, and `bank_statement` tables. Calculates `match_rate_pct = (exact + agent_accepted) / total_bank_rows * 100`.
- `backend/app/api/routes/batches.py`: `GET /api/v1/batch/{id}/report` endpoint.

## Key decisions and why
- **Live DB Calculations**: Stats are computed directly from actual database rows rather than cached counters, guaranteeing numbers match the underlying tables exactly.

## How to verify it
Call `GET /api/v1/batch/{id}/report` for a completed batch ID.

## Known limitations / deferred work
- Processing time measures monotonic execution duration from statement ingestion start to completion.

## Depends on / feeds into
Consumes data from `matches`, `exceptions`, and `bank_statement`. Feeds stats into Phase 8 (Frontend ReportHeader).
