import type { CheckResult } from './api'

const WIDTH = 600
const HEIGHT = 140
const PAD = 8

export default function ResponseChart({ checks }: { checks: CheckResult[] }) {
  const ordered = [...checks].reverse() // the API returns newest first
  if (ordered.length < 2) {
    return <p className="muted">Not enough checks yet for a chart.</p>
  }

  const times = ordered
    .map((c) => c.response_time_ms)
    .filter((v): v is number => v !== null)
  const maxMs = Math.max(100, ...times)
  const x = (i: number) => PAD + (i / (ordered.length - 1)) * (WIDTH - 2 * PAD)
  const y = (ms: number) => HEIGHT - PAD - (ms / maxMs) * (HEIGHT - 2 * PAD)

  const points = ordered
    .map((c, i) => (c.response_time_ms !== null ? `${x(i)},${y(c.response_time_ms)}` : null))
    .filter((p): p is string => p !== null)
    .join(' ')

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Response time of recent checks">
        {ordered.map(
          (c, i) =>
            !c.healthy && (
              <line
                key={c.id}
                x1={x(i)}
                x2={x(i)}
                y1={PAD}
                y2={HEIGHT - PAD}
                stroke="#dc2626"
                strokeOpacity="0.35"
                strokeWidth="3"
              />
            ),
        )}
        {points && <polyline points={points} fill="none" stroke="#2563eb" strokeWidth="2" />}
      </svg>
      <figcaption className="muted">
        Response time of the last {ordered.length} checks (0 to {maxMs} ms). Red bars are failed checks.
      </figcaption>
    </figure>
  )
}
