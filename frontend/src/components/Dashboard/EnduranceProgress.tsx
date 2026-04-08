import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, Activity, Trophy } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface ProgressEntry {
  date: string;
  distance_km: number | null;
  duration_minutes: number | null;
  pace_min_per_km: number | null;
  speed_kmh: number | null;
}

interface EnduranceSummary {
  total_distance_km: number;
  total_duration_minutes: number;
  total_sessions: number;
  avg_pace_min_per_km: number | null;
  best_pace_min_per_km: number | null;
  avg_speed_kmh: number | null;
  best_speed_kmh: number | null;
  longest_distance_km: number | null;
}

interface EnduranceProgressData {
  sport: string;
  progress: ProgressEntry[];
  summary: EnduranceSummary;
}

interface EnduranceProgressProps {
  sport: string;
  apiUrl?: string;
  days?: number;
}

const SPORT_COLORS: Record<string, { line: string; fill: string; bg: string; text: string }> = {
  running: { line: '#f97316', fill: '#f97316', bg: 'bg-orange-500/20', text: 'text-orange-400' },
  cycling: { line: '#84cc16', fill: '#84cc16', bg: 'bg-lime-500/20', text: 'text-lime-400' },
  swimming: { line: '#06b6d4', fill: '#06b6d4', bg: 'bg-cyan-500/20', text: 'text-cyan-400' },
};

