import { useEffect, useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Activity, Eye, EyeOff } from 'lucide-react';

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

interface ChartDataPoint {
  date: string;
  fullDate: string;
  rawDate: string;
  sleep: number | null;
  energy: number | null;
  mood: number | null;
  stress: number | null;
}

interface MetricToggle {
  key: keyof ChartDataPoint;
  label: string;
  color: string;
  visible: boolean;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    color: string;
    name: string;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm shadow-xl">
      <div className="font-medium text-white mb-2">{label}</div>
      <div className="space-y-1">
        {payload.map((entry) => (
          <div key={entry.dataKey} className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-zinc-300">{entry.name}:</span>
            </span>
            <span className="font-medium text-white">
              {entry.dataKey === 'sleep'
                ? `${entry.value?.toFixed(1)} hrs`
                : `${entry.value}/10`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const METRICS: Omit<MetricToggle, 'visible'>[] = [
  { key: 'energy', label: 'Energy', color: '#22c55e' },
  { key: 'mood', label: 'Mood', color: '#3b82f6' },
  { key: 'stress', label: 'Stress', color: '#ef4444' },
  { key: 'sleep', label: 'Sleep', color: '#8b5cf6' },
];

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

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(`${apiUrl}/dashboard/metrics-trends?days=${days}`);
        if (!response.ok) throw new Error('Failed to fetch metrics');
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
    return data.metrics.map((m) => ({
      date: new Date(m.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      fullDate: new Date(m.date).toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      }),
      rawDate: m.date,
      sleep: m.sleep_hours,
      energy: m.energy,
      mood: m.mood,
      stress: m.stress,
    }));
  }, [data]);

  // Calculate averages for visible metrics
  const averages = useMemo(() => {
    if (!data || data.metrics.length === 0) return {};
    const result: Record<string, number> = {};

    for (const metric of METRICS) {
      const values = data.metrics
        .map((m) => m[metric.key as keyof MetricEntry] as number | null)
        .filter((v): v is number => v !== null);

      if (values.length > 0) {
        result[metric.key as string] = values.reduce((a, b) => a + b, 0) / values.length;
      }
    }

    return result;
  }, [data]);

  const toggleMetric = (key: string) => {
    setVisibleMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleChartClick = (chartData: any) => {
    if (chartData?.activePayload?.[0]?.payload?.rawDate) {
      onDayClick?.(chartData.activePayload[0].payload.rawDate);
    }
  };

  if (loading) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4 h-64 animate-pulse" data-testid="metrics-loading" />
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
      <div className="bg-zinc-800 rounded-lg p-4" data-testid="metrics-empty">
        <h3 className="text-lg font-semibold text-white mb-2">Daily Metrics</h3>
        <p className="text-zinc-400">No metrics recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-800 rounded-lg p-4" data-testid="metrics-trends">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Activity className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Daily Metrics</h3>
            <p className="text-sm text-zinc-400">{chartData.length} days</p>
          </div>
        </div>

        {/* Metric toggles */}
        <div className="flex flex-wrap gap-2">
          {METRICS.map((metric) => (
            <button
              key={metric.key as string}
              onClick={() => toggleMetric(metric.key as string)}
              className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded-lg transition-colors ${
                visibleMetrics.has(metric.key as string)
                  ? 'bg-zinc-700 text-white'
                  : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
              }`}
              style={{
                borderLeft: visibleMetrics.has(metric.key as string)
                  ? `3px solid ${metric.color}`
                  : '3px solid transparent',
              }}
            >
              {visibleMetrics.has(metric.key as string) ? (
                <Eye className="w-3 h-3" />
              ) : (
                <EyeOff className="w-3 h-3" />
              )}
              {metric.label}
            </button>
          ))}
        </div>
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} onClick={handleChartClick}>
            <XAxis dataKey="date" stroke="#71717a" fontSize={12} tickLine={false} />
            <YAxis stroke="#71717a" fontSize={12} domain={[0, 10]} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '10px' }}
              formatter={(value) => <span className="text-xs text-zinc-400">{value}</span>}
            />

            {METRICS.map((metric) =>
              visibleMetrics.has(metric.key as string) ? (
                <Line
                  key={metric.key as string}
                  type="monotone"
                  dataKey={metric.key}
                  stroke={metric.color}
                  strokeWidth={2}
                  dot={{ fill: metric.color, r: 3, strokeWidth: 0 }}
                  activeDot={{
                    fill: metric.color,
                    r: 5,
                    strokeWidth: 2,
                    stroke: '#fff',
                    cursor: 'pointer',
                  }}
                  name={metric.label}
                  connectNulls
                />
              ) : null
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Averages footer */}
      <div className="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-zinc-700 text-xs">
        <span className="text-zinc-500">Averages:</span>
        {METRICS.filter((m) => visibleMetrics.has(m.key as string)).map((metric) => (
          <span
            key={metric.key as string}
            className="flex items-center gap-1"
            style={{ color: metric.color }}
          >
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: metric.color }} />
            {metric.label}:{' '}
            {metric.key === 'sleep'
              ? `${(averages[metric.key as string] || 0).toFixed(1)} hrs`
              : `${(averages[metric.key as string] || 0).toFixed(1)}/10`}
          </span>
        ))}
      </div>
    </div>
  );
}
