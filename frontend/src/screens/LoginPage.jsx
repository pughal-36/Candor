import { useState } from 'react'

/**
 * LoginPage — Bespoke Paper & Ledger styled login screen.
 *
 * Designed for finance professionals and merchants.
 * Rejects centered SaaS floating card templates in favor of a asymmetric
 * physical ledger layout (#F3F1EA paper, #1B2430 ink, red margin rule,
 * IBM Plex Mono numbers, active voice inline validation).
 */
export default function LoginPage({ onLoginSuccess }) {
  const [mode, setMode]         = useState('login') // 'login' | 'signup'
  const [fullName, setFullName] = useState('')
  const [company, setCompany]   = useState('')
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [touched, setTouched]   = useState({})
  const [loading, setLoading]   = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const errors = {}
  if (mode === 'signup' && !fullName.trim()) {
    errors.fullName = 'Full name is required.'
  }

  if (!email.trim()) {
    errors.email = 'Email address is required.'
  } else if (!/\S+@\S+\.\S+/.test(email)) {
    errors.email = 'Enter a valid email address (e.g. you@company.com).'
  }

  if (!password) {
    errors.password = 'Password is required.'
  } else if (password.length < 4) {
    errors.password = 'Password must be at least 4 characters.'
  }

  function handleBlur(field) {
    setTouched(t => ({ ...t, [field]: true }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setTouched({ fullName: true, email: true, password: true, company: true })

    if (Object.keys(errors).length > 0) {
      return
    }

    setLoading(true)
    setErrorMsg('')

    setTimeout(() => {
      setLoading(false)
      if (email.toLowerCase().includes('fail')) {
        setErrorMsg("That email and password combination doesn't match our records.")
      } else {
        if (onLoginSuccess) {
          onLoginSuccess({
            email,
            name: fullName || email.split('@')[0],
            company: company || 'Merchant Inc.',
            role: 'Finance Admin'
          })
        }
      }
    }, 600)
  }

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row" style={{ background: '#F3F1EA', color: '#1B2430', fontFamily: 'var(--font-sans, Inter, sans-serif)' }}>
      {/* Physical Ledger Left Panel (Asymmetric Document Margin) */}
      <div className="lg:w-5/12 p-8 lg:p-16 flex flex-col justify-between border-b lg:border-b-0 lg:border-r relative" style={{ borderColor: 'color-mix(in srgb, #1B2430 15%, transparent)' }}>
        {/* Ledger Red Margin Line (CSS visual detail) */}
        <div className="hidden lg:block absolute top-0 bottom-0 left-12 w-px" style={{ background: 'rgba(220, 38, 38, 0.25)' }} />

        <div className="relative z-10">
          <h1 className="text-3xl lg:text-4xl font-serif font-bold tracking-tight mb-4" style={{ color: '#1B2430', fontFamily: 'Playfair Display, Georgia, serif' }}>
            Candor
          </h1>

          <p className="text-sm leading-relaxed max-w-md" style={{ color: 'color-mix(in srgb, #1B2430 75%, transparent)' }}>
            Your books, reconciled in the background — always on, always accurate.
          </p>
        </div>


      </div>

      {/* Form Right Panel (Ruled Document Form) */}
      <div className="lg:w-7/12 p-8 lg:p-16 flex items-center justify-center">
        <div className="w-full max-w-md">
          {/* Mode Switch Tabs */}
          <div className="flex border-b mb-8" style={{ borderColor: 'color-mix(in srgb, #1B2430 20%, transparent)' }}>
            <button
              id="mode-login-tab"
              onClick={() => { setMode('login'); setErrorMsg('') }}
              className="pb-3 px-1 text-sm font-semibold uppercase tracking-wider transition-colors mr-6 relative cursor-pointer"
              style={{
                color: mode === 'login' ? '#1B2430' : 'color-mix(in srgb, #1B2430 45%, transparent)',
                borderBottom: mode === 'login' ? '2px solid #1B2430' : '2px solid transparent',
              }}
            >
              Log in
            </button>
            <button
              id="mode-signup-tab"
              onClick={() => { setMode('signup'); setErrorMsg('') }}
              className="pb-3 px-1 text-sm font-semibold uppercase tracking-wider transition-colors relative cursor-pointer"
              style={{
                color: mode === 'signup' ? '#1B2430' : 'color-mix(in srgb, #1B2430 45%, transparent)',
                borderBottom: mode === 'signup' ? '2px solid #1B2430' : '2px solid transparent',
              }}
            >
              Sign up
            </button>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-bold font-serif mb-1" style={{ color: '#1B2430' }}>
              {mode === 'login' ? 'Log in to your workspace' : 'Create your account'}
            </h2>
            <p className="text-xs font-ledger" style={{ color: 'color-mix(in srgb, #1B2430 60%, transparent)' }}>
              {mode === 'login' ? 'Enter your credentials to access reconciliation batches.' : 'Set up your account to start reconciling.'}
            </p>
          </div>

          {/* Error Alert */}
          {errorMsg && (
            <div id="login-error-alert" className="mb-6 p-3.5 rounded text-xs border font-sans" style={{ background: '#FEE2E2', color: '#991B1B', borderColor: '#FCA5A5' }}>
              <strong>Error:</strong> {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Full Name field for Sign Up */}
            {mode === 'signup' && (
              <div>
                <label htmlFor="fullname-input" className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#1B2430' }}>
                  Full Name
                </label>
                <input
                  id="fullname-input"
                  type="text"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  onBlur={() => handleBlur('fullName')}
                  placeholder="Priya Sharma"
                  className="w-full px-3.5 py-2.5 rounded text-sm font-ledger border transition-all focus:outline-none focus:ring-2 focus:ring-slate-900"
                  style={{
                    background: '#FFFFFF',
                    borderColor: touched.fullName && errors.fullName ? '#DC2626' : 'color-mix(in srgb, #1B2430 25%, transparent)',
                    color: '#1B2430',
                  }}
                />
                {touched.fullName && errors.fullName && (
                  <p className="mt-1 text-xs text-red-600 font-sans">{errors.fullName}</p>
                )}
              </div>
            )}

            {/* Email Field */}
            <div>
              <label htmlFor="email-input" className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#1B2430' }}>
                Email
              </label>
              <input
                id="email-input"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onBlur={() => handleBlur('email')}
                placeholder="you@company.com"
                className="w-full px-3.5 py-2.5 rounded text-sm font-ledger border transition-all focus:outline-none focus:ring-2 focus:ring-slate-900"
                style={{
                  background: '#FFFFFF',
                  borderColor: touched.email && errors.email ? '#DC2626' : 'color-mix(in srgb, #1B2430 25%, transparent)',
                  color: '#1B2430',
                }}
              />
              {touched.email && errors.email && (
                <p id="email-error" className="mt-1 text-xs text-red-600 font-sans">
                  {errors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="password-input" className="block text-xs font-semibold uppercase tracking-wider" style={{ color: '#1B2430' }}>
                  Password
                </label>
                {mode === 'login' && (
                  <a href="#forgot" onClick={e => { e.preventDefault(); alert("Please contact your finance administrator to reset your password.") }} className="text-xs hover:underline" style={{ color: 'color-mix(in srgb, #1B2430 65%, transparent)' }}>
                    Forgot password?
                  </a>
                )}
              </div>
              <input
                id="password-input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onBlur={() => handleBlur('password')}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 rounded text-sm font-ledger border transition-all focus:outline-none focus:ring-2 focus:ring-slate-900"
                style={{
                  background: '#FFFFFF',
                  borderColor: touched.password && errors.password ? '#DC2626' : 'color-mix(in srgb, #1B2430 25%, transparent)',
                  color: '#1B2430',
                }}
              />
              {touched.password && errors.password && (
                <p id="password-error" className="mt-1 text-xs text-red-600 font-sans">
                  {errors.password}
                </p>
              )}
            </div>

            {/* Company Name field for Sign Up */}
            {mode === 'signup' && (
              <div>
                <label htmlFor="company-input" className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#1B2430' }}>
                  Company Name (Optional)
                </label>
                <input
                  id="company-input"
                  type="text"
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  placeholder="Acme E-Commerce Pvt Ltd"
                  className="w-full px-3.5 py-2.5 rounded text-sm font-ledger border transition-all focus:outline-none focus:ring-2 focus:ring-slate-900"
                  style={{
                    background: '#FFFFFF',
                    borderColor: 'color-mix(in srgb, #1B2430 25%, transparent)',
                    color: '#1B2430',
                  }}
                />
              </div>
            )}

            {/* Submit Button */}
            <button
              id="login-submit-btn"
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded text-sm font-semibold tracking-wide text-white transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 cursor-pointer shadow-sm hover:opacity-95 disabled:opacity-50 mt-2"
              style={{ background: '#1B2430' }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2 font-ledger">
                  <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Processing...
                </span>
              ) : mode === 'login' ? (
                'Log in'
              ) : (
                'Create Account & Start'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
