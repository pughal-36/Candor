import { useState } from 'react'
import ConfidenceBadge from '../components/ConfidenceBadge.jsx'
import ReasoningBlock from '../components/ReasoningBlock.jsx'

/**
 * ExceptionLedger — the primary view of Candor.
 *
 * "The exception list is the main character of this UI, not an afterthought."
 * — frontend prompt §3.2
 *
 * Each entry shows:
 *   - The transaction (narration, amount, date)
 *   - Why it didn't clear (reason_code + reason)
 *   - Agent's best-guess candidate + confidence (if any)
 *   - Agent's reasoning (expandable)
 *   - Human resolution controls: Accept / Reject / Unmatched
 *
 * Sort: confidence descending by default (closest-to-resolved at top).
 * The ONE motion moment lives here: resolving a row triggers row-resolving
 * animation class before the row disappears or changes state.
 */

const REASON_LABELS = {
  below_threshold:     'Below threshold',
  verification_failed: 'Verification failed',
  low_ocr_confidence:  'OCR — low confidence',
  no_candidate:        'No candidate found',
  no_bank_row:         'No bank credit found',
  no_settlement:       'No settlement found',
}

const REASON_COLORS = {
  below_threshold:     'var(--color-pending)',
  verification_failed: 'var(--color-exception)',
  low_ocr_confidence:  'var(--color-pending)',
  no_candidate:        'var(--color-ink-500)',
  no_bank_row:         'var(--color-exception)',
  no_settlement:       'var(--color-exception)',
}

