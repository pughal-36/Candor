/**
 * ReasoningBlock — renders the agent's plain-language reasoning.
 *
 * Uses the humanist sans-serif (Inter) rather than monospace — the
 * reasoning is narrative text explaining a decision, not a reference
 * number. This typographic contrast does the job of an accent color.
 * (frontend prompt §2 typography rule)
 */
export default function ReasoningBlock({ reasoning }) {
  if (!reasoning) return null

  return (
    <p
      className="mt-2 text-sm leading-relaxed"
      style={{
        fontFamily: 'var(--font-sans)',
        fontStyle: 'italic',
        color: 'var(--color-ink-600)',
        paddingLeft: '0.75rem',
        borderLeft: '2px solid var(--color-paper-400)',
      }}
    >
      {reasoning}
    </p>
  )
}
