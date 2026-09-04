import { useState } from 'react'

/**
 * LandingPage — Plain-language explanation of the merchant reconciliation pain
 * and Candor's deterministic-first + honest exception philosophy.
 *
 * Uses the same visual palette as the dashboard (ledger/paper theme, IBM Plex Mono,
 * Inter, Playfair Display).
 */
export default function LandingPage({ onGetStarted }) {
  return (
    <div className="min-h-screen" style={{ background: 'var(--color-paper-100)' }}>
      {/* Header / Nav */}
      <header
        className="flex items-center justify-between px-8 py-4 sticky top-0 z-20 border-b"
        style={{ background: 'var(--color-ink-900)', borderColor: 'var(--color-ink-800)' }}
      >
        <div className="flex items-center gap-3">
          <span className="font-display text-2xl tracking-tight" style={{ color: '#E8E4DC' }}>
            Candor
          </span>
          <span className="font-ledger text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(255,255,255,0.1)', color: '#C8C0B0' }}>
            v0.1.0
          </span>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onGetStarted}
            className="text-sm px-4 py-2 rounded transition-colors font-medium"
            style={{ background: '#E8E4DC', color: 'var(--color-ink-900)', border: 'none', cursor: 'pointer' }}
          >
            Launch Dashboard
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-4xl mx-auto px-6 py-16 text-center">
        <h1
          className="text-4xl md:text-5xl font-semibold mb-6 tracking-tight"
          style={{ fontFamily: 'var(--font-display)', color: 'var(--color-ink-900)', lineHeight: 1.15 }}
        >
          A merchant's money lives in three places that never agree.
        </h1>
        <p className="text-lg mb-8 max-w-2xl mx-auto" style={{ color: 'var(--color-ink-600)', lineHeight: 1.6 }}>
          Razorpay settlement reports, bank statement PDFs, and internal store invoices are separated by gateway fees, GST, TDS, T+2 settlement cycles, and mangled UTR numbers.
        </p>

        <div className="flex justify-center gap-4">
          <button
            onClick={onGetStarted}
            className="px-6 py-3 rounded text-base font-medium transition-all"
            style={{ background: 'var(--color-ink-900)', color: '#F5F2EC', border: 'none', cursor: 'pointer' }}
          >
            Start Reconciling Batch
          </button>
        </div>
      </section>

      {/* The Problem Table Strip */}
      <section className="max-w-5xl mx-auto px-6 py-8">
        <div className="rounded p-6" style={{ background: 'var(--color-paper-200)', border: '1px solid var(--color-paper-300)' }}>
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: 'var(--color-ink-500)' }}>
            Why Naive Auto-Reconciliation Fails
          </h3>
          <div className="grid md:grid-cols-3 gap-6 text-sm">
            <div>
              <div className="font-semibold mb-1" style={{ color: 'var(--color-ink-900)' }}>1. Razorpay Payouts</div>
              <p style={{ color: 'var(--color-ink-600)' }}>
                Contains payout IDs, net payout amounts, gateway fees, and UTR reference strings.
              </p>
            </div>
            <div>
              <div className="font-semibold mb-1" style={{ color: 'var(--color-ink-900)' }}>2. Bank Statement PDF</div>
              <p style={{ color: 'var(--color-ink-600)' }}>
                Raw credit narrations with truncated references, spaces, and OCR noise.
              </p>
            </div>
            <div>
              <div className="font-semibold mb-1" style={{ color: 'var(--color-ink-900)' }}>3. Internal Orders</div>
              <p style={{ color: 'var(--color-ink-600)' }}>
                Gross customer invoice totals before gateway fee deductions.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How Candor Works */}
      <section className="max-w-4xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-semibold mb-8 text-center" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-ink-900)' }}>
          How Candor Works
        </h2>

        <div className="space-y-6">
          <StepCard
            num="01"
            title="Three User Uploads per Batch"
            desc="Upload your PDF Bank Statement, Razorpay Settlements CSV, and Internal Orders CSV for a specific period."
          />
          <StepCard
            num="02"
            title="Deterministic Exact Matching"
            desc="Normalizes UTR numbers and reconciles exact fee/TDS arithmetic without wasting LLM calls."
          />
          <StepCard
            num="03"
            title="LLM Fuzzy Pass + Verification Gate"
            desc="Gemini inspects ambiguous items with visible reasoning, verified independently against database arithmetic before acceptance."
          />
          <StepCard
            num="04"
            title="Honest Exception Ledger"
            desc="Unresolved items land on an exception ledger with machine-readable reasons and human controls."
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 text-center text-xs" style={{ borderColor: 'var(--color-paper-300)', color: 'var(--color-ink-500)' }}>
        Candor — Deterministic-first merchant payment reconciliation
      </footer>
    </div>
  )
}

function StepCard({ num, title, desc }) {
  return (
    <div
      className="flex gap-4 p-5 rounded items-start"
      style={{ background: 'var(--color-paper-200)', border: '1px solid var(--color-paper-300)' }}
    >
      <span className="font-ledger text-sm font-bold px-2 py-1 rounded" style={{ background: 'var(--color-ink-900)', color: '#F5F2EC' }}>
        {num}
      </span>
      <div>
        <h4 className="font-semibold text-base mb-1" style={{ color: 'var(--color-ink-900)' }}>{title}</h4>
        <p className="text-sm" style={{ color: 'var(--color-ink-600)' }}>{desc}</p>
      </div>
    </div>
  )
}
