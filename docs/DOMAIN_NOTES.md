# Candor — Domain Reconciliation Notes

## Overview
Bank reconciliation for Indian e-commerce merchants operates across three distinct systems that rarely agree on exact strings or dates:
1. **Bank Statements (PDF)**: Real-time credit logs with raw, mangled narration strings, character truncation, and OCR variance.
2. **Razorpay Settlement Reports (CSV)**: Payment gateway payout feeds containing payout IDs, net payout amounts, gateway fees, GST on fees, and UTR reference numbers.
3. **Internal Merchant Invoices / Orders (CSV)**: Enterprise ERP / store records storing gross order totals, customer names, order IDs, and transaction timestamps.

---

## 1. Normalized UTR / Reference Matching
- **The Problem**: Bank narrations frequently truncate, reformat, or insert spaces into UTR reference numbers (e.g. `CMS/ Razorpay / UTR 2024 0701 00001` vs gateway UTR `UTR2024070100001`).
- **Our Approach**: Deterministic preprocessing strips spaces, dashes, punctuation, and casing (`_normalize_ref`) before exact substring matching, resolving the majority of UTR-linked payouts without incurring LLM latency.

---

## 2. Gateway Fee, GST, & TDS Netting Arithmetic
- **The Problem**: A bank credit never equals the gross order total. The net payout is computed as:
  $$\text{Net Settlement} = \text{Order Gross Amount} - \text{Gateway Fee} - \text{GST on Fee} - \text{TDS}$$
- **Our Approach**: The verification pass and agent reasoning explicitly validate this arithmetic relationship ($|(\text{Settlement Net} + \text{Fee}) - \text{Order Gross}| \le \text{Tolerance}$), rejecting matches where amounts fail accounting reconciliation regardless of stated AI confidence.

---

## 3. Settlement Lag (T+1 / T+2 Cycles)
- **The Problem**: Gateway payouts do not settle on the same day an order is placed. Payouts arrive $1$ to $3$ business days later.
- **Our Approach**: Matching windows enforce a configurable date offset ($0 \le \text{settlement\_date} - \text{order\_date} \le 3\text{ days}$), allowing accurate matching without forcing same-day constraints.

---

## 4. Partial Settlements & Refund Netting
- **The Problem**: Merchant payouts can be reduced when prior period refunds or chargebacks are netted against current payouts, or when high-value orders settle across split payouts.
- **Our Approach**: Unmatched items failing exact thresholds route to the LLM agent, which inspects candidate settlement and order history within the batch to reconstruct multi-row or refund-adjusted explanations.

---

## 5. Matching Engine & Test Data Supplementation Callout (Phase 4 Upgrade)
- **Regex UTR Pattern Matching**: Narrations embed UTRs with dynamic prefixes (`CMS/`, `NEFT-RZP-PARTIAL-`, `IMPS-RAZORPAY-`). UTR tokens are extracted dynamically via `re.search(r"UTR\d+", narration, re.IGNORECASE)` without hardcoding digit length.
- **Generic Fee Arithmetic**: Verified per row using actual `gross_amount - fee == amount` without hardcoding fee percentage.
- **Subset-Sum Layer**: Bounded combinatorial search (`_subset_sum_search`) searches unmatched order pools (bounded to 15-20 candidate orders within date window) for multi-order bundled settlements (e.g. `setl_011` matching `ORD-2024-0011` + `ORD-2024-0012`).
- **Reconstructed Arithmetic Bridge**: Prominently surfaces the full accounting formula for every match: `Order A (₹8,000) + Order B (₹7,300) = ₹15,300 gross − ₹300 (fee) = ₹15,000 net → matches bank credit of ₹15,000`.
- **Continuous Aging Exception Ledger**: Tracks `first_seen_batch_id` and `days_open`, carrying forward unresolved items across batches sorted by `days_open` descending.
- **Test Data Supplementation**: Sample CSV test datasets were deliberately supplemented with multi-order bundled settlements (`setl_011`) and unmatched credits (`setl_012`) to rigorously exercise the subset-sum combinatorial layer and continuous aging exception ledger.

