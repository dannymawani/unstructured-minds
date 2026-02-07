import { useEffect, useState, useMemo } from 'react';
import { Activity, LayoutGrid, PieChart as PieIcon } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

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
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    cachedFetch<WeeklyActivityData>(`${apiUrl}/dashboard/weekly-activity?days=${days}`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, days]);

  const items = useMemo(() => {
    if (!data) return [];
    const maxDuration = Math.max(...data.activities.map((a) => a.total_duration_minutes));
    return data.activities.map((a) => ({
      name: a.activity_type.charAt(0).toUpperCase() + a.activity_type.slice(1),
      duration: a.total_duration_minutes,
      count: a.count,
      type: a.activity_type,
      percentage: (a.total_duration_minutes / data.total_duration_minutes) * 100,
      barWidth: (a.total_duration_minutes / maxDuration) * 100,
      color: COLORS[a.activity_type] || COLORS.other,
    }));
  }, [data]);

  // Build conic-gradient for doughnut
  const conicGradient = useMemo(() => {
    if (items.length === 0) return '';
    let angle = 0;
    const stops = items.map((item) => {
      const start = angle;
      angle += (item.percentage / 100) * 360;
      return `${item.color} ${start}deg ${angle}deg`;
    });
    return `conic-gradient(${stops.join(', ')})`;
  }, [items]);

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

  const totalHours = Math.floor(data.total_duration_minutes / 60);
  const totalMinutes = data.total_duration_minutes % 60;
  const totalTimeStr = totalHours > 0 ? `${totalHours}h ${totalMinutes}m` : `${totalMinutes}m`;

  const formatDuration = (mins: number) => {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

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

        <div className="flex bg-zinc-700 rounded-lg p-1">
          <button
            className={`p-2 rounded transition-colors ${chartType === 'bar' ? 'bg-orange-500 text-white' : 'text-zinc-400 hover:text-white'}`}
            onClick={() => setChartType('bar')}
            aria-label="Bar chart"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            className={`p-2 rounded transition-colors ${chartType === 'pie' ? 'bg-orange-500 text-white' : 'text-zinc-400 hover:text-white'}`}
            onClick={() => setChartType('pie')}
            aria-label="Pie chart"
          >
            <PieIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {chartType === 'bar' ? (
        /* Horizontal bar chart */
        <div className="space-y-2 h-56 overflow-y-auto">
          {items.map((item, i) => (
            <button
              key={item.type}
              className="w-full flex items-center gap-3 group"
              onClick={() => onActivityClick?.(item.type)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              <span className="text-xs text-zinc-400 w-20 text-right shrink-0 group-hover:text-white transition-colors">
                {item.name}
              </span>
              <div className="flex-1 h-5 bg-zinc-700/50 rounded overflow-hidden relative">
                <div
                  className="h-full rounded transition-all duration-300"
                  style={{
                    width: `${item.barWidth}%`,
                    backgroundColor: item.color,
                    opacity: hovered === null || hovered === i ? 1 : 0.4,
                  }}
                />
                {hovered === i && (
                  <span className="absolute inset-0 flex items-center justify-center text-white text-xs font-medium">
                    {formatDuration(item.duration)} &middot; {item.count} sessions &middot; {item.percentage.toFixed(0)}%
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      ) : (
        /* Doughnut chart */
        <div className="flex items-center justify-center h-56 gap-6">
          <div className="relative">
            <div
              className="w-40 h-40 rounded-full"
              style={{
                background: conicGradient,
                mask: 'radial-gradient(circle at center, transparent 55%, black 55%)',
                WebkitMask: 'radial-gradient(circle at center, transparent 55%, black 55%)',
              }}
            />
            {hovered !== null && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-white text-sm font-medium">{items[hovered].name}</span>
                <span className="text-zinc-400 text-xs">{items[hovered].percentage.toFixed(0)}%</span>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            {items.map((item, i) => (
              <button
                key={item.type}
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
                onClick={() => onActivityClick?.(item.type)}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
              >
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                {item.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {chartType === 'bar' && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-700 text-xs text-zinc-400">
          <span>Click a bar to filter</span>
          <span>
            Avg per session:{' '}
            {Math.round(data.total_duration_minutes / data.activities.reduce((sum, a) => sum + a.count, 0))} min
          </span>
        </div>
      )}
    </div>
  );
}
