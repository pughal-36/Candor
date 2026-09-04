/**
 * ReportHeader — compact summary strip at the top of the dashboard.
 *
 * Shows: match rate %, breakdown by type, processing time.
 * "A compact strip at the top of the dashboard, not a separate page."
 * — frontend prompt §3.4
 *
 * No cards. No shadows. Just a ruled horizontal band.
 */
export default function ReportHeader({ report, loading }) {
  if (loading || !report) return null
  if (report.status) return null // still processing

  const { total_bank_rows, exact_matches, agent_accepted_matches, exceptions, match_rate_pct, processing_time_seconds } = report

  return (
    <div
      className="flex flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3 text-sm"
      style={{
        background: 'var(--color-paper-200)',
        borderBottom: '1px solid var(--color-paper-300)',
      }}
    >
      {/* Match rate — the headline number */}
      <Stat
        label="Match rate"
        value={`${match_rate_pct}%`}
        mono
        color={match_rate_pct >= 75 ? 'var(--color-matched)' : match_rate_pct >= 50 ? 'var(--color-pending)' : 'var(--color-exception)'}
      />

      <Divider />

      <Stat label="Total rows"   value={total_bank_rows}            mono />
      <Stat label="Exact"        value={exact_matches}              mono color="var(--color-matched)" />
      <Stat label="Agent"        value={agent_accepted_matches}     mono color="var(--color-agent)" />
      <Stat label="Exceptions"   value={exceptions}                 mono color={exceptions > 0 ? 'var(--color-exception)' : 'var(--color-ink-500)'} />

      <Divider />

      <Stat
        label="Processed in"
        value={`${processing_time_seconds}s`}
        mono
        color="var(--color-ink-500)"
      />
    </div>
  )
}

function Stat({ label, value, mono, color }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span style={{ color: 'var(--color-ink-500)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </span>
      <span
        className={mono ? 'font-ledger' : ''}
        style={{ color: color ?? 'var(--color-ink-800)', fontWeight: 600 }}
      >
        {value}
      </span>
    </div>
  )
}

function Divider() {
  return <span style={{ color: 'var(--color-paper-400)', userSelect: 'none' }}>|</span>
}
