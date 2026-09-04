# Candor — System Overview & Architecture

Candor is a deterministic-first payment reconciliation agent built for Indian e-commerce merchants. It reconciles bank statement credits against Razorpay payment gateway settlements and internal store orders.

## Key Principles
1. **Deterministic-First**: Exact matches (matching reference numbers, amounts, and dates) are resolved instantly without LLM latency or cost.
2. **LLM Fuzzy Match (Temperature 0)**: Ambiguous transactions are processed by a Google Gemini agent using function-calling tools to query real database tables.
3. **Deterministic Verification Gate**: Every agent-proposed match must pass independent checks (ID existence and arithmetic verification: `settlement.amount + settlement.fee == order.amount`) before being accepted.
4. **Honest Exception Ledger**: Transactions that fail matching or verification are never silently dropped; they land on an Exception Ledger with explicit reason codes and reasoning for human review.
5. **Exception-First UI**: A custom React + Tailwind CSS dashboard styled after ledger paper and ink, prioritizing exceptions over cleared matches.

---

## Phase Documentation Index

1. [Phase 1 — Schema & Seed Data](phase-1-schema-and-seed-data.md)
2. [Phase 2 — Bank Statement Ingestion](phase-2-bank-statement-ingestion.md)
3. [Phase 3 — Deterministic Match Pass](phase-3-deterministic-match-pass.md)
4. [Phase 4 — Agent Fuzzy Match Pass](phase-4-agent-fuzzy-match-pass.md)
5. [Phase 5 — Verification Pass](phase-5-verification-pass.md)
6. [Phase 6 — Exception Ledger](phase-6-exception-ledger.md)
7. [Phase 7 — Reporting Layer](phase-7-reporting-layer.md)
8. [Phase 8 — Frontend UI](phase-8-frontend.md)
