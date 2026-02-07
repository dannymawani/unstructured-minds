import { useEffect, useState } from 'react';
import { Moon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface MetricEntry {
  date: string;
  sleep_hours: number | null;
  sleep_quality: number | null;
}

interface SleepTrendsData {
  metrics: MetricEntry[];
}

interface SleepTrendsProps {
  apiUrl?: string;
  days?: number;
  onDayClick?: (date: string) => void;
}

// SVG layout constants
const W = 400;
const H = 160;
const PAD = { t: 8, r: 8, b: 24, l: 36 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;
const Y_MIN = 0;
const Y_MAX = 12;

function sx(i: number, count: number) {
  return PAD.l + (count > 1 ? (i / (count - 1)) * plotW : plotW / 2);
}

function sy(val: number) {
  return PAD.t + plotH - ((val - Y_MIN) / (Y_MAX - Y_MIN)) * plotH;
}

export function SleepTrends({
  apiUrl = 'http://localhost:8000',
  days = 30,
  onDayClick,
}: SleepTrendsProps) {
  const [data, setData] = useState<SleepTrendsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    cachedFetch<SleepTrendsData>(`${apiUrl}/dashboard/metrics-trends?days=${days}`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, days]);

  if (loading) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="sleep-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="sleep-error">
        Error: {error}
      </div>
    );
  }

  if (!data || data.metrics.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="sleep-empty">
        <h3 className="text-lg font-semibold text-foreground mb-2">Sleep Trends</h3>
        <p className="text-muted-foreground">No sleep data recorded yet.</p>
      </div>
    );
  }

  const sleepData = data.metrics.filter((m) => m.sleep_hours !== null);

  if (sleepData.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="sleep-empty">
        <h3 className="text-lg font-semibold text-foreground mb-2">Sleep Trends</h3>
        <p className="text-muted-foreground">No sleep data recorded yet.</p>
      </div>
    );
  }

  const n = sleepData.length;
  const values = sleepData.map((m) => m.sleep_hours || 0);
  const avgSleep = values.reduce((a, b) => a + b, 0) / n;
  const recentAvg = values.slice(-7).reduce((a, b) => a + b, 0) / Math.min(7, n);
  const prevSlice = values.slice(-14, -7);
  const previousAvg = prevSlice.length > 0 ? prevSlice.reduce((a, b) => a + b, 0) / prevSlice.length : recentAvg;

  let trend: 'up' | 'down' | 'flat' = 'flat';
  if (recentAvg > previousAvg + 0.25) trend = 'up';
  else if (recentAvg < previousAvg - 0.25) trend = 'down';

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-muted-foreground';

  // Build SVG points
  const points = values.map((v, i) => `${sx(i, n)},${sy(v)}`);
  const polyline = points.join(' ');
  // Area polygon: line + close along bottom
  const areaPoints = [
    `${sx(0, n)},${sy(Y_MIN)}`,
    ...points,
    `${sx(n - 1, n)},${sy(Y_MIN)}`,
  ].join(' ');

  const goalY = sy(8);

  // Tick labels on X axis (show ~6 evenly spaced)
  const xTickCount = Math.min(6, n);
  const xTicks = Array.from({ length: xTickCount }, (_, i) => {
    const idx = Math.round((i / (xTickCount - 1)) * (n - 1));
    return {
      x: sx(idx, n),
      label: new Date(sleepData[idx].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    };
  });

  const hoveredEntry = hovered !== null ? sleepData[hovered] : null;

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="sleep-trends">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2">
          <Moon className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-foreground">Sleep Trends</h3>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1">
            <TrendIcon className={`w-4 h-4 ${trendColor}`} />
            <span className="text-xl font-bold text-foreground">{avgSleep.toFixed(1)} hrs</span>
          </div>
          <p className="text-xs text-muted-foreground">avg / night</p>
        </div>
      </div>

      <div className="relative h-48">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
          {/* Y grid lines */}
          {[0, 4, 8, 12].map((v) => (
            <line key={v} x1={PAD.l} x2={W - PAD.r} y1={sy(v)} y2={sy(v)} stroke="#3f3f46" strokeWidth="0.5" />
          ))}
          {/* Y labels */}
          {[0, 4, 8, 12].map((v) => (
            <text key={`yl-${v}`} x={PAD.l - 6} y={sy(v) + 3} fill="#71717a" fontSize="9" textAnchor="end">{v}h</text>
          ))}
          {/* 8h goal line */}
          <line x1={PAD.l} x2={W - PAD.r} y1={goalY} y2={goalY} stroke="#22c55e" strokeWidth="0.8" strokeDasharray="4 3" />
          <text x={W - PAD.r + 4} y={goalY + 3} fill="#22c55e" fontSize="8">8h goal</text>
          {/* Area fill */}
          <polygon points={areaPoints} fill="url(#sleepGrad)" />
          <defs>
            <linearGradient id="sleepGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* Line */}
          <polyline points={polyline} fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinejoin="round" />
          {/* Data points + hover targets */}
          {values.map((v, i) => (
            <g key={i}>
              <circle cx={sx(i, n)} cy={sy(v)} r="3" fill="#3b82f6" stroke={hovered === i ? '#fff' : 'none'} strokeWidth="2" />
              <circle
                cx={sx(i, n)} cy={sy(v)} r="12" fill="transparent"
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => onDayClick?.(sleepData[i].date)}
              />
            </g>
          ))}
          {/* X labels */}
          {xTicks.map((t, i) => (
            <text key={i} x={t.x} y={H - 4} fill="#71717a" fontSize="8" textAnchor="middle">{t.label}</text>
          ))}
        </svg>

        {/* Tooltip */}
        {hoveredEntry && hovered !== null && (
          <div
            className="absolute pointer-events-none bg-popover text-popover-foreground rounded-md shadow-lg border border-border px-3 py-2 text-sm z-10"
            style={{
              left: `${(sx(hovered, n) / W) * 100}%`,
              top: `${(sy(values[hovered]) / H) * 100}%`,
              transform: 'translate(-50%, -120%)',
            }}
          >
            <div className="font-medium text-foreground text-xs mb-1">
              {new Date(hoveredEntry.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </div>
            <div className="text-blue-400 text-xs">{(hoveredEntry.sleep_hours || 0).toFixed(1)} hours</div>
            {hoveredEntry.sleep_quality !== null && (
              <div className="text-muted-foreground text-xs">Quality: {hoveredEntry.sleep_quality}/10</div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
        <span>Last {days} days</span>
        <span>
          7-day avg: {recentAvg.toFixed(1)} hrs {trend === 'up' ? '(improving)' : trend === 'down' ? '(declining)' : ''}
        </span>
      </div>
    </div>
  );
}
