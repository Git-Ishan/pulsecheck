const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export type Stats = {
  total: number
  up: number
  down: number
  unknown: number
}

export type Monitor = {
  id: number
  name: string | null
  url: string
  enabled: boolean
  current_status: 'UNKNOWN' | 'UP' | 'DOWN'
  consecutive_failures: number
  last_checked_at: string | null
  last_response_time_ms: number | null
  last_http_status: number | null
  created_at: string
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }
  return response.json()
}

export const fetchStats = () => getJson<Stats>('/stats')
export const fetchMonitors = () => getJson<Monitor[]>('/monitors')

function describeError(status: number, detail: unknown): string {
  if (status === 401) return 'The API key is wrong or missing.'
  if (status === 503) return 'The server has no API key configured, so changes are disabled.'
  if (status === 409) return 'The monitor limit has been reached.'
  if (status === 429) return 'Too many requests. Wait a minute and try again.'
  if (status === 422) {
    if (typeof detail === 'string') return detail
    return 'That does not look like a valid http(s) URL.'
  }
  return `Request failed with status ${status}.`
}

export async function createMonitor(apiKey: string, name: string, url: string): Promise<Monitor> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/monitors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
      body: JSON.stringify({ name: name.trim() || null, url: url.trim() }),
    })
  } catch {
    throw new Error('Could not reach the API.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(describeError(response.status, body?.detail))
  }
  return response.json()
}

export type CheckResult = {
  id: number
  monitor_id: number
  checked_at: string
  healthy: boolean
  http_status_code: number | null
  response_time_ms: number | null
  error_type: string | null
}

export type Incident = {
  id: number
  monitor_id: number
  started_at: string
  resolved_at: string | null
}

export type Uptime = {
  monitor_id: number
  window_hours: number
  sample_size: number
  successful_checks: number
  failed_checks: number
  uptime_percent: number | null
  average_response_time_ms: number | null
}

export const fetchChecks = (id: number, limit = 50) =>
  getJson<CheckResult[]>(`/monitors/${id}/checks?limit=${limit}`)
export const fetchIncidents = (id: number) =>
  getJson<Incident[]>(`/monitors/${id}/incidents?limit=10`)
export const fetchUptime = (id: number, hours = 24) =>
  getJson<Uptime>(`/monitors/${id}/uptime?hours=${hours}`)

export async function deleteMonitor(apiKey: string, id: number): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/monitors/${id}`, {
      method: 'DELETE',
      headers: { 'X-API-Key': apiKey },
    })
  } catch {
    throw new Error('Could not reach the API.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(describeError(response.status, body?.detail))
  }
}