export default function ExceptionLedger({ exceptions, loading, error, onResolve }) {
  const [expanded, setExpanded]   = useState({})
  const [resolving, setResolving] = useState({})
  const [sortBy, setSortBy]       = useState('days_open')

  if (loading) return <LoadingState />
  if (error)   return <ErrorState message={error} />

  const sorted = [...exceptions].sort((a, b) => {
    if (sortBy === 'days_open')  return (b.days_open ?? 0) - (a.days_open ?? 0)
    if (sortBy === 'confidence') return (b.agent_confidence ?? -1) - (a.agent_confidence ?? -1)
    if (sortBy === 'date')       return new Date(a.date ?? 0) - new Date(b.date ?? 0)
    if (sortBy === 'amount')     return (b.amount ?? 0) - (a.amount ?? 0)
    return 0
  })

  const unresolved = sorted.filter(e => !e.resolution)
  const resolved   = sorted.filter(e => e.resolution)

  async function handleResolve(exc, resolution) {
    setResolving(r => ({ ...r, [exc.id]: true }))
    await onResolve(exc.id, resolution)
    // Brief delay so the animation plays before state updates
    setTimeout(() => setResolving(r => ({ ...r, [exc.id]: false })), 750)
  }

  return (
    <div>
      {/* Header row */}
      <div className="flex items-center justify-between mb-4 px-1">
        <div>
          <span className="text-lg font-semibold" style={{ color: 'var(--color-ink-900)' }}>
            Exception Ledger
          </span>
          <span className="ml-2 text-sm font-ledger" style={{ color: 'var(--color-exception)' }}>
            {unresolved.length} pending
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-ink-500)' }}>
          <span>Sort:</span>
          {[
            { id: 'days_open', label: 'Days Open (Oldest)' },
            { id: 'confidence', label: 'Confidence' },
            { id: 'date', label: 'Date' },
            { id: 'amount', label: 'Amount' },
          ].map(s => (
            <button
              key={s.id}
              id={`sort-exceptions-${s.id}`}
              onClick={() => setSortBy(s.id)}
              className="px-2 py-1 rounded transition-colors"
              style={{
                background: sortBy === s.id ? 'var(--color-paper-300)' : 'transparent',
                color: sortBy === s.id ? 'var(--color-ink-800)' : 'var(--color-ink-500)',
                fontFamily: 'var(--font-sans)',
                fontWeight: sortBy === s.id ? 600 : 400,
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {unresolved.length === 0 && resolved.length === 0 && (
        <EmptyState />
      )}

      {/* Unresolved exceptions */}
      {unresolved.length > 0 && (
        <div
          className="rounded overflow-hidden"
          style={{ border: '1px solid var(--color-paper-300)' }}
        >
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr style={{ background: 'var(--color-paper-200)', borderBottom: '1px solid var(--color-paper-300)' }}>
                <Th>Age</Th>
                <Th>Date</Th>
                <Th>Narration</Th>
                <Th align="right">Amount</Th>
                <Th>Reason</Th>
                <Th>Confidence</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {unresolved.map(exc => (
                <ExceptionRow
                  key={exc.id}
                  exc={exc}
                  isExpanded={!!expanded[exc.id]}
                  isResolving={!!resolving[exc.id]}
                  onToggle={() => setExpanded(e => ({ ...e, [exc.id]: !e[exc.id] }))}
                  onResolve={handleResolve}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Resolved exceptions (collapsed section) */}
      {resolved.length > 0 && (
        <details className="mt-6" style={{ color: 'var(--color-ink-500)' }}>
          <summary className="cursor-pointer text-sm select-none py-2">
            {resolved.length} resolved exception{resolved.length !== 1 ? 's' : ''}
          </summary>
          <div className="mt-2 rounded overflow-hidden" style={{ border: '1px solid var(--color-paper-300)' }}>
            <table className="w-full text-sm border-collapse">
              <tbody>
                {resolved.map(exc => (
                  <ExceptionRow
                    key={exc.id}
                    exc={exc}
                    isExpanded={!!expanded[exc.id]}
                    isResolving={false}
                    onToggle={() => setExpanded(e => ({ ...e, [exc.id]: !e[exc.id] }))}
                    onResolve={handleResolve}
                    dimmed
                  />
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  )
}

function ExceptionRow({ exc, isExpanded, isResolving, onToggle, onResolve, dimmed }) {
  const reasonColor = REASON_COLORS[exc.reason_code] ?? 'var(--color-ink-500)'

  return (
    <>
      <tr
        id={`exception-row-${exc.id}`}
        className={isResolving ? 'row-resolving' : ''}
        style={{
          borderBottom: '1px solid var(--color-paper-200)',
          opacity: dimmed ? 0.55 : 1,
          borderLeft: exc.resolution ? 'none'
            : exc.agent_confidence >= 0.5
            ? '3px solid color-mix(in srgb, var(--color-pending) 60%, transparent)'
            : '3px solid transparent',
          transition: 'opacity 0.3s',
        }}
      >
        <td className="px-3 py-3 font-ledger text-xs whitespace-nowrap font-medium" style={{ color: exc.days_open > 7 ? 'var(--color-exception)' : 'var(--color-ink-700)' }}>
          <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: exc.days_open > 7 ? 'color-mix(in srgb, var(--color-exception) 10%, transparent)' : 'var(--color-paper-300)' }}>
            {exc.days_open ?? 0}d open
          </span>
        </td>
        <td className="px-3 py-3 font-ledger text-xs whitespace-nowrap" style={{ color: 'var(--color-ink-600)' }}>
          {exc.date ?? '—'}
        </td>
        <td className="px-3 py-3 max-w-xs">
          <div className="truncate text-xs" style={{ color: 'var(--color-ink-800)' }} title={exc.narration}>
            {exc.narration ?? '—'}
          </div>
          {exc.extracted_reference && (
            <div className="font-ledger text-xs mt-0.5" style={{ color: 'var(--color-ink-400)' }}>
              {exc.extracted_reference}
            </div>
          )}
        </td>
        <td className="px-3 py-3 font-ledger text-xs text-right whitespace-nowrap" style={{ color: 'var(--color-ink-900)' }}>
          {exc.amount != null ? `₹${Number(exc.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—'}
        </td>
        <td className="px-3 py-3">
          <span className="text-xs font-medium" style={{ color: reasonColor }}>
            {REASON_LABELS[exc.reason_code] ?? exc.reason_code}
          </span>
        </td>
        <td className="px-3 py-3">
          <div className="flex items-center gap-1.5">
            <ConfidenceBadge confidence={exc.agent_confidence} />
            {exc.agent_reasoning && (
              <button
                id={`expand-reasoning-${exc.id}`}
                onClick={onToggle}
                className="text-xs underline-offset-2 hover:underline"
                style={{ color: 'var(--color-ink-400)', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                {isExpanded ? 'hide' : 'why?'}
              </button>
            )}
          </div>
        </td>
        <td className="px-3 py-3">
          {!exc.resolution ? (
            <div className="flex gap-1.5">
              <ActionBtn id={`accept-${exc.id}`} onClick={() => onResolve(exc, 'accepted')}  color="matched"   label="Accept" />
              <ActionBtn id={`reject-${exc.id}`} onClick={() => onResolve(exc, 'rejected')}  color="exception" label="Reject" />
              <ActionBtn id={`unmatch-${exc.id}`} onClick={() => onResolve(exc, 'unmatched')} color="ink-500"   label="Unmatch" />
            </div>
          ) : (
            <span className="font-ledger text-xs capitalize" style={{ color: 'var(--color-ink-400)' }}>
              {exc.resolution}
            </span>
          )}
        </td>
      </tr>

      {/* Expanded reasoning row */}
      {isExpanded && exc.agent_reasoning && (
        <tr style={{ borderBottom: '1px solid var(--color-paper-200)' }}>
          <td />
          <td colSpan={5} className="px-3 pb-3">
            <ReasoningBlock reasoning={exc.agent_reasoning} />
            {exc.reason && (
              <p className="mt-1 text-xs" style={{ color: 'var(--color-ink-400)' }}>
                <strong>Why flagged:</strong> {exc.reason}
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

function ActionBtn({ id, onClick, color, label }) {
  const colorMap = {
    matched:   'var(--color-matched)',
    exception: 'var(--color-exception)',
    'ink-500': 'var(--color-ink-500)',
  }
  const c = colorMap[color] ?? 'var(--color-ink-500)'
  return (
    <button
      id={id}
      onClick={onClick}
      className="text-xs px-2 py-1 rounded transition-colors"
      style={{
        color: c,
        background: `color-mix(in srgb, ${c} 8%, transparent)`,
        border: `1px solid color-mix(in srgb, ${c} 25%, transparent)`,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  )
}

function Th({ children, align = 'left' }) {
  return (
    <th
      className="px-3 py-2 text-xs font-medium"
      style={{ color: 'var(--color-ink-500)', textAlign: align, fontFamily: 'var(--font-sans)', fontWeight: 500 }}
    >
      {children}
    </th>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-40">
      <span className="text-sm font-ledger" style={{ color: 'var(--color-ink-400)' }}>Loading exceptions…</span>
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div className="p-4 rounded text-sm"
      style={{ color: 'var(--color-exception)', background: 'color-mix(in srgb, var(--color-exception) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--color-exception) 20%, transparent)' }}>
      {message}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-40 gap-2" style={{ color: 'var(--color-ink-400)' }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <span className="text-sm">No exceptions — all transactions matched.</span>
    </div>
  )
}