const W = 500;
const H = 160;
const PAD = { t: 8, r: 8, b: 24, l: 36 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

function formatPace(pace: number | null): string {
  if (pace === null) return '-';
  const mins = Math.floor(pace);
  const secs = Math.round((pace - mins) * 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function EnduranceProgress({
  sport,
  apiUrl = 'http://localhost:8000',
  days = 90,
}: EnduranceProgressProps) {
  const [data, setData] = useState<EnduranceProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPace, setShowPace] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);

  const colors = SPORT_COLORS[sport] || SPORT_COLORS.running;

  useEffect(() => {
    setLoading(true);
    cachedFetch<EnduranceProgressData>(
      `${apiUrl}/dashboard/endurance-progress?sport=${encodeURIComponent(sport)}&days=${days}`
    )
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, sport, days]);

  if (loading) {
    return <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="endurance-progress-loading" />;
  }

  if (error) {
    return <div className="text-red-400 p-4" data-testid="endurance-progress-error">Error: {error}</div>;
  }

  if (!data || data.progress.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="endurance-progress-empty">
        <h3 className="text-lg font-semibold text-foreground mb-2">{sport.charAt(0).toUpperCase() + sport.slice(1)} Progress</h3>
        <p className="text-muted-foreground">No data for this sport yet.</p>
      </div>
    );
  }

  const n = data.progress.length;
  const values = showPace
    ? (sport === 'cycling'
      ? data.progress.map((p) => p.speed_kmh)
      : data.progress.map((p) => p.pace_min_per_km))
    : data.progress.map((p) => p.distance_km);

  const nonNull = values.filter((v): v is number => v !== null);
  const yMin = nonNull.length > 0 ? Math.min(...nonNull) : 0;
  const yMax = nonNull.length > 0 ? Math.max(...nonNull) : 1;
  const yPad = (yMax - yMin) * 0.15 || 1;
  const scaleMin = Math.max(0, yMin - yPad);
  const scaleMax = yMax + yPad;

  function sx(i: number) {
    return PAD.l + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
  }
  function sy(val: number) {
    return PAD.t + plotH - ((val - scaleMin) / (scaleMax - scaleMin)) * plotH;
  }

  // Build polyline segments (skip nulls)
  const segments: string[][] = [];
  let current: string[] = [];
  values.forEach((v, i) => {
    if (v !== null) {
      current.push(`${sx(i)},${sy(v)}`);
    } else if (current.length > 0) {
      segments.push(current);
      current = [];
    }
  });
  if (current.length > 0) segments.push(current);

  // Area polygon
  const areaSegment = segments[0] || [];
  const areaPoints = areaSegment.length > 0
    ? [`${areaSegment[0].split(',')[0]},${sy(scaleMin)}`, ...areaSegment, `${areaSegment[areaSegment.length - 1].split(',')[0]},${sy(scaleMin)}`].join(' ')
    : '';

  // Trend
  const firstDist = data.progress[0]?.distance_km;
  const lastDist = data.progress[n - 1]?.distance_km;
  let trend: 'up' | 'down' | 'flat' = 'flat';
  let trendPercent = 0;
  if (firstDist && lastDist) {
    if (lastDist > firstDist) { trend = 'up'; trendPercent = ((lastDist - firstDist) / firstDist) * 100; }
    else if (lastDist < firstDist) { trend = 'down'; trendPercent = ((firstDist - lastDist) / firstDist) * 100; }
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-muted-foreground';

  // X ticks
  const xTickCount = Math.min(8, n);
  const xTicks = Array.from({ length: xTickCount }, (_, i) => {
    const idx = n === 1 ? 0 : Math.round((i / (xTickCount - 1)) * (n - 1));
    return {
      x: sx(idx),
      label: new Date(data.progress[idx].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    };
  });

  // Y ticks
  const yRange = scaleMax - scaleMin;
  const yStep = yRange > 50 ? 20 : yRange > 20 ? 10 : yRange > 5 ? 5 : yRange > 2 ? 1 : 0.5;
  const yTicks: number[] = [];
  for (let v = Math.ceil(scaleMin / yStep) * yStep; v <= scaleMax; v += yStep) yTicks.push(v);

  const hoveredEntry = hovered !== null ? data.progress[hovered] : null;
  const hoveredVal = hovered !== null ? values[hovered] : null;

  const sportLabel = sport.charAt(0).toUpperCase() + sport.slice(1);
  const gradientId = `enduranceGrad-${sport}`;

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="endurance-progress">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 ${colors.bg} rounded-lg`}>
            <Activity className={`w-5 h-5 ${colors.text}`} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">{sportLabel} Progress</h3>
            <p className="text-sm text-muted-foreground">{data.summary.total_sessions} sessions</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex bg-secondary rounded-lg p-1">
            <button
              className={`px-2 py-1 text-xs rounded transition-colors ${!showPace ? `bg-card ${colors.text}` : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setShowPace(false)}
            >Distance</button>
            <button
              className={`px-2 py-1 text-xs rounded transition-colors ${showPace ? `bg-card ${colors.text}` : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setShowPace(true)}
            >{sport === 'cycling' ? 'Speed' : 'Pace'}</button>
          </div>

          <div className="text-right">
            <div className="flex items-center gap-1">
              <TrendIcon className={`w-4 h-4 ${trendColor}`} />
              <span className="text-xl font-bold text-foreground">
                {data.summary.total_distance_km.toFixed(1)} km
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {trend !== 'flat' && (
                <span className={trendColor}>{trend === 'up' ? '+' : '-'}{trendPercent.toFixed(1)}%</span>
              )}
              {' '}total distance
            </p>
          </div>
        </div>
      </div>

      <div className="relative h-48">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
          {/* Y grid */}
          {yTicks.map((v) => (
            <g key={v}>
              <line x1={PAD.l} x2={W - PAD.r} y1={sy(v)} y2={sy(v)} stroke="#3f3f46" strokeWidth="0.5" />
              <text x={PAD.l - 4} y={sy(v) + 3} fill="#71717a" fontSize="8" textAnchor="end">
                {Number.isInteger(v) ? v : v.toFixed(1)}
              </text>
            </g>
          ))}

          {/* Area fill */}
          {areaPoints && (
            <>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.fill} stopOpacity="0.25" />
                  <stop offset="100%" stopColor={colors.fill} stopOpacity="0" />
                </linearGradient>
              </defs>
              <polygon points={areaPoints} fill={`url(#${gradientId})`} />
            </>
          )}

          {/* Lines */}
          {segments.map((seg, si) => (
            <polyline key={si} points={seg.join(' ')} fill="none" stroke={colors.line} strokeWidth="2" strokeLinejoin="round" />
          ))}

          {/* Data points */}
          {values.map((v, i) =>
            v !== null ? (
              <circle key={i} cx={sx(i)} cy={sy(v)} r="3.5" fill={colors.line}
                stroke={hovered === i ? '#fff' : 'none'} strokeWidth="2" />
            ) : null
          )}

          {/* Hover targets */}
          {data.progress.map((_, i) => (
            <rect key={`h-${i}`}
              x={sx(i) - (n > 1 ? plotW / (n - 1) / 2 : 10)} y={PAD.t}
              width={n > 1 ? plotW / (n - 1) : 20} height={plotH}
              fill="transparent" style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}

          {/* X labels */}
          {xTicks.map((t, i) => (
            <text key={i} x={t.x} y={H - 4} fill="#71717a" fontSize="8" textAnchor="middle">{t.label}</text>
          ))}
        </svg>

        {/* Tooltip */}
        {hoveredEntry && hovered !== null && hoveredVal !== null && (
          <div
            className="absolute pointer-events-none bg-popover text-popover-foreground rounded-md shadow-lg border border-border px-3 py-2 text-xs z-10"
            style={{
              left: `${(sx(hovered) / W) * 100}%`,
              top: `${(sy(hoveredVal) / H) * 100}%`,
              transform: 'translate(-50%, -120%)',
            }}
          >
            <div className="font-medium text-foreground mb-1">
              {new Date(hoveredEntry.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
            </div>
            {hoveredEntry.distance_km !== null && (
              <div className={colors.text}>Distance: {hoveredEntry.distance_km.toFixed(1)} km</div>
            )}
            {hoveredEntry.duration_minutes !== null && (
              <div className="text-muted-foreground">Duration: {formatDuration(hoveredEntry.duration_minutes)}</div>
            )}
            {sport === 'cycling' ? (
              hoveredEntry.speed_kmh !== null && <div className="text-muted-foreground">Speed: {hoveredEntry.speed_kmh.toFixed(1)} km/h</div>
            ) : (
              hoveredEntry.pace_min_per_km !== null && <div className="text-muted-foreground">Pace: {formatPace(hoveredEntry.pace_min_per_km)} /km</div>
            )}
          </div>
        )}
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 pt-3 border-t border-border">
        <div>
          <p className="text-xs text-muted-foreground">Total Distance</p>
          <p className="text-sm font-semibold text-foreground">{data.summary.total_distance_km.toFixed(1)} km</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Total Time</p>
          <p className="text-sm font-semibold text-foreground">{formatDuration(data.summary.total_duration_minutes)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">
            {sport === 'cycling' ? 'Best Speed' : 'Best Pace'}
          </p>
          <p className="text-sm font-semibold text-foreground inline-flex items-center gap-1">
            <Trophy className="w-3.5 h-3.5 text-amber-400" />
            {sport === 'cycling'
              ? (data.summary.best_speed_kmh !== null ? `${data.summary.best_speed_kmh.toFixed(1)} km/h` : '-')
              : (data.summary.best_pace_min_per_km !== null ? `${formatPace(data.summary.best_pace_min_per_km)} /km` : '-')}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Longest Run</p>
          <p className="text-sm font-semibold text-foreground">
            {data.summary.longest_distance_km !== null ? `${data.summary.longest_distance_km.toFixed(1)} km` : '-'}
          </p>
        </div>
      </div>
    </div>
  );
}
