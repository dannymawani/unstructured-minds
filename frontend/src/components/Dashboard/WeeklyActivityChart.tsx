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

  const totalSessions = useMemo(() => {
    if (!data) return 0;
    return data.activities.reduce((sum, a) => sum + a.count, 0);
  }, [data]);

  const items = useMemo(() => {
    if (!data) return [];
    const maxCount = Math.max(...data.activities.map((a) => a.count));
    return data.activities.map((a) => ({
      name: a.activity_type.charAt(0).toUpperCase() + a.activity_type.slice(1),
      duration: a.total_duration_minutes,
      count: a.count,
      type: a.activity_type,
      percentage: totalSessions > 0 ? (a.count / totalSessions) * 100 : 0,
      barWidth: maxCount > 0 ? (a.count / maxCount) * 100 : 0,
      color: COLORS[a.activity_type] || COLORS.other,
    }));
  }, [data, totalSessions]);

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
      <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="activity-loading" />
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
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="activity-empty">
        <h3 className="text-lg font-semibold text-foreground mb-2">Weekly Activity</h3>
        <p className="text-muted-foreground">No activities recorded yet.</p>
      </div>
    );
  }

  const formatDuration = (mins: number) => {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="weekly-activity-chart">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-orange-500/20 rounded-lg">
            <Activity className="w-5 h-5 text-orange-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Activity Breakdown</h3>
            <p className="text-sm text-muted-foreground">
              {totalSessions} session{totalSessions !== 1 ? 's' : ''} | {data.activities.length} types
            </p>
          </div>
        </div>

        <div className="flex bg-secondary rounded-lg p-1">
          <button
            className={`p-2 rounded transition-colors ${chartType === 'bar' ? 'bg-orange-500 text-white' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setChartType('bar')}
            aria-label="Bar chart"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            className={`p-2 rounded transition-colors ${chartType === 'pie' ? 'bg-orange-500 text-white' : 'text-muted-foreground hover:text-foreground'}`}
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
              <span className="text-xs text-muted-foreground w-20 text-right shrink-0 group-hover:text-foreground transition-colors">
                {item.name}
              </span>
              <div className="flex-1 h-5 bg-secondary/50 rounded overflow-hidden relative">
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
                    {item.count} session{item.count !== 1 ? 's' : ''} &middot; {formatDuration(item.duration)} &middot; {item.percentage.toFixed(0)}%
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
                <span className="text-foreground text-sm font-medium">{items[hovered].name}</span>
                <span className="text-muted-foreground text-xs">{items[hovered].percentage.toFixed(0)}%</span>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            {items.map((item, i) => (
              <button
                key={item.type}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
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
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
          <span>Click a bar to filter</span>
          <span>
            {totalSessions > 0 ? `Avg ${Math.round(data.total_duration_minutes / totalSessions)} min/session` : ''}
          </span>
        </div>
      )}
    </div>
  );
}
