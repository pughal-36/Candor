/**
 * MatchTypeTag — badge showing how a transaction was matched.
 *
 * 'exact'          → muted green  (deterministic pass)
 * 'agent_accepted' → deep blue    (LLM pass, verified)
 */
export default function MatchTypeTag({ type }) {
  const cfg = {
    exact: {
      label: 'Exact 1:1',
      style: { color: 'var(--color-matched)', background: 'color-mix(in srgb, var(--color-matched) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--color-matched) 25%, transparent)' },
    },
    subset_sum: {
      label: 'Subset-Sum',
      style: { color: '#047857', background: 'color-mix(in srgb, #047857 10%, transparent)', border: '1px solid color-mix(in srgb, #047857 30%, transparent)' },
    },
    agent_accepted: {
      label: 'Agent',
      style: { color: 'var(--color-agent)', background: 'color-mix(in srgb, var(--color-agent) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--color-agent) 25%, transparent)' },
    },
  }

  const entry = cfg[type] ?? { label: type, style: {} }

  return (
    <span className="font-ledger text-xs px-1.5 py-0.5 rounded" style={entry.style}>
      {entry.label}
    </span>
  )
}
