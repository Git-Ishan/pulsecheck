import { useEffect, useState } from 'react'
import { deleteMonitor, fetchChecks, fetchIncidents, fetchUptime } from './api'
import type { CheckResult, Incident, Monitor, Uptime } from './api'
import ResponseChart from './ResponseChart'

const REFRESH_MS = 10_000

type Data = { uptime: Uptime; checks: CheckResult[]; incidents: Incident[] }

function formatTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : 'ongoing'
}

function formatDuration(startIso: string, endIso: string): string {
  const seconds = Math.max(0, Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000))
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m`
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

export default function MonitorDetail({
  monitor,
  apiKey,
  onDeleted,
}: {
  monitor: Monitor
  apiKey: string
  onDeleted: () => void
}) {
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [uptime, checks, incidents] = await Promise.all([
          fetchUptime(monitor.id),
          fetchChecks(monitor.id),
          fetchIncidents(monitor.id),
        ])
        if (!cancelled) {
          setData({ uptime, checks, incidents })
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
  }, [monitor.id])

  async function handleDelete() {
    if (!apiKey) {
      setMessage('Enter the API key in the form above first.')
      return
    }
    if (!window.confirm(`Delete "${monitor.name ?? monitor.url}" and all of its history?`)) return
    setBusy(true)
    setMessage(null)
    try {
      await deleteMonitor(apiKey, monitor.id)
      onDeleted()
    } catch (err) {
      setMessage((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <section className="detail">
      <div className="detail-head">
        <h2>{monitor.name ?? monitor.url}</h2>
        <button className="danger" onClick={handleDelete} disabled={busy}>
          Delete
        </button>
      </div>
      {message && <p className="error">{message}</p>}
      {error && <p className="error">Could not load details: {error}</p>}
      {data && (
        <>
          <div className="summary">
            <div>
              <span className="number">
                {data.uptime.uptime_percent !== null ? `${data.uptime.uptime_percent}%` : 'n/a'}
              </span>
              uptime, last {data.uptime.window_hours}h
            </div>
            <div>
              <span className="number">{data.uptime.sample_size}</span>
              checks in that window
            </div>
            <div>
              <span className="number">
                {data.uptime.average_response_time_ms !== null
                  ? `${data.uptime.average_response_time_ms} ms`
                  : 'n/a'}
              </span>
              average response (successful checks)
            </div>
          </div>
          <p className="muted">
            Uptime is a check-based estimate: successful checks divided by all completed checks in the window.
            It says nothing about the time between checks.
          </p>

          <ResponseChart checks={data.checks} />

          <h3>Incidents</h3>
          {data.incidents.length === 0 ? (
            <p className="muted">No incidents recorded.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Resolved</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {data.incidents.map((i) => (
                  <tr key={i.id}>
                    <td>{formatTime(i.started_at)}</td>
                    <td>{formatTime(i.resolved_at)}</td>
                    <td>{i.resolved_at ? formatDuration(i.started_at, i.resolved_at) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Recent checks</h3>
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Result</th>
                <th>HTTP</th>
                <th>Response</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {data.checks.slice(0, 10).map((c) => (
                <tr key={c.id}>
                  <td>{formatTime(c.checked_at)}</td>
                  <td>{c.healthy ? 'OK' : 'FAIL'}</td>
                  <td>{c.http_status_code ?? '-'}</td>
                  <td>{c.response_time_ms !== null ? `${c.response_time_ms} ms` : '-'}</td>
                  <td>{c.error_type ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
