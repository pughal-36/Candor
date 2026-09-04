# Phase 1 — Schema & Seed Data

## Objective
Establish the Supabase PostgreSQL database schema for Candor, including tables for bank statements, Razorpay settlements, internal merchant orders, matches, exceptions, and configuration parameters, along with representative Indian e-commerce seed data.

## What was built
- **Tables**:
  - `bank_statement`: Stores ingested bank statement rows with columns `batch_id`, `date`, `narration`, `amount`, `extracted_reference`, and boolean `low_ocr_confidence`.
  - `razorpay_settlements`: Gateway settlement feed with `payout_id`, `amount` (net), `fee`, `tax`, `gross_amount`, `date`, and `reference_number` (UTR/NEFT/IMPS).
  - `internal_orders`: Merchant store orders with `order_id`, `amount`, `customer`, `date`, and `payment_status`.
  - `matches`: Reconciled transaction pairs with `match_type` (`exact` or `agent_accepted`), `confidence`, and `reasoning`.
  - `exceptions`: Unresolved transactions ledger with mandatory `reason_code` (`below_threshold`, `verification_failed`, `low_ocr_confidence`, `no_candidate`, `no_bank_row`, `no_settlement`), agent candidate links, reasoning, and human resolution status (`accepted`, `rejected`, `unmatched`).
  - `config`: Key-value store for application parameters, starting with `confidence_threshold`.
  - `batches`: Metadata tracking uploaded PDF files and reconciliation status.
- **Seed Data**: 10 representative transactions across all three data sources demonstrating exact matches, fee deductions, garbled narrations, split payments, and missing settlements.

## Key decisions and why
- **`low_ocr_confidence` Flag**: Stored directly on `bank_statement` rows to ensure transparency when OCR is triggered.
- **Numeric Precision**: Used `NUMERIC(12, 2)` for monetary values to eliminate IEEE 754 floating-point inaccuracies.
- **Config Table**: Stored `confidence_threshold` in the database so that UI adjustments take effect on runtime without backend restarts.

## How to verify it
Query tables directly via Supabase SQL Editor:
```sql
SELECT count(*) FROM razorpay_settlements; -- 10 rows
SELECT count(*) FROM internal_orders;       -- 10 rows
```

## Known limitations / deferred work
- Seed data currently covers 10 transactions. Production databases would index reference numbers and dates for high-volume performance.

## Depends on / feeds into
Feeds into Phase 2 (Bank statement ingestion) and Phase 3 (Deterministic match pass).
