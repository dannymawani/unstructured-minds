import { useEffect, useState, useMemo } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
  Cell,
  ReferenceLine,
} from 'recharts';
import { Brain, ChevronDown } from 'lucide-react';

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

interface ChartDataPoint {
  date: string;
  sleep: number;
  energy: number;
  mood: number;
  stress: number;
  activity: number;
  size: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: ChartDataPoint;
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
      <div className="font-medium text-white mb-1">
        {new Date(data.date).toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
        })}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <span className="text-zinc-400">Sleep:</span>
        <span className="text-white">{data.sleep.toFixed(1)} hrs</span>
        <span className="text-zinc-400">Energy:</span>
        <span className="text-white">{data.energy}/10</span>
        <span className="text-zinc-400">Mood:</span>
        <span className="text-white">{data.mood}/10</span>
        <span className="text-zinc-400">Stress:</span>
        <span className="text-white">{data.stress}/10</span>
        {data.activity > 0 && (
          <>
            <span className="text-zinc-400">Activity:</span>
            <span className="text-white">{data.activity} min</span>
          </>
        )}
      </div>
    </div>
  );
}

function getCorrelationColor(correlation: number | null): string {
  if (correlation === null) return 'text-zinc-500';
  const abs = Math.abs(correlation);
  if (abs < 0.3) return 'text-zinc-400';
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

export function MoodCorrelation({
  apiUrl = 'http://localhost:8000',
  days = 30,
}: MoodCorrelationProps) {
  const [data, setData] = useState<CorrelationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPair, setSelectedPair] = useState<MetricPair>('sleep_mood');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(`${apiUrl}/dashboard/correlation?days=${days}`);
        if (!response.ok) throw new Error('Failed to fetch correlation data');
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [apiUrl, days]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.entries
      .filter(
        (e) =>
          e.sleep_hours !== null &&
          e.energy !== null &&
          e.mood !== null &&
          e.stress !== null
      )
      .map((e) => ({
        date: e.date,
        sleep: e.sleep_hours || 0,
        energy: e.energy || 0,
        mood: e.mood || 0,
        stress: e.stress || 0,
        activity: e.activity_minutes || 0,
        size: 100,
      }));
  }, [data]);

  const currentPair = METRIC_PAIRS.find((p) => p.value === selectedPair)!;
  const correlation = data?.correlations[selectedPair] ?? null;

  if (loading) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4 h-72 animate-pulse" data-testid="correlation-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="correlation-error">
        Error: {error}
      </div>
    );
  }

  if (!data || chartData.length < 3) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4" data-testid="correlation-empty">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Mood Correlations</h3>
        </div>
        <p className="text-zinc-400">Need at least 3 days of data to show correlations.</p>
      </div>
    );
  }

  // Calculate domain for X axis based on selected metric
  const xValues = chartData.map((d) => d[currentPair.xKey as keyof ChartDataPoint] as number);
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const xPadding = (xMax - xMin) * 0.1 || 1;

  return (
    <div className="bg-zinc-800 rounded-lg p-4" data-testid="mood-correlation">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Mood Correlations</h3>
        </div>

        {/* Metric selector dropdown */}
        <div className="relative">
          <button
            className="flex items-center gap-2 bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-3 py-2 rounded-lg transition-colors"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            {currentPair.label}
            <ChevronDown className={`w-4 h-4 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </button>
          {isDropdownOpen && (
            <div className="absolute right-0 mt-1 w-48 bg-zinc-700 rounded-lg shadow-lg z-10 overflow-hidden">
              {METRIC_PAIRS.map((pair) => (
                <button
                  key={pair.value}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-zinc-600 transition-colors ${
                    pair.value === selectedPair ? 'bg-zinc-600 text-white' : 'text-zinc-300'
                  }`}
                  onClick={() => {
                    setSelectedPair(pair.value);
                    setIsDropdownOpen(false);
                  }}
                >
                  {pair.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Correlation indicator */}
      <div className="flex items-center gap-3 mb-3 text-sm">
        <span className="text-zinc-400">Correlation:</span>
        <span className={`font-medium ${getCorrelationColor(correlation)}`}>
          {correlation !== null ? correlation.toFixed(2) : 'N/A'}
        </span>
        <span className={`text-xs ${getCorrelationColor(correlation)}`}>
          ({getCorrelationLabel(correlation)})
        </span>
      </div>

      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
            <XAxis
              type="number"
              dataKey={currentPair.xKey}
              name={currentPair.xLabel}
              stroke="#71717a"
              fontSize={12}
              domain={[Math.max(0, xMin - xPadding), xMax + xPadding]}
              tickLine={false}
              label={{ value: currentPair.xLabel, position: 'bottom', fill: '#71717a', fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey={currentPair.yKey}
              name={currentPair.yLabel}
              stroke="#71717a"
              fontSize={12}
              domain={[0, 10]}
              tickLine={false}
              axisLine={false}
              label={{ value: currentPair.yLabel, angle: -90, position: 'insideLeft', fill: '#71717a', fontSize: 11 }}
            />
            <ZAxis type="number" dataKey="size" range={[50, 200]} />
            <Tooltip content={<CustomTooltip />} />
            {/* Average lines */}
            <ReferenceLine
              y={chartData.reduce((sum, d) => sum + (d[currentPair.yKey as keyof ChartDataPoint] as number), 0) / chartData.length}
              stroke="#8b5cf6"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
            />
            <Scatter data={chartData} fill="#8b5cf6">
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.mood >= 7 ? '#22c55e' : entry.mood >= 5 ? '#f59e0b' : '#ef4444'}
                  fillOpacity={0.7}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between mt-2 text-xs text-zinc-500">
        <span>{chartData.length} data points</span>
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
