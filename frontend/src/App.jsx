import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { api } from './api/client.js'
import LandingPage from './screens/LandingPage.jsx'
import UploadScreen from './screens/UploadScreen.jsx'
import ExceptionLedger from './screens/ExceptionLedger.jsx'
import MatchedTransactions from './screens/MatchedTransactions.jsx'
import ReportHeader from './screens/ReportHeader.jsx'
import LoginPage from './screens/LoginPage.jsx'
import HistoryView from './screens/HistoryView.jsx'

/**
 * Candor — root application.
 * Views: 'landing' | 'login' | 'upload' | 'exceptions' | 'matches' | 'history'
 */

const INITIAL = {
  batch: null,           // { id, status, filename }
  matches: [],
  exceptions: [],
  report: null,
  threshold: 0.75,
  thresholdDraft: null,  // local slider value before API commit
  activeView: 'landing', // Open on landing page first
  loading: { data: false, report: false, threshold: false },
  errors: { data: null, report: null, threshold: null },
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_BATCH':
      return { ...state, batch: action.batch }
    case 'SET_STATUS':
      return { ...state, batch: { ...state.batch, status: action.status } }
    case 'SET_DATA':
      return {
        ...state,
        matches: action.matches,
        exceptions: action.exceptions,
        loading: { ...state.loading, data: false },
        errors:  { ...state.errors,  data: null },
        activeView: 'exceptions',   // land on exceptions first after completion
      }
    case 'SET_REPORT':
      return {
        ...state,
        report: action.report,
        loading: { ...state.loading, report: false },
      }
    case 'SET_THRESHOLD':
      return { ...state, threshold: action.value, thresholdDraft: null }
    case 'DRAFT_THRESHOLD':
      return { ...state, thresholdDraft: action.value }
    case 'RESOLVE_EXCEPTION': {
      const updated = state.exceptions.map(e =>
        e.id === action.id ? { ...e, resolution: action.resolution } : e
      )
      return { ...state, exceptions: updated }
    }
    case 'SET_VIEW':
      return { ...state, activeView: action.view }
    case 'LOADING':
      return { ...state, loading: { ...state.loading, ...action.flags } }
    case 'ERROR':
      return { ...state, errors:  { ...state.errors,  ...action.flags } }
    case 'RESET':
      return { ...INITIAL }
    default:
      return state
  }
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, INITIAL)
  const [user, setUser]   = useState(null)
  const pollRef = useRef(null)

  // ---- Upload ----
  const handleUpload = useCallback(async ({ statement, settlements, orders }) => {
    const { data, error } = await api.uploadBatch({ statement, settlements, orders })
    if (error || !data) {
      dispatch({ type: 'ERROR', flags: { data: error ?? 'Upload failed.' } })
      return
    }
    dispatch({ type: 'SET_BATCH', batch: { id: data.batch_id, status: data.status, filename: statement.name } })
    startPolling(data.batch_id)
  }, [])

  // ---- Polling ----
  function startPolling(batchId) {
    stopPolling()
    let isFetching = false
    const startTime = Date.now()
    const MAX_POLL_MS = 60000 // 60 seconds timeout

    pollRef.current = setInterval(async () => {
      if (isFetching) return

      if (Date.now() - startTime > MAX_POLL_MS) {
        stopPolling()
        dispatch({ type: 'SET_STATUS', status: 'error' })
        dispatch({ type: 'ERROR', flags: { data: 'Processing timed out. Please retry.' } })
        return
      }

      isFetching = true
      try {
        const { data, error } = await api.getBatchStatus(batchId)
        if (error) {
          stopPolling()
          dispatch({ type: 'SET_STATUS', status: 'error' })
          dispatch({ type: 'ERROR', flags: { data: error } })
          return
        }
        if (!data) return
        dispatch({ type: 'SET_STATUS', status: data.status })

        if (data.status === 'done' || data.status === 'error') {
          stopPolling()
          if (data.status === 'done') {
            loadBatchData(batchId)
          } else if (data.status === 'error') {
            dispatch({ type: 'ERROR', flags: { data: data.error_message ?? 'Backend reconciliation failed.' } })
          }
        }
      } finally {
        isFetching = false
      }
    }, 1500)
  }

  function stopPolling() {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  useEffect(() => () => stopPolling(), [])

  // ---- Load matches + exceptions + report ----
  async function loadBatchData(batchId) {
    dispatch({ type: 'LOADING', flags: { data: true, report: true } })
    const [mRes, eRes, rRes] = await Promise.all([
      api.getBatchMatches(batchId),
      api.getBatchExceptions(batchId),
      api.getBatchReport(batchId),
    ])

    if (mRes.error || eRes.error) {
      dispatch({ type: 'ERROR', flags: { data: mRes.error ?? eRes.error } })
    } else {
      dispatch({ type: 'SET_DATA', matches: mRes.data ?? [], exceptions: eRes.data ?? [] })
    }

    if (rRes.data) dispatch({ type: 'SET_REPORT', report: rRes.data })
  }

  // ---- Threshold ----
  useEffect(() => {
    api.getThreshold().then(({ data }) => {
      if (data) dispatch({ type: 'SET_THRESHOLD', value: data.value })
    })
  }, [])

  const commitThreshold = useCallback(async (value) => {
    dispatch({ type: 'LOADING', flags: { threshold: true } })
    const { data, error } = await api.updateThreshold(value)
    if (data) dispatch({ type: 'SET_THRESHOLD', value: data.value })
    if (error) dispatch({ type: 'ERROR', flags: { threshold: error } })
    dispatch({ type: 'LOADING', flags: { threshold: false } })
  }, [])

  // ---- Exception resolution ----
  const handleResolve = useCallback(async (id, resolution) => {
    dispatch({ type: 'RESOLVE_EXCEPTION', id, resolution })
    const { error } = await api.resolveException(id, { resolution })
    if (error) {
      dispatch({ type: 'RESOLVE_EXCEPTION', id, resolution: null })
    }
  }, [])

  const { batch, matches, exceptions, report, threshold, thresholdDraft,
          activeView, loading, errors } = state

  const exceptionCount  = exceptions.filter(e => !e.resolution).length
  const matchCount      = matches.length
  const hasBatchData    = matchCount > 0 || exceptions.length > 0

  if (activeView === 'landing') {
    return <LandingPage user={user} onGetStarted={() => dispatch({ type: 'SET_VIEW', view: user ? 'upload' : 'login' })} />
  }

  if (activeView === 'login') {
    return (
      <LoginPage
        onLoginSuccess={(u) => {
          setUser(u)
          dispatch({ type: 'SET_VIEW', view: 'upload' }) // Requirement 2.5: Upload as default post-login screen
        }}
      />
    )
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--color-paper-100)' }}>
      {/* ======================== NAV ======================== */}
      <header
        className="flex items-center justify-between px-6 py-3 sticky top-0 z-10 shadow-sm"
        style={{ background: 'var(--color-ink-900)', color: '#fff' }}
      >
        <div className="flex items-center gap-3">
          <span
            className="font-display text-xl tracking-tight select-none cursor-pointer"
            style={{ color: '#E8E4DC' }}
            onClick={() => dispatch({ type: 'SET_VIEW', view: 'landing' })}
          >
            Candor
          </span>
        </div>

        {/* Tab navigation */}
        <nav className="flex items-center gap-1">
          <NavTab
            id="tab-landing"
            label="Overview"
            active={activeView === 'landing'}
            onClick={() => dispatch({ type: 'SET_VIEW', view: 'landing' })}
          />
          <NavTab
            id="tab-upload"
            label="Upload"
            active={activeView === 'upload'}
            onClick={() => dispatch({ type: 'SET_VIEW', view: 'upload' })}
          />
          {hasBatchData && (
            <>
              <NavTab
                id="tab-exceptions"
                label={`Exceptions${exceptionCount > 0 ? ` (${exceptionCount})` : ''}`}
                active={activeView === 'exceptions'}
                danger={exceptionCount > 0}
                onClick={() => dispatch({ type: 'SET_VIEW', view: 'exceptions' })}
              />
              <NavTab
                id="tab-matches"
                label={`Matched (${matchCount})`}
                active={activeView === 'matches'}
                onClick={() => dispatch({ type: 'SET_VIEW', view: 'matches' })}
              />
            </>
          )}
          <NavTab
            id="tab-history"
            label="History"
            active={activeView === 'history'}
            onClick={() => dispatch({ type: 'SET_VIEW', view: 'history' })}
          />
        </nav>

        {/* Right side controls: Threshold & User Logout */}
        <div className="flex items-center gap-4">
          <ThresholdControl
            value={thresholdDraft ?? threshold}
            loading={loading.threshold}
            onChange={(v) => dispatch({ type: 'DRAFT_THRESHOLD', value: v })}
            onCommit={commitThreshold}
          />

          {user ? (
            <div className="flex items-center gap-2 pl-3 border-l border-white/20">
              <span className="text-xs font-ledger text-slate-300">
                {user.email}
              </span>
              <button
                id="logout-btn"
                onClick={() => {
                  setUser(null)
                  dispatch({ type: 'SET_VIEW', view: 'login' })
                }}
                className="text-xs font-ledger px-2 py-1 rounded bg-red-950/60 hover:bg-red-900 text-red-200 border border-red-800 transition-colors cursor-pointer"
                title="Log out of your session"
              >
                Log out
              </button>
            </div>
          ) : (
            <button
              id="header-login-btn"
              onClick={() => dispatch({ type: 'SET_VIEW', view: 'login' })}
              className="text-xs font-ledger px-2.5 py-1 rounded bg-white/15 hover:bg-white/25 text-white transition-colors cursor-pointer"
            >
              Log in
            </button>
          )}
        </div>
      </header>

      {/* ======================== REPORT STRIP ======================== */}
      {hasBatchData && (
        <ReportHeader report={report} loading={loading.report} />
      )}

      {/* ======================== MAIN CONTENT ======================== */}
      <main className="px-6 py-6 max-w-7xl mx-auto">
        {activeView === 'upload' && (
          <UploadScreen
            onBatchCreated={handleUpload}
            batchStatus={batch?.status}
            serverError={errors.data}
          />
        )}

        {activeView === 'exceptions' && (
          <ExceptionLedger
            exceptions={exceptions}
            loading={loading.data}
            error={errors.data}
            onResolve={handleResolve}
          />
        )}

        {activeView === 'matches' && (
          <MatchedTransactions
            matches={matches}
            loading={loading.data}
            error={errors.data}
          />
        )}

        {activeView === 'history' && (
          <HistoryView
            currentBatchId={batch?.id}
            onLoadBatch={(bId) => {
              dispatch({ type: 'SET_BATCH', batch: { id: bId, status: 'done', filename: 'batch' } })
              loadBatchData(bId)
            }}
          />
        )}
      </main>
    </div>
  )
}

