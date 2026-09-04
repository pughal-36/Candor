/**
 * Candor API client.
 * Every call returns { data, error } — never throws.
 * The frontend must handle both — no silent happy-path assumptions.
 */

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request(method, path, body, timeoutMs = 30000) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const opts = {
      method,
      headers: body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    }
    const res = await fetch(`${BASE}/api/v1${path}`, opts)
    clearTimeout(timeoutId)
    const data = await res.json().catch(() => null)
    if (!res.ok) {
      return { data: null, error: data?.detail ?? `HTTP ${res.status}` }
    }
    return { data, error: null }
  } catch (err) {
    clearTimeout(timeoutId)
    if (err.name === 'AbortError') {
      return { data: null, error: `Request timed out after ${Math.round(timeoutMs / 1000)} seconds` }
    }
    return { data: null, error: err.message ?? 'Network error' }
  }
}

export const api = {
  uploadBatch: ({ statement, settlements, orders }) => {
    const fd = new FormData()
    if (statement) fd.append('statement_file', statement)
    if (settlements) fd.append('settlements_file', settlements)
    if (orders) fd.append('orders_file', orders)
    return request('POST', '/upload-batch', fd, 30000)
  },
  uploadStatement: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('POST', '/upload-statement', fd, 30000)
  },
  getBatchStatus:     (id)       => request('GET',   `/batch/${id}/status`, undefined, 10000),
  getBatchMatches:    (id)       => request('GET',   `/batch/${id}/matches`, undefined, 15000),
  getBatchExceptions: (id)       => request('GET',   `/batch/${id}/exceptions`, undefined, 15000),
  getBatchReport:     (id)       => request('GET',   `/batch/${id}/report`, undefined, 15000),
  resolveException:   (id, body) => request('PATCH', `/exception/${id}`, body, 15000),
  getThreshold:       ()         => request('GET',   '/config/threshold', undefined, 10000),
  updateThreshold:    (value)    => request('PATCH', '/config/threshold', { value }, 10000),
}
