/**
 * ConfidenceBadge — shows an agent confidence score as a coloured pill.
 *
 * Color key (reserved only for state, not decoration):
 *   >= 75%  matched green
 *   50-74%  amber / pending
 *   < 50%   exception red
 *
 * Amounts are rendered in IBM Plex Mono so they read like numbers,
 * not like UI chrome. (frontend prompt §2 typography rule)
 */
export default function ConfidenceBadge({ confidence }) {
  if (confidence === null || confidence === undefined) return null

  const pct = Math.round(confidence * 100)

  const style =
    confidence >= 0.75
      ? { color: 'var(--color-matched)',   background: 'color-mix(in srgb, var(--color-matched) 10%, transparent)',   border: '1px solid color-mix(in srgb, var(--color-matched) 30%, transparent)' }
      : confidence >= 0.5
      ? { color: 'var(--color-pending)',   background: 'color-mix(in srgb, var(--color-pending) 10%, transparent)',   border: '1px solid color-mix(in srgb, var(--color-pending) 30%, transparent)' }
      : { color: 'var(--color-exception)', background: 'color-mix(in srgb, var(--color-exception) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--color-exception) 30%, transparent)' }

  return (
    <span
      style={style}
      className="font-ledger text-xs px-1.5 py-0.5 rounded"
      title={`Agent confidence: ${pct}%`}
    >
      {pct}%
    </span>
  )
}
