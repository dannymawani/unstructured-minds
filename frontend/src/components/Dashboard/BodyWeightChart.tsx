import { useEffect, useState } from 'react';
import { Scale, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface BodyWeightEntry {
  date: string;
  weight_kg: number;
}

interface BodyWeightData {
  entries: BodyWeightEntry[];
  current_kg: number | null;
  period_change_kg: number | null;
}

interface BodyWeightChartProps {
  apiUrl?: string;
  days?: number;
}

// SVG layout constants (same as SleepTrends)
const W = 400;
const H = 160;
const PAD = { t: 8, r: 8, b: 24, l: 42 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

function sx(i: number, count: number) {
  return PAD.l + (count > 1 ? (i / (count - 1)) * plotW : plotW / 2);
}

function sy(val: number, yMin: number, yMax: number) {
  return PAD.t + plotH - ((val - yMin) / (yMax - yMin)) * plotH;
}

export function BodyWeightChart({
  apiUrl = 'http://localhost:8000',
  days = 90,
}: BodyWeightChartProps) {
  const [data, setData] = useState<BodyWeightData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    cachedFetch<BodyWeightData>(`${apiUrl}/dashboard/body-weight?days=${days}`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, days]);

  if (loading) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="weight-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="weight-error">
        Error: {error}
      </div>
    );
  }

  if (!data || data.entries.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="weight-empty">
        <h3 className="text-lg font-semibold text-foreground mb-2">Body Weight</h3>
        <p className="text-muted-foreground">No weight data recorded yet.</p>
      </div>
    );
  }

  const entries = data.entries;
  const n = entries.length;
  const values = entries.map((e) => e.weight_kg);

  // Y-axis range with 2kg padding
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const yPad = Math.max((rawMax - rawMin) * 0.2, 1);
  const yMin = Math.floor(rawMin - yPad);
  const yMax = Math.ceil(rawMax + yPad);

  // Trend: compare last 7 entries vs previous 7
  const recentSlice = values.slice(-7);
  const recentAvg = recentSlice.reduce((a, b) => a + b, 0) / recentSlice.length;
  const prevSlice = values.slice(-14, -7);
  const previousAvg = prevSlice.length > 0 ? prevSlice.reduce((a, b) => a + b, 0) / prevSlice.length : recentAvg;

  let trend: 'up' | 'down' | 'flat' = 'flat';
  if (recentAvg > previousAvg + 0.3) trend = 'up';
  else if (recentAvg < previousAvg - 0.3) trend = 'down';

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'flat' ? 'text-muted-foreground' : 'text-teal-400';

  // Build SVG points
  const points = values.map((v, i) => `${sx(i, n)},${sy(v, yMin, yMax)}`);
  const polyline = points.join(' ');
  const areaPoints = [
    `${sx(0, n)},${sy(yMin, yMin, yMax)}`,
    ...points,
    `${sx(n - 1, n)},${sy(yMin, yMin, yMax)}`,
  ].join(' ');

  // Y-axis ticks: ~4 evenly spaced
  const yRange = yMax - yMin;
  const yStep = Math.max(1, Math.round(yRange / 4));
  const yTicks: number[] = [];
  for (let v = yMin; v <= yMax; v += yStep) {
    yTicks.push(v);
  }

  // X-axis ticks: ~6 evenly spaced
  const xTickCount = Math.min(6, n);
  const xTicks = Array.from({ length: xTickCount }, (_, i) => {
    const idx = xTickCount <= 1 ? 0 : Math.round((i / (xTickCount - 1)) * (n - 1));
    return {
      x: sx(idx, n),
      label: new Date(entries[idx].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    };
  });

  const hoveredEntry = hovered !== null ? entries[hovered] : null;
  const changeSign = data.period_change_kg !== null && data.period_change_kg > 0 ? '+' : '';

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="body-weight-chart">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-teal-400" />
          <h3 className="text-lg font-semibold text-foreground">Body Weight</h3>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1">
            <TrendIcon className={`w-4 h-4 ${trendColor}`} />
            <span className="text-xl font-bold text-foreground">
              {data.current_kg !== null ? `${data.current_kg} kg` : '--'}
            </span>
          </div>
          {data.period_change_kg !== null && (
            <p className="text-xs text-muted-foreground">
              {changeSign}{data.period_change_kg} kg
            </p>
          )}
        </div>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ aspectRatio: `${W}/${H}` }}>
          {/* Y grid lines */}
          {yTicks.map((v) => (
            <line key={v} x1={PAD.l} x2={W - PAD.r} y1={sy(v, yMin, yMax)} y2={sy(v, yMin, yMax)} stroke="#3f3f46" strokeWidth="0.5" />
          ))}
          {/* Y labels */}
          {yTicks.map((v) => (
            <text key={`yl-${v}`} x={PAD.l - 6} y={sy(v, yMin, yMax) + 3} fill="#71717a" fontSize="9" textAnchor="end">{v}</text>
          ))}
          {/* Area fill */}
          <polygon points={areaPoints} fill="url(#weightGrad)" />
          <defs>
            <linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#14b8a6" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#14b8a6" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* Line */}
          <polyline points={polyline} fill="none" stroke="#14b8a6" strokeWidth="2" strokeLinejoin="round" />
          {/* Data points + hover targets */}
          {values.map((v, i) => (
            <g key={i}>
              <circle cx={sx(i, n)} cy={sy(v, yMin, yMax)} r="3" fill="#14b8a6" stroke={hovered === i ? '#fff' : 'none'} strokeWidth="2" />
              <circle
                cx={sx(i, n)} cy={sy(v, yMin, yMax)} r="12" fill="transparent"
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
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
              top: `${(sy(values[hovered], yMin, yMax) / H) * 100}%`,
              transform: 'translate(-50%, -120%)',
            }}
          >
            <div className="font-medium text-foreground text-xs mb-1">
              {new Date(hoveredEntry.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </div>
            <div className="text-teal-400 text-xs">{hoveredEntry.weight_kg} kg</div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
        <span>Last {days} days</span>
        <span>{n} measurements</span>
      </div>
    </div>
  );
}
