import { useState } from 'react'
import MatchTypeTag from '../components/MatchTypeTag.jsx'
import ConfidenceBadge from '../components/ConfidenceBadge.jsx'
import ReasoningBlock from '../components/ReasoningBlock.jsx'

/**
 * MatchedTransactions — Senior UI/UX pass for confirmed matches.
 *
 * Density, column alignment, clean inline reasoning expansion, and empty states.
 */
export default function MatchedTransactions({ matches = [], loading, error }) {
  const [expanded, setExpanded] = useState({})
  const [filter, setFilter]     = useState('all')

  if (loading) return <LoadingState />
  if (error)   return <ErrorState message={error} />

  const filtered = filter === 'all'
    ? matches
    : matches.filter(m => m.match_type === filter)

  const exactCount = matches.filter(m => m.match_type === 'exact').length
  const subsetCount = matches.filter(m => m.match_type === 'subset_sum').length
  const agentCount = matches.filter(m => m.match_type === 'agent_accepted').length

  return (
    <div>
      {/* Header Bar */}
      <div className="flex items-center justify-between mb-4 px-1">
        <div>
          <span className="text-lg font-semibold" style={{ color: 'var(--color-ink-900)' }}>
            Matched Transactions
          </span>
          <span className="ml-2 text-xs font-ledger px-2 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--color-matched) 12%, transparent)', color: 'var(--color-matched)' }}>
            {matches.length} confirmed
          </span>
        </div>

        {/* Filter Pills */}
        <div className="flex gap-1.5 text-xs">
          {[
            { key: 'all',            label: `All (${matches.length})` },
            { key: 'exact',          label: `Exact 1:1 (${exactCount})` },
            { key: 'subset_sum',     label: `Subset-Sum Batch (${subsetCount})` },
            { key: 'agent_accepted', label: `Agent (${agentCount})` },
          ].map(({ key, label }) => (
            <button
              key={key}
              id={`filter-matches-${key}`}
              onClick={() => setFilter(key)}
              className="px-3 py-1 rounded transition-colors text-xs font-medium"
              style={{
                background: filter === key ? 'var(--color-paper-300)' : 'transparent',
                color: filter === key ? 'var(--color-ink-900)' : 'var(--color-ink-500)',
                border: `1px solid ${filter === key ? 'var(--color-paper-400)' : 'transparent'}`,
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState filter={filter} />
      ) : (
        <div className="rounded overflow-hidden" style={{ border: '1px solid var(--color-paper-300)', background: 'var(--color-paper-100)' }}>
          <table className="w-full text-sm border-collapse text-left">
            <thead>
              <tr style={{ background: 'var(--color-paper-200)', borderBottom: '1px solid var(--color-paper-300)' }}>
                <Th>Date</Th>
                <Th>Bank Narration & Reconstructed Arithmetic Bridge</Th>
                <Th align="right">Credit Amount</Th>
                <Th>Match Type</Th>
                <Th>Confidence</Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(m => (
                <tr key={m.id} id={`match-row-${m.id}`} className="border-b transition-colors hover:bg-black/5" style={{ borderColor: 'var(--color-paper-200)' }}>
                  <td className="px-3.5 py-3 font-ledger text-xs whitespace-nowrap align-top" style={{ color: 'var(--color-ink-600)' }}>
                    {m.date || '—'}
                  </td>
                  <td className="px-3.5 py-3 max-w-xl align-top">
                    <div className="text-xs font-sans font-medium" style={{ color: 'var(--color-ink-900)' }} title={m.narration}>
                      {m.narration || '—'}
                    </div>
                    {/* Prominent Accounting Bridge Display */}
                    {(m.bridge_summary || m.reasoning) && (
                      <div className="mt-1.5 p-2 rounded text-xs font-ledger" style={{ background: 'color-mix(in srgb, var(--color-matched) 6%, var(--color-paper-100))', border: '1px solid color-mix(in srgb, var(--color-matched) 20%, transparent)', color: 'var(--color-ink-900)' }}>
                        <span className="font-semibold text-emerald-800 uppercase tracking-wider mr-1.5" style={{ fontSize: '0.65rem' }}>
                          Arithmetic Bridge:
                        </span>
                        {m.bridge_summary || m.reasoning}
                      </div>
                    )}
                  </td>
                  <td className="px-3.5 py-3 font-ledger text-xs text-right whitespace-nowrap font-medium align-top" style={{ color: 'var(--color-ink-900)' }}>
                    {m.amount != null ? `₹${Number(m.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—'}
                  </td>
                  <td className="px-3.5 py-3 align-top">
                    <MatchTypeTag type={m.match_type} />
                  </td>
                  <td className="px-3.5 py-3 align-top">
                    <ConfidenceBadge confidence={m.confidence ?? 1.0} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Th({ children, align = 'left' }) {
  return (
    <th className="px-3.5 py-2.5 text-xs font-semibold uppercase tracking-wider"
      style={{ color: 'var(--color-ink-500)', textAlign: align, fontSize: '0.7rem' }}>
      {children}
    </th>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-40">
      <span className="text-sm font-ledger" style={{ color: 'var(--color-ink-500)' }}>Loading matches…</span>
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

function EmptyState({ filter }) {
  return (
    <div className="flex flex-col items-center justify-center h-40 text-sm gap-2" style={{ color: 'var(--color-ink-500)' }}>
      <span>No {filter === 'all' ? '' : filter.replace('_', ' ')} matches found for this batch.</span>
    </div>
  )
}