function NavTab({ id, label, active, danger, onClick }) {
  return (
    <button
      id={id}
      onClick={onClick}
      className="px-3 py-1.5 text-sm rounded transition-colors"
      style={{
        background: active ? 'rgba(255,255,255,0.12)' : 'transparent',
        color: active
          ? '#F5F2EC'
          : danger
          ? '#F08080'
          : 'rgba(255,255,255,0.55)',
        fontWeight: active ? 500 : 400,
        border: 'none',
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  )
}

function ThresholdControl({ value, loading, onChange, onCommit }) {
  const pct = Math.round((value ?? 0.75) * 100)

  return (
    <div className="flex items-center gap-2" title="Confidence threshold — agent matches below this score go to the exception ledger">
      <label htmlFor="threshold-slider" className="text-xs" style={{ color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap' }}>
        Threshold
      </label>
      <input
        id="threshold-slider"
        type="range"
        min={0}
        max={100}
        step={5}
        value={pct}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        onMouseUp={() => onCommit(value)}
        onTouchEnd={() => onCommit(value)}
        className="w-24 cursor-pointer"
        style={{ accentColor: '#C8C0B0' }}
      />
      <span
        className="font-ledger text-xs w-8 text-right tabular-nums"
        style={{ color: loading ? 'rgba(255,255,255,0.35)' : '#E8E4DC' }}
      >
        {pct}%
      </span>
    </div>
  )
}
