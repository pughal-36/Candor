import { useState } from 'react'

/**
 * UploadScreen — Multi-source upload zone (PDF Statement + Settlements CSV + Orders CSV).
 *
 * Each batch requires user-provided files for all 3 sources to ensure
 * genuine 3-way reconciliation without hardcoded seed data.
 */
export default function UploadScreen({ onBatchCreated, batchStatus, serverError }) {
  const [statementFile, setStatementFile]   = useState(null)
  const [settlementsFile, setSettlementsFile] = useState(null)
  const [ordersFile, setOrdersFile]           = useState(null)
  const [error, setError]                   = useState(null)
  const [uploading, setUploading]           = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!statementFile) {
      setError('Bank Statement PDF is required.')
      return
    }
    setError(null)
    setUploading(true)

    try {
      await onBatchCreated({
        statement: statementFile,
        settlements: settlementsFile,
        orders: ordersFile,
      })
    } catch (err) {
      setError(err.message || 'Failed to submit batch upload.')
    } finally {
      setUploading(false)
    }
  }

  if (batchStatus && batchStatus !== 'done' && batchStatus !== 'error') {
    return <ProcessingView status={batchStatus} />
  }

  const activeError = error || serverError

  return (
    <div className="flex flex-col items-center justify-center min-h-[65vh] px-6 py-8">
      <div className="w-full max-w-2xl">
        <div className="mb-6">
          <h2
            className="text-2xl mb-1 font-semibold"
            style={{ fontFamily: 'var(--font-display)', color: 'var(--color-ink-900)' }}
          >
            Reconciliation Batch Upload
          </h2>
          <p className="text-sm" style={{ color: 'var(--color-ink-500)' }}>
            Provide your PDF Bank Statement alongside Razorpay Settlements and Orders CSV exports.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* File 1: Bank Statement PDF (Required) */}
          <FileZone
            id="pdf-upload"
            label="1. Bank Statement (PDF)"
            subtitle="Text-layer PDF or scanned statement (OCR fallback)"
            accept="application/pdf,.pdf"
            file={statementFile}
            onChange={(f) => setStatementFile(f)}
            required
          />

          {/* File 2: Razorpay Settlements CSV */}
          <FileZone
            id="settlements-upload"
            label="2. Razorpay Settlements (CSV)"
            subtitle="Dashboard payout export containing UTRs, fees, and net payouts"
            accept=".csv,text/csv"
            file={settlementsFile}
            onChange={(f) => setSettlementsFile(f)}
          />

          {/* File 3: Internal Orders CSV */}
          <FileZone
            id="orders-upload"
            label="3. Internal Merchant Orders (CSV)"
            subtitle="Store/ERP orders containing order IDs and gross amounts"
            accept=".csv,text/csv"
            file={ordersFile}
            onChange={(f) => setOrdersFile(f)}
          />

          {/* Submit Action Button */}
          <div className="pt-4 flex items-center justify-between">
            <span className="text-xs" style={{ color: 'var(--color-ink-500)' }}>
              {statementFile ? 'Ready to process batch' : 'Select Bank Statement PDF to begin'}
            </span>
            <button
              type="submit"
              disabled={!statementFile || uploading}
              className="px-6 py-2.5 rounded font-medium text-sm transition-all"
              style={{
                background: statementFile && !uploading ? 'var(--color-ink-900)' : 'var(--color-paper-300)',
                color: statementFile && !uploading ? '#F5F2EC' : 'var(--color-ink-400)',
                border: 'none',
                cursor: statementFile && !uploading ? 'pointer' : 'not-allowed',
              }}
            >
              {uploading ? 'Uploading & Processing…' : 'Run Reconciliation Batch'}
            </button>
          </div>
        </form>

        {activeError && (
          <div
            className="mt-6 p-4 rounded text-sm flex flex-col gap-1 border"
            style={{
              color: 'var(--color-exception)',
              background: 'color-mix(in srgb, var(--color-exception) 8%, transparent)',
              borderColor: 'color-mix(in srgb, var(--color-exception) 25%, transparent)',
            }}
          >
            <span className="font-semibold">Batch Validation or Pipeline Error</span>
            <span>{activeError}</span>
          </div>
        )}
      </div>
    </div>
  )
}

function FileZone({ id, label, subtitle, accept, file, onChange, required }) {
  return (
    <div
      className="p-4 rounded border transition-colors flex items-center justify-between"
      style={{
        background: file ? 'color-mix(in srgb, var(--color-matched) 5%, var(--color-paper-100))' : 'var(--color-paper-200)',
        borderColor: file ? 'color-mix(in srgb, var(--color-matched) 30%, transparent)' : 'var(--color-paper-300)',
      }}
    >
      <div>
        <div className="text-sm font-semibold flex items-center gap-1.5" style={{ color: 'var(--color-ink-900)' }}>
          {label}
          {required && <span style={{ color: 'var(--color-exception)' }}>*</span>}
        </div>
        <div className="text-xs" style={{ color: 'var(--color-ink-500)' }}>
          {subtitle}
        </div>
      </div>

      <label htmlFor={id} className="cursor-pointer">
        <span
          className="px-3 py-1.5 rounded text-xs font-medium border inline-block"
          style={{
            background: file ? 'var(--color-paper-100)' : 'var(--color-paper-300)',
            color: 'var(--color-ink-800)',
            borderColor: 'var(--color-paper-400)',
          }}
        >
          {file ? `✓ ${file.name.slice(0, 24)}` : 'Browse File'}
        </span>
        <input
          id={id}
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(e) => e.target.files?.[0] && onChange(e.target.files[0])}
        />
      </label>
    </div>
  )
}

function ProcessingView({ status }) {
  const stages = {
    pending:  { label: 'Queued',              pct: 10 },
    parsing:  { label: 'Ingesting 3 sources…', pct: 40 },
    matching: { label: 'Reconciling batch…',   pct: 75 },
  }
  const { label, pct } = stages[status] ?? { label: status, pct: 50 }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div className="w-full max-w-xs">
        <div className="flex justify-between text-xs mb-2" style={{ color: 'var(--color-ink-500)' }}>
          <span className="font-ledger">{label}</span>
          <span className="font-ledger">{pct}%</span>
        </div>
        <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--color-paper-300)' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, background: 'var(--color-ink-800)' }}
          />
        </div>
      </div>
    </div>
  )
}
