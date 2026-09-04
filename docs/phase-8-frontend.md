# Phase 8 — Frontend UI

## Objective
Build a web interface using React, Tailwind CSS v4, and Vite adhering to the "exception-first" philosophy and paper/ink accounting aesthetic.

## What was built
- `frontend/src/App.jsx`: Main dashboard container using `useReducer` for state management and polling. Default view switches to Exception Ledger upon batch completion.
- `frontend/src/screens/UploadScreen.jsx`: Drag-and-drop PDF uploader with honest status feedback (parsing, OCR fallback notice, matching).
- `frontend/src/screens/ExceptionLedger.jsx`: Primary view containing exception table, reason badges, confidence pills, expandable reasoning blocks, and action buttons (`Accept`, `Reject`, `Unmatch`).
- `frontend/src/screens/MatchedTransactions.jsx`: View showing confirmed exact and agent-accepted matches with expandable reasoning text.
- `frontend/src/screens/ReportHeader.jsx`: Ruled horizontal summary strip displaying match rate %, totals, and execution time.
- `frontend/src/components/ConfidenceBadge.jsx`, `MatchTypeTag.jsx`, `ReasoningBlock.jsx`: Reusable UI components.
- `frontend/src/index.css`: Custom design tokens in Tailwind v4 `@theme` (paper warm background `#FAF8F4`, ink text `#1A1A2E`, IBM Plex Mono for amounts/IDs, Inter for UI, Playfair Display for wordmark, and the single `resolveFlash` animation keyframe).

## Key decisions and why
- **Exception-First Focus**: Defaults navigation to the Exception Ledger so accounting reviewers spend zero time clicking through cleared items.
- **Single Motion Moment**: `resolveFlash` CSS animation runs when resolving an exception, providing subtle feedback without UI clutter.
- **Monospace vs Humanist Typography**: All currency amounts and reference IDs use IBM Plex Mono; agent explanations use humanist italic Inter font.

## How to verify it
Run Vite dev server or build:
```powershell
cd frontend
npm run build
```
Build succeeds cleanly in ~500ms with zero errors.

## Known limitations / deferred work
- Real-time confidence threshold slider updates `PATCH /api/v1/config/threshold`.

## Depends on / feeds into
Consumes all FastAPI backend endpoints from Phases 2–7.
