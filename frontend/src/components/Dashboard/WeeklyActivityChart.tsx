import { useEffect, useState, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import { Activity, LayoutGrid, PieChart as PieIcon } from 'lucide-react';

interface ActivitySummary {
  activity_type: string;
  count: number;
  total_duration_minutes: number;
}

interface WeeklyActivityData {
  activities: ActivitySummary[];
  total_duration_minutes: number;
}

interface WeeklyActivityChartProps {
  apiUrl?: string;
  days?: number;
  onActivityClick?: (activityType: string) => void;
}

const COLORS: Record<string, string> = {
  strength: '#3b82f6',
  cardio: '#ef4444',
  bjj: '#8b5cf6',
  yoga: '#10b981',
  walk: '#f59e0b',
  recovery: '#6366f1',
  stretching: '#14b8a6',
  swimming: '#06b6d4',
  cycling: '#84cc16',
  running: '#f97316',
  hiit: '#ec4899',
  other: '#6b7280',
};

interface ChartDataPoint {
  name: string;
  duration: number;
  count: number;
  type: string;
  percentage: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: ChartDataPoint;
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  const hours = Math.floor(data.duration / 60);
  const minutes = data.duration % 60;
  const timeStr = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm shadow-xl">
      <div className="font-medium text-white mb-2 flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-sm"
          style={{ backgroundColor: COLORS[data.type] || COLORS.other }}
        />
        {data.name}
      </div>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-zinc-400">Duration:</span>
          <span className="text-white font-medium">{timeStr}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-zinc-400">Sessions:</span>
          <span className="text-white">{data.count}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-zinc-400">Share:</span>
          <span className="text-white">{data.percentage.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

type ChartType = 'bar' | 'pie';

export function WeeklyActivityChart({
  apiUrl = 'http://localhost:8000',
  days = 7,
  onActivityClick,
}: WeeklyActivityChartProps) {
  const [data, setData] = useState<WeeklyActivityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<ChartType>('bar');

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(`${apiUrl}/dashboard/weekly-activity?days=${days}`);
        if (!response.ok) throw new Error('Failed to fetch activity data');
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

  const chartData: ChartDataPoint[] = useMemo(() => {
    if (!data) return [];
    return data.activities.map((a) => ({
      name: a.activity_type.charAt(0).toUpperCase() + a.activity_type.slice(1),
      duration: a.total_duration_minutes,
      count: a.count,
      type: a.activity_type,
      percentage: (a.total_duration_minutes / data.total_duration_minutes) * 100,
    }));
  }, [data]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleBarClick = (data: any) => {
    if (data?.type) {
      onActivityClick?.(data.type);
    }
  };

  const handlePieClick = (index: number) => {
    if (chartData[index]) {
      onActivityClick?.(chartData[index].type);
    }
  };

  if (loading) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4 h-64 animate-pulse" data-testid="activity-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="activity-error">
        Error: {error}
      </div>
    );
  }

  if (!data || data.activities.length === 0) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4" data-testid="activity-empty">
        <h3 className="text-lg font-semibold text-white mb-2">Weekly Activity</h3>
        <p className="text-zinc-400">No activities recorded yet.</p>
      </div>
    );
  }

  // Format total time
  const totalHours = Math.floor(data.total_duration_minutes / 60);
  const totalMinutes = data.total_duration_minutes % 60;
  const totalTimeStr = totalHours > 0 ? `${totalHours}h ${totalMinutes}m` : `${totalMinutes}m`;

  return (
    <div className="bg-zinc-800 rounded-lg p-4" data-testid="weekly-activity-chart">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-orange-500/20 rounded-lg">
            <Activity className="w-5 h-5 text-orange-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Activity Breakdown</h3>
            <p className="text-sm text-zinc-400">
              {data.activities.length} types | {totalTimeStr} total
            </p>
          </div>
        </div>

        {/* Chart type toggle */}
        <div className="flex bg-zinc-700 rounded-lg p-1">
          <button
            className={`p-2 rounded transition-colors ${
              chartType === 'bar' ? 'bg-orange-500 text-white' : 'text-zinc-400 hover:text-white'
            }`}
            onClick={() => setChartType('bar')}
            aria-label="Bar chart"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            className={`p-2 rounded transition-colors ${
              chartType === 'pie' ? 'bg-orange-500 text-white' : 'text-zinc-400 hover:text-white'
            }`}
            onClick={() => setChartType('pie')}
            aria-label="Pie chart"
          >
            <PieIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar' ? (
            <BarChart data={chartData} layout="vertical">
              <XAxis type="number" stroke="#71717a" fontSize={12} tickLine={false} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#71717a"
                fontSize={12}
                width={80}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar
                dataKey="duration"
                radius={[0, 4, 4, 0]}
                onClick={handleBarClick}
                cursor="pointer"
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[entry.type] || COLORS.other}
                  />
                ))}
              </Bar>
            </BarChart>
          ) : (
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                dataKey="duration"
                nameKey="name"
                onClick={(_, index) => handlePieClick(index)}
                cursor="pointer"
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[entry.type] || COLORS.other}
                    stroke="#27272a"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Legend for pie chart */}
      {chartType === 'pie' && (
        <div className="flex flex-wrap justify-center gap-3 mt-3 pt-3 border-t border-zinc-700">
          {chartData.map((entry) => (
            <button
              key={entry.type}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
              onClick={() => onActivityClick?.(entry.type)}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: COLORS[entry.type] || COLORS.other }}
              />
              {entry.name}
            </button>
          ))}
        </div>
      )}

      {/* Stats footer for bar chart */}
      {chartType === 'bar' && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-700 text-xs text-zinc-400">
          <span>Click a bar to filter</span>
          <span>
            Avg per session:{' '}
            {Math.round(
              data.total_duration_minutes / data.activities.reduce((sum, a) => sum + a.count, 0)
            )}{' '}
            min
          </span>
        </div>
      )}
    </div>
  );
}
