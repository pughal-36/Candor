# Phase 4 — Agent Fuzzy Match Pass

## Objective
Use an LLM agent powered by Google Gemini function-calling to analyze ambiguous bank statement rows, search real database tables via tools, and propose candidate matches with confidence scores and reasoning.

## What was built
- `backend/app/matching/agent.py`:
  - Built using the official `google-genai` SDK (`google.genai`).
  - Strict non-negotiable: `temperature = 0` for deterministic, repeatable agent decisions.
  - Implements 5 database query tools (`get_settlements_by_date_range`, `get_settlements_by_amount_range`, `get_orders_by_date_range`, `get_orders_by_amount_range`, `find_settlement_by_partial_reference`).
  - Output parsed into structured `AgentMatchResult` (settlement ID, order ID, confidence, reasoning).

## Key decisions and why
- **Tool-Calling Only**: The agent is forbidden from memory-based reasoning or hallucinating IDs/amounts. It can only cite UUIDs returned by tool executions.
- **Migration to `google-genai`**: Built directly on the current official Google GenAI SDK to ensure zero deprecation warnings and long-term stability.

## How to verify it
Inspect agent execution in `pipeline.py` or trigger fuzzy matching on an unmatched bank row with a partial UTR reference. The agent will execute tool calls and output structured JSON.

## Known limitations / deferred work
- Max tool rounds capped at 10 to prevent infinite looping on difficult edge cases.

## Test Data Callout (Matching Engine Upgrade)
- The initial happy-path sample data resolved entirely through the 1:1 deterministic pass. To properly test and demonstrate the subset-sum layer, the agent pass, and the aging exception ledger:
  - Added **1 multi-order bundled settlement** (`setl_011` matching `ORD-2024-0011` + `ORD-2024-0012` via subset-sum layer).
  - Added **1 unmatched credit** (`setl_012`) with no valid match to exercise the continuous aging exception ledger.
- Note: Happy-path sample data was deliberately supplemented so that subset-sum, agent fuzzy matching, and aging exception handling are fully tested and demonstrable.

## Depends on / feeds into
Receives unmatched rows from Phase 3 (Deterministic & Subset-Sum Pass). Feeds proposed candidate matches into Phase 5 (Verification pass).
