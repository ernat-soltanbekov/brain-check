export default function PerformanceChart({ attempts }) {
  const points = [...attempts].slice(0, 12).reverse()
  if (!points.length)
    return <p className="muted">Complete your first session to start your progression chart.</p>
  const x = (i) => (points.length === 1 ? 300 : 35 + (i * 530) / (points.length - 1))
  const y = (score) => 145 - score * 1.15
  return (
    <div className="chart">
      <svg
        viewBox="0 0 600 185"
        role="img"
        aria-label={`Recent quiz scores: ${points.map((p) => `${p.score}%`).join(', ')}`}
      >
        <defs>
          <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6e947b" stopOpacity=".24" />
            <stop offset="100%" stopColor="#6e947b" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 50, 100].map((score) => (
          <g key={score}>
            <line
              x1="35"
              x2="575"
              y1={y(score)}
              y2={y(score)}
              stroke="#e4e7df"
              strokeDasharray="4 5"
            />
            <text x="0" y={y(score) + 4} fontSize="10" fill="#7b847d">
              {score}
            </text>
          </g>
        ))}
        <path
          d={`M ${x(0)} 145 ${points.map((p, i) => `L ${x(i)} ${y(p.score)}`).join(' ')} L ${x(points.length - 1)} 145 Z`}
          fill="url(#chart-fill)"
        />
        <polyline
          points={points.map((p, i) => `${x(i)},${y(p.score)}`).join(' ')}
          fill="none"
          stroke="#3f7058"
          strokeWidth="2.5"
        />
        {points.map((p, i) => (
          <g key={p.id}>
            <circle cx={x(i)} cy={y(p.score)} r="4" fill="#3f7058" stroke="#fff" strokeWidth="2">
              <title>
                {p.title}: {p.score}% · {p.difficulty}
              </title>
            </circle>
            <text x={x(i)} y="174" textAnchor="middle" fontSize="10" fill="#7b847d">
              {i + 1}
            </text>
          </g>
        ))}
      </svg>
      <p className="chart-caption">
        SESSION NUMBER <span>Objective score (%)</span>
      </p>
    </div>
  )
}
