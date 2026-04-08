import { useEffect, useState, useMemo } from 'react';
import { Activity, Eye, EyeOff } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface MetricEntry {
  date: string;
  sleep_hours: number | null;
  energy: number | null;
  mood: number | null;
  stress: number | null;
}

interface MetricsTrendsData {
  metrics: MetricEntry[];
}

interface MetricsTrendsProps {
  apiUrl?: string;
  days?: number;
  onDayClick?: (date: string) => void;
}

interface MetricConfig {
  key: string;
  dataKey: keyof MetricEntry;
  label: string;
  color: string;
}

const METRICS: MetricConfig[] = [
  { key: 'energy', dataKey: 'energy', label: 'Energy', color: '#22c55e' },
  { key: 'mood', dataKey: 'mood', label: 'Mood', color: '#3b82f6' },
  { key: 'stress', dataKey: 'stress', label: 'Stress', color: '#ef4444' },
  { key: 'sleep', dataKey: 'sleep_hours', label: 'Sleep', color: '#8b5cf6' },
];

// SVG layout
const W = 400;
const H = 160;
const PAD = { t: 8, r: 8, b: 24, l: 28 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;
const Y_MIN = 0;
const Y_MAX = 10;

function sx(i: number, count: number) {
  return PAD.l + (count > 1 ? (i / (count - 1)) * plotW : plotW / 2);
}
function sy(val: number) {
  return PAD.t + plotH - ((val - Y_MIN) / (Y_MAX - Y_MIN)) * plotH;
}

export function MetricsTrends({
  apiUrl = 'http://localhost:8000',
  days = 7,
  onDayClick,
}: MetricsTrendsProps) {
  const [data, setData] = useState<MetricsTrendsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleMetrics, setVisibleMetrics] = useState<Set<string>>(
    new Set(['energy', 'mood', 'stress'])
  );
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    cachedFetch<MetricsTrendsData>(`${apiUrl}/dashboard/metrics-trends?days=${days}`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, days]);

  const averages = useMemo(() => {
    if (!data || data.metrics.length === 0) return {};
    const result: Record<string, number> = {};
    for (const metric of METRICS) {
      const values = data.metrics
        .map((m) => m[metric.dataKey] as number | null)
        .filter((v): v is number => v !== null);
      if (values.length > 0) {
        result[metric.key] = values.reduce((a, b) => a + b, 0) / values.length;
      }
    }
    return result;
  }, [data]);

  const toggleMetric = (key: string) => {
    setVisibleMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="metrics-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="metrics-error">
        Error: {error}
      </div>
    );
  }

  if (!data || data.metrics.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="metrics-empty">
        <h3 className="text-lg font-semibold text-foreground mb-2">Daily Metrics</h3>
        <p className="text-muted-foreground">No metrics recorded yet.</p>
      </div>
    );
  }

  const n = data.metrics.length;

  // X ticks
  const xTickCount = Math.min(6, n);
  const xTicks = Array.from({ length: xTickCount }, (_, i) => {
    const idx = n === 1 ? 0 : Math.round((i / (xTickCount - 1)) * (n - 1));
    return {
      x: sx(idx, n),
      label: new Date(data.metrics[idx].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    };
  });

  const hoveredEntry = hovered !== null ? data.metrics[hovered] : null;

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="metrics-trends">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Activity className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Daily Metrics</h3>
            <p className="text-sm text-muted-foreground">{n} days</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {METRICS.map((metric) => (
            <button
              key={metric.key}
              onClick={() => toggleMetric(metric.key)}
              className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded-lg transition-colors ${
                visibleMetrics.has(metric.key)
                  ? 'bg-secondary text-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}
              style={{
                borderLeft: visibleMetrics.has(metric.key)
                  ? `3px solid ${metric.color}`
                  : '3px solid transparent',
              }}
            >
              {visibleMetrics.has(metric.key) ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
              {metric.label}
            </button>
          ))}
        </div>
      </div>

      <div className="relative h-56">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
          {/* Y grid */}
          {[0, 2, 4, 6, 8, 10].map((v) => (
            <line key={v} x1={PAD.l} x2={W - PAD.r} y1={sy(v)} y2={sy(v)} stroke="#3f3f46" strokeWidth="0.5" />
          ))}
          {[0, 5, 10].map((v) => (
            <text key={`yl-${v}`} x={PAD.l - 4} y={sy(v) + 3} fill="#71717a" fontSize="8" textAnchor="end">{v}</text>
          ))}

          {/* Lines for each visible metric */}
          {METRICS.filter((m) => visibleMetrics.has(m.key)).map((metric) => {
            const vals = data.metrics.map((entry) => entry[metric.dataKey] as number | null);
            // Build polyline skipping nulls (segments between non-null points)
            const segments: string[] = [];
            let currentSegment: string[] = [];
            vals.forEach((v, i) => {
              if (v !== null) {
                currentSegment.push(`${sx(i, n)},${sy(v)}`);
              } else if (currentSegment.length > 0) {
                segments.push(currentSegment.join(' '));
                currentSegment = [];
              }
            });
            if (currentSegment.length > 0) segments.push(currentSegment.join(' '));

            return (
              <g key={metric.key}>
                {segments.map((seg, si) => (
                  <polyline
                    key={si}
                    points={seg}
                    fill="none"
                    stroke={metric.color}
                    strokeWidth="2"
                    strokeLinejoin="round"
                  />
                ))}
                {vals.map((v, i) =>
                  v !== null ? (
                    <circle key={i} cx={sx(i, n)} cy={sy(v)} r="2.5" fill={metric.color}
                      stroke={hovered === i ? '#fff' : 'none'} strokeWidth="1.5" />
                  ) : null
                )}
              </g>
            );
          })}

          {/* Invisible hover targets (one per data point column) */}
          {data.metrics.map((_, i) => (
            <rect
              key={`hover-${i}`}
              x={sx(i, n) - (n > 1 ? plotW / (n - 1) / 2 : 10)}
              y={PAD.t}
              width={n > 1 ? plotW / (n - 1) : 20}
              height={plotH}
              fill="transparent"
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onDayClick?.(data.metrics[i].date)}
            />
          ))}

          {/* Hover indicator line */}
          {hovered !== null && (
            <line x1={sx(hovered, n)} x2={sx(hovered, n)} y1={PAD.t} y2={PAD.t + plotH} stroke="#71717a" strokeWidth="0.5" strokeDasharray="3 2" />
          )}

          {/* X labels */}
          {xTicks.map((t, i) => (
            <text key={i} x={t.x} y={H - 4} fill="#71717a" fontSize="8" textAnchor="middle">{t.label}</text>
          ))}
        </svg>

        {/* Tooltip */}
        {hoveredEntry && hovered !== null && (
          <div
            className="absolute pointer-events-none bg-popover text-popover-foreground rounded-md shadow-lg border border-border px-3 py-2 text-xs z-10"
            style={{
              left: `${(sx(hovered, n) / W) * 100}%`,
              top: 0,
              transform: 'translateX(-50%)',
            }}
          >
            <div className="font-medium text-foreground mb-1">
              {new Date(hoveredEntry.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </div>
            {METRICS.filter((m) => visibleMetrics.has(m.key)).map((metric) => {
              const val = hoveredEntry[metric.dataKey] as number | null;
              if (val === null) return null;
              return (
                <div key={metric.key} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: metric.color }} />
                  <span className="text-muted-foreground">{metric.label}:</span>
                  <span className="text-foreground font-medium">
                    {metric.key === 'sleep' ? `${val.toFixed(1)} hrs` : `${val}/10`}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Averages footer */}
      <div className="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-border text-xs">
        <span className="text-muted-foreground">Averages:</span>
        {METRICS.filter((m) => visibleMetrics.has(m.key)).map((metric) => (
          <span key={metric.key} className="flex items-center gap-1" style={{ color: metric.color }}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: metric.color }} />
            {metric.label}:{' '}
            {metric.key === 'sleep'
              ? `${(averages[metric.key] || 0).toFixed(1)} hrs`
              : `${(averages[metric.key] || 0).toFixed(1)}/10`}
          </span>
        ))}
      </div>
    </div>
  );
}
