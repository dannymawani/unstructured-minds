import { useEffect, useState, useMemo } from 'react';
import { Brain, ChevronDown } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface CorrelationEntry {
  date: string;
  sleep_hours: number | null;
  energy: number | null;
  mood: number | null;
  stress: number | null;
  activity_minutes: number | null;
}

interface CorrelationData {
  entries: CorrelationEntry[];
  correlations: {
    sleep_mood: number | null;
    sleep_energy: number | null;
    activity_mood: number | null;
    activity_energy: number | null;
    stress_mood: number | null;
  };
}

interface MoodCorrelationProps {
  apiUrl?: string;
  days?: number;
}

type MetricPair = 'sleep_mood' | 'sleep_energy' | 'activity_mood' | 'activity_energy' | 'stress_mood';

const METRIC_PAIRS: { value: MetricPair; label: string; xKey: string; yKey: string; xLabel: string; yLabel: string }[] = [
  { value: 'sleep_mood', label: 'Sleep vs Mood', xKey: 'sleep', yKey: 'mood', xLabel: 'Sleep (hrs)', yLabel: 'Mood' },
  { value: 'sleep_energy', label: 'Sleep vs Energy', xKey: 'sleep', yKey: 'energy', xLabel: 'Sleep (hrs)', yLabel: 'Energy' },
  { value: 'activity_mood', label: 'Activity vs Mood', xKey: 'activity', yKey: 'mood', xLabel: 'Activity (min)', yLabel: 'Mood' },
  { value: 'activity_energy', label: 'Activity vs Energy', xKey: 'activity', yKey: 'energy', xLabel: 'Activity (min)', yLabel: 'Energy' },
  { value: 'stress_mood', label: 'Stress vs Mood', xKey: 'stress', yKey: 'mood', xLabel: 'Stress', yLabel: 'Mood' },
];

interface DataPoint {
  date: string;
  sleep: number;
  energy: number;
  mood: number;
  stress: number;
  activity: number;
}

function getCorrelationColor(correlation: number | null): string {
  if (correlation === null) return 'text-muted-foreground';
  const abs = Math.abs(correlation);
  if (abs < 0.3) return 'text-muted-foreground';
  if (abs < 0.6) return correlation > 0 ? 'text-yellow-400' : 'text-orange-400';
  return correlation > 0 ? 'text-green-400' : 'text-red-400';
}

function getCorrelationLabel(correlation: number | null): string {
  if (correlation === null) return 'No data';
  const abs = Math.abs(correlation);
  const direction = correlation > 0 ? 'positive' : 'negative';
  if (abs < 0.3) return `Weak ${direction}`;
  if (abs < 0.6) return `Moderate ${direction}`;
  return `Strong ${direction}`;
}

// SVG layout
const W = 400;
const H = 180;
const PAD = { t: 8, r: 8, b: 28, l: 36 };
const plotW = W - PAD.l - PAD.r;
const plotH = H - PAD.t - PAD.b;

