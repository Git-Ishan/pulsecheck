import { useEffect, useState } from 'react'
import { fetchStats } from './api'
import type { Stats } from './api'
import './App.css'

function StatCard({ label, value, kind }: { label: string; value: number; kind: string }) {
  return (
    <div className={`card ${kind}`}>
      <span className="number">{value}</span>
      {label}
    </div>
  )
}

function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((err: Error) => setError(err.message))
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
    </main>
  )
}

export default App
