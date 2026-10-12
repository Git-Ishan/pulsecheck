const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export type Stats = {
  total: number
  up: number
  down: number
  unknown: number
}

export async function fetchStats(): Promise<Stats> {
  const response = await fetch(`${API_URL}/stats`)
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }
  return response.json()
}
