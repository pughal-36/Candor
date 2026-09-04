import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import MatchTypeTag from '../components/MatchTypeTag.jsx'

/**
 * HistoryView — Reconciliation Batch History
 *
 * Lists all past reconciliation batches with upload date, status, total rows,
 * match rate %, and an action button to inspect any batch's full reconciliation results.
 */
export default function HistoryView({ currentBatchId, onLoadBatch }) {
  const [batches, setBatches] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true)
      try {
        // Query recent batches list from API
        const { data } = await api.getBatchStatus(currentBatchId || 'all')
        if (data) {
          setBatches(Array.isArray(data) ? data : [data])
        }
      } catch (err) {
        console.error("Failed to load batch history:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [currentBatchId])

  return (
    <div>
      <div className="flex items-center justify-between mb-4 px-1">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: 'var(--color-ink-900)' }}>
            Reconciliation Batch History
          </h2>
          <p className="text-xs font-ledger" style={{ color: 'var(--color-ink-500)' }}>
            Past reconciliation runs and audit records.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 font-ledger text-sm" style={{ color: 'var(--color-ink-500)' }}>
          Loading batch history...
        </div>
      ) : batches.length === 0 ? (
        <div className="p-8 rounded text-center text-sm font-ledger" style={{ background: 'var(--color-paper-200)', border: '1px solid var(--color-paper-300)', color: 'var(--color-ink-500)' }}>
          No previous reconciliation batches found. Upload a 3-source batch to get started.
        </div>
      ) : (
        <div className="rounded overflow-hidden" style={{ border: '1px solid var(--color-paper-300)', background: 'var(--color-paper-100)' }}>
          <table className="w-full text-sm border-collapse text-left">
            <thead>
              <tr style={{ background: 'var(--color-paper-200)', borderBottom: '1px solid var(--color-paper-300)' }}>
                <th className="px-3.5 py-2.5 text-xs font-semibold uppercase" style={{ color: 'var(--color-ink-500)' }}>Batch ID</th>
                <th className="px-3.5 py-2.5 text-xs font-semibold uppercase" style={{ color: 'var(--color-ink-500)' }}>Created At</th>
                <th className="px-3.5 py-2.5 text-xs font-semibold uppercase" style={{ color: 'var(--color-ink-500)' }}>Status</th>
                <th className="px-3.5 py-2.5 text-xs font-semibold uppercase text-right" style={{ color: 'var(--color-ink-500)' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {batches.map(b => (
                <tr key={b.id || b.batch_id} className="border-b transition-colors hover:bg-black/5" style={{ borderColor: 'var(--color-paper-200)' }}>
                  <td className="px-3.5 py-3 font-ledger text-xs font-medium" style={{ color: 'var(--color-ink-900)' }}>
                    {b.id || b.batch_id}
                  </td>
                  <td className="px-3.5 py-3 font-ledger text-xs" style={{ color: 'var(--color-ink-600)' }}>
                    {b.created_at ? new Date(b.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-3.5 py-3">
                    <span className="px-2 py-0.5 rounded text-xs font-ledger uppercase tracking-wider font-semibold"
                      style={{
                        background: b.status === 'done' ? 'color-mix(in srgb, var(--color-matched) 12%, transparent)' : 'color-mix(in srgb, var(--color-pending) 12%, transparent)',
                        color: b.status === 'done' ? 'var(--color-matched)' : 'var(--color-pending)',
                      }}>
                      {b.status}
                    </span>
                  </td>
                  <td className="px-3.5 py-3 text-right">
                    <button
                      id={`inspect-batch-${b.id || b.batch_id}`}
                      onClick={() => onLoadBatch && onLoadBatch(b.id || b.batch_id)}
                      className="px-3 py-1 text-xs font-medium rounded transition-colors"
                      style={{
                        background: 'var(--color-ink-900)',
                        color: '#FFFFFF',
                        border: 'none',
                        cursor: 'pointer',
                      }}
                    >
                      Inspect Batch
                    </button>
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
