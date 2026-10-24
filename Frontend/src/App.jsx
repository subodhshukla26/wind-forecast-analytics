import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Activity,
  AlertCircle,
  BarChart3,
  CalendarDays,
  ChevronDown,
  CircleHelp,
  Database,
  FileText,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  Settings2,
  Wind,
  X,
} from 'lucide-react'

// Base URL configured via Vite environment variable with local fallback
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') || 'http://localhost:8000'

const navItems = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Forecast Analysis', icon: Activity, active: true },
  { label: 'Accuracy Reports', icon: BarChart3 },
  { label: 'Data Overview', icon: Database },
]

function Metric({ label, value, detail, tone = 'mint', icon: Icon }) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className={`metric-icon ${tone}`}>
          <Icon size={16} />
        </span>
      </div>
      <strong>{value}</strong>
      <div className="metric-detail">
        <span className={tone === 'mint' ? 'positive' : ''}>{detail}</span>
        <span className="period-label">vs benchmark</span>
      </div>
    </article>
  )
}

function formatUTCHourMinute(isoString) {
  if (!isoString) return '--:--'
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return '--:--'
  const hours = String(date.getUTCHours()).padStart(2, '0')
  const minutes = String(date.getUTCMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}

function formatPublishTimestamp(isoString) {
  if (!isoString) return 'Pending'
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return 'Pending'
  const day = date.getUTCDate()
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const month = months[date.getUTCMonth()]
  const hours = String(date.getUTCHours()).padStart(2, '0')
  const minutes = String(date.getUTCMinutes()).padStart(2, '0')
  return `${day} ${month} · ${hours}:${minutes}`
}

export default function App() {
  const [selectedDate] = useState('2026-01-15')
  const [decisionHour] = useState(10)
  const [decisionMinute] = useState(0)

  const [range, setRange] = useState('Full day')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showAllPeriods, setShowAllPeriods] = useState(false)

  // API State
  const [periods, setPeriods] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [lastFetched, setLastFetched] = useState(null)

  // Native Fetch API integration
  const loadAnalyticsData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)

    const queryParams = new URLSearchParams({
      start_date: selectedDate,
      end_date: selectedDate,
      decision_hour: String(decisionHour),
      decision_minute: String(decisionMinute),
    })

    try {
      const [errorsResponse, summaryResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/errors?${queryParams.toString()}`),
        fetch(`${API_BASE_URL}/api/accuracy/summary?${queryParams.toString()}`),
      ])

      if (!errorsResponse.ok) {
        const errorData = await errorsResponse.json().catch(() => ({}))
        throw new Error(errorData.detail || `Forecast error data failed (${errorsResponse.status})`)
      }

      if (!summaryResponse.ok) {
        const errorData = await summaryResponse.json().catch(() => ({}))
        throw new Error(errorData.detail || `Accuracy summary failed (${summaryResponse.status})`)
      }

      const errorsPayload = await errorsResponse.json()
      const summaryPayload = await summaryResponse.json()

      const rawRecords = Array.isArray(errorsPayload.data) ? errorsPayload.data : []
      const transformedPeriods = rawRecords.map((item) => ({
        time: formatUTCHourMinute(item.deliveryTime),
        rawTime: item.deliveryTime,
        publishTimeFormatted: formatPublishTimestamp(item.selectedPublishTime),
        publishTime: item.selectedPublishTime,
        forecast: item.forecastGeneration != null ? Math.round(item.forecastGeneration) : null,
        actual: item.actualGeneration != null ? Math.round(item.actualGeneration) : null,
        error: item.forecastErrorMW != null ? Math.round(item.forecastErrorMW) : null,
        absoluteError: item.absoluteErrorMW != null ? Math.round(item.absoluteErrorMW) : null,
        percentageError: item.percentageError != null ? Number(item.percentageError.toFixed(1)) : null,
      }))

      setPeriods(transformedPeriods)
      setMetrics(summaryPayload.metrics || null)
      setLastFetched(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred while fetching data.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [selectedDate, decisionHour, decisionMinute])

  useEffect(() => {
    loadAnalyticsData()
  }, [loadAnalyticsData])

  // Filter periods based on user range selection
  const visibleData = useMemo(() => {
    if (!periods.length) return []
    if (range === 'Morning') {
      return periods.filter((item) => {
        const hour = parseInt(item.time.split(':')[0], 10)
        return hour >= 0 && hour < 12
      })
    }
    if (range === 'Evening') {
      return periods.filter((item) => {
        const hour = parseInt(item.time.split(':')[0], 10)
        return hour >= 12 && hour < 24
      })
    }
    return periods
  }, [periods, range])

  // Derived KPI calculations
  const validForecasts = useMemo(
    () => visibleData.filter((x) => x.forecast !== null),
    [visibleData]
  )
  const validActuals = useMemo(
    () => visibleData.filter((x) => x.actual !== null),
    [visibleData]
  )

  const avgForecast = useMemo(() => {
    if (!validForecasts.length) return 0
    return Math.round(validForecasts.reduce((sum, x) => sum + x.forecast, 0) / validForecasts.length)
  }, [validForecasts])

  const avgActual = useMemo(() => {
    if (!validActuals.length) return 0
    return Math.round(validActuals.reduce((sum, x) => sum + x.actual, 0) / validActuals.length)
  }, [validActuals])

  const displayMae = useMemo(() => {
    if (metrics?.maeMW != null) return `${Math.round(metrics.maeMW).toLocaleString()} MW`
    const withErrors = visibleData.filter((x) => x.absoluteError !== null)
    if (!withErrors.length) return 'N/A'
    const computedMae = Math.round(
      withErrors.reduce((sum, x) => sum + x.absoluteError, 0) / withErrors.length
    )
    return `${computedMae.toLocaleString()} MW`
  }, [metrics, visibleData])

  const displayRmse = useMemo(() => {
    if (metrics?.rmseMW != null) return `${Math.round(metrics.rmseMW).toLocaleString()} MW`
    return 'N/A'
  }, [metrics])

  // Accuracy threshold percentages for snapshot card
  const accuracyStats = useMemo(() => {
    const validWithPct = periods.filter((x) => x.percentageError !== null)
    if (!validWithPct.length) return { within5: 0, within10: 0, score: 0 }
    const count5 = validWithPct.filter((x) => Math.abs(x.percentageError) <= 5).length
    const count10 = validWithPct.filter((x) => Math.abs(x.percentageError) <= 10).length
    const within5 = Math.round((count5 / validWithPct.length) * 100)
    const within10 = Math.round((count10 / validWithPct.length) * 100)
    return {
      within5,
      within10,
      score: within10,
    }
  }, [periods])

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-mark">
            <Wind size={20} />
          </div>
          <div>
            <b>WindSight</b>
            <small>ENERGY INTELLIGENCE</small>
          </div>
          <button className="mobile-close" onClick={() => setMobileOpen(false)}>
            <X size={18} />
          </button>
        </div>

        <div className="workspace">
          <span className="workspace-dot" />
          North Sea Portfolio <ChevronDown size={14} />
        </div>

        <nav>
          <p className="nav-heading">WORKSPACE</p>
          {navItems.map(({ label, icon: Icon, active }) => (
            <button key={label} className={`nav-item ${active ? 'active' : ''}`}>
              <Icon size={18} />
              {label}
              {active && <span className="active-pip" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <Settings2 size={18} />
            Settings
          </button>
          <button className="nav-item">
            <CircleHelp size={18} />
            Help centre
          </button>
          <div className="user">
            <div className="avatar">JD</div>
            <div>
              <b>Jamie Davies</b>
              <small>Procurement team</small>
            </div>
            <ChevronDown size={15} />
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <button className="scrim" aria-label="Close menu" onClick={() => setMobileOpen(false)} />
      )}

      {/* Main Content Area */}
      <main className="main-content">
        <header className="topbar">
          <button className="menu-trigger" onClick={() => setMobileOpen(true)}>
            <Menu size={20} />
          </button>
          <div className="breadcrumbs">
            <span>Workspace</span>
            <b>/</b>
            <strong>Forecast analysis</strong>
          </div>
          <div className="top-actions">
            <div className="status">
              <span />
              {error ? 'API Offline' : 'Live data'}
            </div>
            <button className="icon-button" aria-label="Search">
              <Search size={18} />
            </button>
            <button className="icon-button" aria-label="Documents">
              <FileText size={18} />
            </button>
          </div>
        </header>

        <div className="page-wrap">
          {/* Page Intro */}
          <section className="page-intro">
            <div>
              <div className="eyebrow">
                FORECAST ANALYSIS <span>•</span> JANUARY 2026
              </div>
              <h1>Wind generation forecast</h1>
              <p>Monitor forecast performance and make confident day-ahead purchasing decisions.</p>
            </div>
            <div className="intro-actions">
              <button
                className="outline-button"
                onClick={() => loadAnalyticsData(true)}
                disabled={loading || refreshing}
              >
                <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
                {refreshing ? 'Refreshing' : 'Refresh data'}
              </button>
              <button className="primary-button">
                <CalendarDays size={16} />
                15 Jan 2026 <ChevronDown size={15} />
              </button>
            </div>
          </section>

          {/* Error Banner State */}
          {error && (
            <div
              style={{
                marginBottom: '20px',
                padding: '14px 18px',
                borderRadius: '8px',
                background: '#34151a',
                border: '1px solid #752932',
                color: '#ffb3b8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
                fontSize: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <AlertCircle size={18} color="#ff7b82" />
                <span>
                  <strong>Backend Connection Error:</strong> {error}
                </span>
              </div>
              <button
                onClick={() => loadAnalyticsData(false)}
                className="outline-button"
                style={{ height: '28px', padding: '0 10px', borderColor: '#ff7b82', color: '#ff7b82' }}
              >
                Retry
              </button>
            </div>
          )}

          {/* KPI Metrics Grid */}
          <section className="metric-grid">
            <Metric
              label="Forecasted generation"
              value={loading ? '...' : `${avgForecast.toLocaleString()} MW`}
              detail={loading ? 'Loading...' : `${validForecasts.length} periods active`}
              icon={Wind}
            />
            <Metric
              label="Actual generation"
              value={loading ? '...' : `${avgActual.toLocaleString()} MW`}
              detail={loading ? 'Loading...' : `${validActuals.length} periods recorded`}
              tone="blue"
              icon={Activity}
            />
            <Metric
              label="Mean absolute error"
              value={loading ? '...' : displayMae}
              detail={loading ? 'Loading...' : `${metrics?.evaluatedPeriods ?? 0} paired periods`}
              tone="amber"
              icon={BarChart3}
            />
            <Metric
              label="Root mean square error"
              value={loading ? '...' : displayRmse}
              detail="Elexon evaluation"
              tone="purple"
              icon={Activity}
            />
          </section>

          {/* Forecast vs Actual Chart */}
          <section className="chart-card">
            <div className="card-header">
              <div>
                <h2>Forecast vs actual generation</h2>
                <p>
                  Half-hourly delivery periods · Decision cutoff {String(decisionHour).padStart(2, '0')}:
                  {String(decisionMinute).padStart(2, '0')} GMT day-ahead
                </p>
              </div>
              <div className="range-controls">
                {['Full day', 'Morning', 'Evening'].map((item) => (
                  <button
                    key={item}
                    className={range === item ? 'selected' : ''}
                    onClick={() => setRange(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <div className="chart-wrap">
              {loading ? (
                <div
                  style={{
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#7895a0',
                    fontSize: '13px',
                  }}
                >
                  <RefreshCw size={18} className="spin" style={{ marginRight: '8px' }} />
                  Retrieving delivery periods from backend...
                </div>
              ) : visibleData.length === 0 ? (
                <div
                  style={{
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#7895a0',
                    fontSize: '13px',
                  }}
                >
                  No forecast or actual data found for this selection.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={visibleData} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
                    <defs>
                      <linearGradient id="forecastFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#65e4b8" stopOpacity={0.16} />
                        <stop offset="100%" stopColor="#65e4b8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#244253" strokeDasharray="3 5" vertical={false} />
                    <XAxis
                      dataKey="time"
                      interval={range === 'Full day' ? 5 : 2}
                      tick={{ fill: '#7893a1', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: '#7893a1', fontSize: 11 }}
                      tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 'auto']}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#102d3d',
                        border: '1px solid #2c5364',
                        borderRadius: 10,
                        color: '#fff',
                      }}
                      formatter={(value, name) => [
                        `${value != null ? value.toLocaleString() : '--'} MW`,
                        name === 'forecast' ? 'Forecast' : 'Actual',
                      ]}
                    />
                    <Legend
                      verticalAlign="top"
                      align="right"
                      iconType="circle"
                      iconSize={7}
                      wrapperStyle={{ color: '#9ab4bf', fontSize: 12, paddingBottom: 12 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="forecast"
                      name="forecast"
                      stroke="#65e4b8"
                      strokeWidth={2.5}
                      fill="url(#forecastFill)"
                    />
                    <Area
                      type="monotone"
                      dataKey="actual"
                      name="actual"
                      stroke="#72a8ff"
                      strokeWidth={2}
                      fill="none"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="chart-foot">
              <span>
                <i className="legend-mint" />
                Latest eligible forecast before 10:00 GMT D-1
              </span>
              <span>
                <i className="legend-blue" />
                Actual generation · Elexon BMRS (FUELHH)
              </span>
              <span className="confidence">
                Evaluated periods: <b>{metrics?.evaluatedPeriods ?? visibleData.length}</b>
              </span>
            </div>
          </section>

          {/* Lower Grid: Delivery Table & Accuracy Snapshot */}
          <section className="lower-grid">
            {/* Delivery Period Detail Table */}
            <div className="table-card">
              <div className="card-header">
                <div>
                  <h2>Delivery period detail</h2>
                  <p>
                    Showing {showAllPeriods ? visibleData.length : Math.min(8, visibleData.length)} of{' '}
                    {periods.length} periods
                  </p>
                </div>
                <button
                  className="filter-button"
                  onClick={() => setShowAllPeriods((prev) => !prev)}
                >
                  <Settings2 size={15} />
                  {showAllPeriods ? 'Show Top 8' : 'Show All'}
                </button>
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Delivery time</th>
                      <th>Published</th>
                      <th>Forecast</th>
                      <th>Actual</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: '#7895a0' }}>
                          Loading period records...
                        </td>
                      </tr>
                    ) : visibleData.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: '#7895a0' }}>
                          No delivery periods available.
                        </td>
                      </tr>
                    ) : (
                      (showAllPeriods ? visibleData : visibleData.slice(0, 8)).map((item) => (
                        <tr key={item.rawTime || item.time}>
                          <td>
                            <b>{item.time}</b> <span className="gmt">GMT</span>
                          </td>
                          <td>{item.publishTimeFormatted}</td>
                          <td>{item.forecast != null ? `${item.forecast.toLocaleString()} MW` : '--'}</td>
                          <td>{item.actual != null ? `${item.actual.toLocaleString()} MW` : '--'}</td>
                          <td
                            className={
                              item.error == null
                                ? ''
                                : item.error > 0
                                  ? 'error-up'
                                  : 'error-down'
                            }
                          >
                            {item.error == null
                              ? '--'
                              : `${item.error > 0 ? '+' : ''}${item.error.toLocaleString()} MW`}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <button
                className="view-all"
                onClick={() => setShowAllPeriods((prev) => !prev)}
              >
                {showAllPeriods ? 'Collapse delivery periods' : 'View all delivery periods'}{' '}
                <span>{showAllPeriods ? '↑' : '→'}</span>
              </button>
            </div>

            {/* Accuracy Snapshot Card */}
            <aside className="accuracy-card">
              <div className="card-header">
                <div>
                  <h2>Accuracy snapshot</h2>
                  <p>Current forecast performance</p>
                </div>
                <span className="accuracy-badge">
                  {accuracyStats.score >= 85
                    ? 'Excellent'
                    : accuracyStats.score >= 70
                      ? 'Good'
                      : 'Moderate'}
                </span>
              </div>

              <div className="accuracy-score">
                <div className="score-ring">
                  <strong>{accuracyStats.score}</strong>
                  <span>/100</span>
                </div>
                <div>
                  <b>High confidence forecast</b>
                  <p>
                    {metrics?.maeMW
                      ? `MAE of ${Math.round(metrics.maeMW)} MW across evaluated delivery periods.`
                      : 'Real-time accuracy based on day-ahead settlement.'}
                  </p>
                </div>
              </div>

              <div className="accuracy-bar">
                <div>
                  <span>Within ±5% error</span>
                  <b>{accuracyStats.within5}%</b>
                </div>
                <div className="bar">
                  <span style={{ width: `${accuracyStats.within5}%` }} />
                </div>
              </div>

              <div className="accuracy-bar">
                <div>
                  <span>Within ±10% error</span>
                  <b>{accuracyStats.within10}%</b>
                </div>
                <div className="bar">
                  <span style={{ width: `${accuracyStats.within10}%` }} />
                </div>
              </div>

              <div className="last-updated">
                <span className="workspace-dot" />
                {lastFetched
                  ? `Last updated ${lastFetched.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
                  : 'Awaiting sync with Elexon API'}
              </div>
            </aside>
          </section>
        </div>
      </main>
    </div>
  )
}