export function MoodCorrelation({
  apiUrl = 'http://localhost:8000',
  days = 30,
}: MoodCorrelationProps) {
  const [data, setData] = useState<CorrelationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPair, setSelectedPair] = useState<MetricPair>('sleep_mood');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    cachedFetch<CorrelationData>(`${apiUrl}/dashboard/correlation?days=${days}`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, days]);

  const chartDataPoints: DataPoint[] = useMemo(() => {
    if (!data) return [];
    const pair = METRIC_PAIRS.find((p) => p.value === selectedPair)!;
    // Map pair keys back to entry field names
    const fieldMap: Record<string, keyof CorrelationEntry> = {
      sleep: 'sleep_hours',
      energy: 'energy',
      mood: 'mood',
      stress: 'stress',
      activity: 'activity_minutes',
    };
    const xField = fieldMap[pair.xKey];
    const yField = fieldMap[pair.yKey];
    return data.entries
      .filter((e) => e[xField] !== null && e[yField] !== null)
      .map((e) => ({
        date: e.date,
        sleep: e.sleep_hours || 0,
        energy: e.energy || 0,
        mood: e.mood || 0,
        stress: e.stress || 0,
        activity: e.activity_minutes || 0,
      }));
  }, [data, selectedPair]);

  const currentPair = METRIC_PAIRS.find((p) => p.value === selectedPair)!;
  const correlation = data?.correlations[selectedPair] ?? null;

  if (loading) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4 h-72 animate-pulse" data-testid="correlation-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="correlation-error">
        Error: {error}
      </div>
    );
  }

  if (!data || chartDataPoints.length < 3) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="correlation-empty">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-foreground">Mood Correlations</h3>
        </div>
        <p className="text-muted-foreground">Need at least 3 days of data to show correlations.</p>
      </div>
    );
  }

  const xValues = chartDataPoints.map((d) => d[currentPair.xKey as keyof DataPoint] as number);
  const yValues = chartDataPoints.map((d) => d[currentPair.yKey as keyof DataPoint] as number);
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const xPadding = (xMax - xMin) * 0.1 || 1;
  const scaleXMin = Math.max(0, xMin - xPadding);
  const scaleXMax = xMax + xPadding;
  const yMin = 0;
  const yMax = 10;
  const yAvg = yValues.reduce((a, b) => a + b, 0) / yValues.length;

  function scaleX(val: number) {
    return PAD.l + ((val - scaleXMin) / (scaleXMax - scaleXMin)) * plotW;
  }
  function scaleY(val: number) {
    return PAD.t + plotH - ((val - yMin) / (yMax - yMin)) * plotH;
  }

  function dotColor(mood: number) {
    if (mood >= 7) return 'rgba(34, 197, 94, 0.7)';
    if (mood >= 5) return 'rgba(245, 158, 11, 0.7)';
    return 'rgba(239, 68, 68, 0.7)';
  }

  const hoveredPoint = hovered !== null ? chartDataPoints[hovered] : null;

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="mood-correlation">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-foreground">Mood Correlations</h3>
        </div>

        <div className="relative">
          <button
            className="flex items-center gap-2 bg-secondary hover:bg-secondary text-foreground text-sm px-3 py-2 rounded-lg transition-colors"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            {currentPair.label}
            <ChevronDown className={`w-4 h-4 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </button>
          {isDropdownOpen && (
            <div className="absolute right-0 mt-1 w-48 bg-secondary rounded-lg shadow-lg z-10 overflow-hidden">
              {METRIC_PAIRS.map((pair) => (
                <button
                  key={pair.value}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-secondary transition-colors ${
                    pair.value === selectedPair ? 'bg-secondary text-foreground' : 'text-muted-foreground'
                  }`}
                  onClick={() => { setSelectedPair(pair.value); setIsDropdownOpen(false); }}
                >
                  {pair.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3 text-sm">
        <span className="text-muted-foreground">Correlation:</span>
        <span className={`font-medium ${getCorrelationColor(correlation)}`}>
          {correlation !== null ? correlation.toFixed(2) : 'N/A'}
        </span>
        <span className={`text-xs ${getCorrelationColor(correlation)}`}>
          ({getCorrelationLabel(correlation)})
        </span>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ aspectRatio: `${W}/${H}` }}>
          {/* Y grid */}
          {[0, 2, 4, 6, 8, 10].map((v) => (
            <line key={v} x1={PAD.l} x2={W - PAD.r} y1={scaleY(v)} y2={scaleY(v)} stroke="#3f3f46" strokeWidth="0.5" />
          ))}
          {[0, 5, 10].map((v) => (
            <text key={`yl-${v}`} x={PAD.l - 4} y={scaleY(v) + 3} fill="#71717a" fontSize="8" textAnchor="end">{v}</text>
          ))}

          {/* Y-axis label */}
          <text x="8" y={PAD.t + plotH / 2} fill="#71717a" fontSize="8" textAnchor="middle"
            transform={`rotate(-90, 8, ${PAD.t + plotH / 2})`}>{currentPair.yLabel}</text>
          {/* X-axis label */}
          <text x={PAD.l + plotW / 2} y={H - 2} fill="#71717a" fontSize="8" textAnchor="middle">{currentPair.xLabel}</text>

          {/* Y average reference line */}
          <line x1={PAD.l} x2={W - PAD.r} y1={scaleY(yAvg)} y2={scaleY(yAvg)}
            stroke="#8b5cf6" strokeWidth="0.8" strokeDasharray="4 3" />

          {/* Scatter dots */}
          {chartDataPoints.map((d, i) => {
            const cx = scaleX(d[currentPair.xKey as keyof DataPoint] as number);
            const cy = scaleY(d[currentPair.yKey as keyof DataPoint] as number);
            return (
              <g key={i}>
                <circle cx={cx} cy={cy} r={hovered === i ? 7 : 5} fill={dotColor(d.mood)}
                  stroke={hovered === i ? '#fff' : 'none'} strokeWidth="2"
                  style={{ cursor: 'pointer', transition: 'r 0.15s' }}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                />
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {hoveredPoint && hovered !== null && (
          <div
            className="absolute pointer-events-none bg-popover text-popover-foreground rounded-md shadow-lg border border-border px-3 py-2 text-xs z-10"
            style={{
              left: `${(scaleX(hoveredPoint[currentPair.xKey as keyof DataPoint] as number) / W) * 100}%`,
              top: `${(scaleY(hoveredPoint[currentPair.yKey as keyof DataPoint] as number) / H) * 100}%`,
              transform: 'translate(-50%, -120%)',
            }}
          >
            <div className="font-medium text-foreground mb-1">
              {new Date(hoveredPoint.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </div>
            <div className="text-muted-foreground">Sleep: {hoveredPoint.sleep.toFixed(1)} hrs</div>
            <div className="text-muted-foreground">Energy: {hoveredPoint.energy}/10</div>
            <div className="text-muted-foreground">Mood: {hoveredPoint.mood}/10</div>
            <div className="text-muted-foreground">Stress: {hoveredPoint.stress}/10</div>
            {hoveredPoint.activity > 0 && <div className="text-muted-foreground">Activity: {hoveredPoint.activity} min</div>}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
        <span>{chartDataPoints.length} data points</span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" /> Good mood
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-yellow-500" /> Neutral
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Low mood
          </span>
        </div>
      </div>
    </div>
  );
}
