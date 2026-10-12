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
