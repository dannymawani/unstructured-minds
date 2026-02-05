import { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Moon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

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

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: {
      date: string;
      sleep: number;
      quality: number | null;
      fullDate: string;
    };
  }>;
  label?: string;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
      <div className="font-medium text-white mb-1">{data.fullDate}</div>
      <div className="flex items-center gap-2 text-blue-400">
        <Moon className="w-3 h-3" />
        <span>{data.sleep.toFixed(1)} hours</span>
      </div>
      {data.quality !== null && (
        <div className="text-zinc-400 text-xs mt-1">Quality: {data.quality}/10</div>
      )}
    </div>
  );
}

export function SleepTrends({
  apiUrl = 'http://localhost:8000',
  days = 30,
  onDayClick,
}: SleepTrendsProps) {
  const [data, setData] = useState<SleepTrendsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(`${apiUrl}/dashboard/metrics-trends?days=${days}`);
        if (!response.ok) throw new Error('Failed to fetch sleep data');
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

  if (loading) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4 h-64 animate-pulse" data-testid="sleep-loading" />
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
      <div className="bg-zinc-800 rounded-lg p-4" data-testid="sleep-empty">
        <h3 className="text-lg font-semibold text-white mb-2">Sleep Trends</h3>
        <p className="text-zinc-400">No sleep data recorded yet.</p>
      </div>
    );
  }

  // Filter to only entries with sleep data
  const sleepData = data.metrics.filter((m) => m.sleep_hours !== null);

  if (sleepData.length === 0) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4" data-testid="sleep-empty">
        <h3 className="text-lg font-semibold text-white mb-2">Sleep Trends</h3>
        <p className="text-zinc-400">No sleep data recorded yet.</p>
      </div>
    );
  }

  const chartData = sleepData.map((m) => ({
    date: new Date(m.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    fullDate: new Date(m.date).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    }),
    sleep: m.sleep_hours || 0,
    quality: m.sleep_quality,
    rawDate: m.date,
  }));

  // Calculate stats
  const avgSleep = sleepData.reduce((sum, m) => sum + (m.sleep_hours || 0), 0) / sleepData.length;
  const recentAvg =
    sleepData.slice(-7).reduce((sum, m) => sum + (m.sleep_hours || 0), 0) /
    Math.min(7, sleepData.length);
  const previousAvg =
    sleepData.slice(-14, -7).reduce((sum, m) => sum + (m.sleep_hours || 0), 0) /
    Math.min(7, sleepData.slice(-14, -7).length || 1);

  let trend: 'up' | 'down' | 'flat' = 'flat';
  if (recentAvg > previousAvg + 0.25) trend = 'up';
  else if (recentAvg < previousAvg - 0.25) trend = 'down';

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor =
    trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-zinc-400';

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleChartClick = (e: any) => {
    if (e?.activePayload?.[0]?.payload?.rawDate) {
      onDayClick?.(e.activePayload[0].payload.rawDate);
    }
  };

  return (
    <div className="bg-zinc-800 rounded-lg p-4" data-testid="sleep-trends">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2">
          <Moon className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Sleep Trends</h3>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1">
            <TrendIcon className={`w-4 h-4 ${trendColor}`} />
            <span className="text-xl font-bold text-white">{avgSleep.toFixed(1)} hrs</span>
          </div>
          <p className="text-xs text-zinc-400">avg / night</p>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            onClick={handleChartClick}
          >
            <defs>
              <linearGradient id="sleepGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="date" stroke="#71717a" fontSize={12} tickLine={false} />
            <YAxis
              stroke="#71717a"
              fontSize={12}
              domain={[0, 12]}
              ticks={[0, 4, 8, 12]}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* Reference line at 8 hours (recommended sleep) */}
            <ReferenceLine
              y={8}
              stroke="#22c55e"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{
                value: '8h goal',
                position: 'right',
                fill: '#22c55e',
                fontSize: 10,
              }}
            />
            <Area
              type="monotone"
              dataKey="sleep"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#sleepGradient)"
              dot={{ fill: '#3b82f6', r: 3, strokeWidth: 0 }}
              activeDot={{ fill: '#60a5fa', r: 5, strokeWidth: 2, stroke: '#fff' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Sleep quality legend */}
      <div className="flex items-center justify-between mt-3 text-xs text-zinc-500">
        <span>Last {days} days</span>
        <span>
          7-day avg: {recentAvg.toFixed(1)} hrs {trend === 'up' ? '(improving)' : trend === 'down' ? '(declining)' : ''}
        </span>
      </div>
    </div>
  );
}
