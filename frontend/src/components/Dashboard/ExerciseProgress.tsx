import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, Dumbbell, Target } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface ProgressEntry {
  date: string;
  max_weight_kg: number | null;
  total_reps: number;
  total_sets: number;
}

interface ExerciseSummary {
  current_max: number | null;
  all_time_max: number | null;
  total_volume: number;
  total_sessions: number;
}

interface ExerciseProgressData {
  exercise: string;
  progress: ProgressEntry[];
  summary: ExerciseSummary;
}

interface ExerciseProgressProps {
  exercise: string;
  apiUrl?: string;
  days?: number;
  onDayClick?: (date: string) => void;
}

// SVG layout
const W = 500;
const H = 160;
const PAD = { t: 8, r: 8, b: 24, l: 36 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

export function ExerciseProgress({
  exercise,
  apiUrl = 'http://localhost:8000',
  days = 30,
  onDayClick,
}: ExerciseProgressProps) {
  const [data, setData] = useState<ExerciseProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showReps, setShowReps] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    cachedFetch<ExerciseProgressData>(
      `${apiUrl}/dashboard/exercise-progress?exercise=${encodeURIComponent(exercise)}&days=${days}`
    )
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, exercise, days]);

  if (loading) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="exercise-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="exercise-error">
        Error: {error}
      </div>
    );
  }

  if (!data || data.progress.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="exercise-empty">
        <h3 className="text-lg font-semibold text-foreground mb-2">{exercise} Progress</h3>
        <p className="text-muted-foreground">No data for this exercise yet.</p>
      </div>
    );
  }

  const n = data.progress.length;
  const values = showReps
    ? data.progress.map((p) => p.total_reps)
    : data.progress.map((p) => p.max_weight_kg);

  // Compute Y range from non-null values
  const nonNull = values.filter((v): v is number => v !== null);
  const yMin = nonNull.length > 0 ? Math.min(...nonNull) : 0;
  const yMax = nonNull.length > 0 ? Math.max(...nonNull) : 1;
  const yPad = (yMax - yMin) * 0.15 || 5;
  const scaleMin = Math.max(0, yMin - yPad);
  const scaleMax = yMax + yPad;

  function sx(i: number) {
    return PAD.l + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
  }
  function sy(val: number) {
    return PAD.t + plotH - ((val - scaleMin) / (scaleMax - scaleMin)) * plotH;
  }

  // Build polyline (skip nulls)
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

  // Area polygon for the first continuous segment
  const areaSegment = segments[0] || [];
  const areaPoints = areaSegment.length > 0
    ? [`${areaSegment[0].split(',')[0]},${sy(scaleMin)}`, ...areaSegment, `${areaSegment[areaSegment.length - 1].split(',')[0]},${sy(scaleMin)}`].join(' ')
    : '';

  // Trend
  const firstWeight = data.progress[0]?.max_weight_kg;
  const lastWeight = data.progress[n - 1]?.max_weight_kg;
  let trend: 'up' | 'down' | 'flat' = 'flat';
  let trendPercent = 0;
  if (firstWeight && lastWeight) {
    if (lastWeight > firstWeight) { trend = 'up'; trendPercent = ((lastWeight - firstWeight) / firstWeight) * 100; }
    else if (lastWeight < firstWeight) { trend = 'down'; trendPercent = ((firstWeight - lastWeight) / firstWeight) * 100; }
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-muted-foreground';

  const periodMax = Math.max(...data.progress.filter((p) => p.max_weight_kg !== null).map((p) => p.max_weight_kg!), 0);
  const isPR = periodMax === data.summary.all_time_max;

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
  const yStep = yRange > 50 ? 20 : yRange > 20 ? 10 : yRange > 5 ? 5 : 1;
  const yTicks: number[] = [];
  for (let v = Math.ceil(scaleMin / yStep) * yStep; v <= scaleMax; v += yStep) yTicks.push(v);

  const hoveredEntry = hovered !== null ? data.progress[hovered] : null;
  const hoveredVal = hovered !== null ? values[hovered] : null;

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="exercise-progress">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Dumbbell className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">{data.exercise} Progress</h3>
            <p className="text-sm text-muted-foreground">{data.summary.total_sessions} sessions</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex bg-secondary rounded-lg p-1">
            <button
              className={`px-2 py-1 text-xs rounded transition-colors ${!showReps ? 'bg-purple-500 text-white' : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setShowReps(false)}
            >Weight</button>
            <button
              className={`px-2 py-1 text-xs rounded transition-colors ${showReps ? 'bg-purple-500 text-white' : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setShowReps(true)}
            >Reps</button>
          </div>

          <div className="text-right">
            <div className="flex items-center gap-1">
              <TrendIcon className={`w-4 h-4 ${trendColor}`} />
              <span className="text-xl font-bold text-foreground">
                {data.summary.current_max ?? '-'} kg
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {trend !== 'flat' && (
                <span className={trendColor}>{trend === 'up' ? '+' : '-'}{trendPercent.toFixed(1)}%</span>
              )}
              {' '}All-time: {data.summary.all_time_max ?? '-'} kg
              {isPR && periodMax > 0 && <span className="ml-1 text-yellow-400">PR!</span>}
            </p>
          </div>
        </div>
      </div>

      <div className="relative h-48">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
          {/* Y grid + labels */}
          {yTicks.map((v) => (
            <g key={v}>
              <line x1={PAD.l} x2={W - PAD.r} y1={sy(v)} y2={sy(v)} stroke="#3f3f46" strokeWidth="0.5" />
              <text x={PAD.l - 4} y={sy(v) + 3} fill="#71717a" fontSize="8" textAnchor="end">{v}</text>
            </g>
          ))}

          {/* PR reference line */}
          {data.summary.all_time_max && !showReps && (
            <>
              <line x1={PAD.l} x2={W - PAD.r} y1={sy(data.summary.all_time_max)} y2={sy(data.summary.all_time_max)}
                stroke="#f59e0b" strokeWidth="0.8" strokeDasharray="4 3" />
              <text x={W - PAD.r + 4} y={sy(data.summary.all_time_max) + 3} fill="#f59e0b" fontSize="8">PR</text>
            </>
          )}

          {/* Area fill */}
          {areaPoints && (
            <>
              <defs>
                <linearGradient id="exerciseGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
                </linearGradient>
              </defs>
              <polygon points={areaPoints} fill="url(#exerciseGrad)" />
            </>
          )}

          {/* Lines */}
          {segments.map((seg, si) => (
            <polyline key={si} points={seg.join(' ')} fill="none" stroke="#8b5cf6" strokeWidth="2" strokeLinejoin="round" />
          ))}

          {/* Data points */}
          {values.map((v, i) =>
            v !== null ? (
              <circle key={i} cx={sx(i)} cy={sy(v)} r="3.5" fill="#8b5cf6"
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
              onClick={() => onDayClick?.(data.progress[i].date)}
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
            {hoveredEntry.max_weight_kg !== null && (
              <div className="text-purple-400">Max Weight: {hoveredEntry.max_weight_kg} kg</div>
            )}
            <div className="text-muted-foreground">Reps: {hoveredEntry.total_reps} &middot; Sets: {hoveredEntry.total_sets}</div>
            {hoveredEntry.max_weight_kg && (
              <div className="text-muted-foreground">Volume: {(hoveredEntry.max_weight_kg * hoveredEntry.total_reps).toLocaleString()} kg</div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
        <span>
          <Target className="w-3 h-3 inline mr-1" />
          Total Volume: {data.summary.total_volume.toLocaleString()} kg
        </span>
        <span>Click a point to view details</span>
      </div>
    </div>
  );
}
