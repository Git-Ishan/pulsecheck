import { useEffect, useState } from 'react'
import { fetchMonitors, fetchStats } from './api'
import type { Monitor, Stats } from './api'
import './App.css'

const REFRESH_MS = 10_000

function StatCard({ label, value, kind }: { label: string; value: number; kind: string }) {
  return (
    <div className={`card ${kind}`}>
      <span className="number">{value}</span>
      {label}
    </div>
  )
}

function StatusBadge({ status }: { status: Monitor['current_status'] }) {
  return <span className={`badge ${status.toLowerCase()}`}>{status}</span>
}

function formatTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : 'never'
}

function MonitorRow({ monitor }: { monitor: Monitor }) {
  return (
    <tr>
      <td>
        <strong>{monitor.name ?? monitor.url}</strong>
        {monitor.name && <div className="muted">{monitor.url}</div>}
      </td>
      <td>
        <StatusBadge status={monitor.current_status} />
      </td>
      <td>{monitor.last_response_time_ms !== null ? `${monitor.last_response_time_ms} ms` : '-'}</td>
      <td>{monitor.last_http_status ?? '-'}</td>
      <td>{formatTime(monitor.last_checked_at)}</td>
    </tr>
  )
}

function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [monitors, setMonitors] = useState<Monitor[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [newStats, newMonitors] = await Promise.all([fetchStats(), fetchMonitors()])
        if (!cancelled) {
          setStats(newStats)
          setMonitors(newMonitors)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError((err as Error).message)
      }
    }

    load()
    const timer = setInterval(load, REFRESH_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  return (
    <main>
      <h1>PulseCheck</h1>
      {error && <p className="error">Could not reach the API: {error}</p>}
      {!error && !stats && <p>Loading...</p>}
      {stats && (
        <section className="cards">
          <StatCard label="Total" value={stats.total} kind="total" />
          <StatCard label="Up" value={stats.up} kind="up" />
          <StatCard label="Down" value={stats.down} kind="down" />
          <StatCard label="Unknown" value={stats.unknown} kind="unknown" />
        </section>
      )}
      {monitors && monitors.length === 0 && <p className="muted">No monitors yet.</p>}
      {monitors && monitors.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Monitor</th>
              <th>Status</th>
              <th>Response</th>
              <th>HTTP</th>
              <th>Last checked</th>
            </tr>
          </thead>
          <tbody>
            {monitors.map((m) => (
              <MonitorRow key={m.id} monitor={m} />
            ))}
          </tbody>
        </table>
      )}
      <p className="muted">Refreshes every {REFRESH_MS / 1000} seconds.</p>
    </main>
  )
}

export default App
