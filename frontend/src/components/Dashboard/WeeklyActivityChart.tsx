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

interface ActivityGroup {
  group_name: string;
  entry_count: number;
  subtypes: string[];
}

interface ActivityGroupData {
  groups: ActivityGroup[];
  total_entries: number;
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

const GROUP_COLORS: Record<string, string> = {
  'Strength Training': '#3b82f6',
  'Running / Cardio': '#ef4444',
  'BJJ / Martial Arts': '#8b5cf6',
  'Yoga / Mobility': '#10b981',
  'Walking': '#f59e0b',
  'Swimming': '#06b6d4',
  'Cycling': '#84cc16',
  'HIIT': '#ec4899',
  'Recovery': '#6366f1',
  'Other': '#6b7280',
};

type ChartType = 'bar' | 'pie';
type DataView = 'types' | 'groups';

export function WeeklyActivityChart({
  apiUrl = 'http://localhost:8000',
  days = 7,
  onActivityClick,
}: WeeklyActivityChartProps) {
  const [data, setData] = useState<WeeklyActivityData | null>(null);
  const [groupData, setGroupData] = useState<ActivityGroupData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<ChartType>('bar');
  const [dataView, setDataView] = useState<DataView>('types');
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      cachedFetch<WeeklyActivityData>(`${apiUrl}/dashboard/weekly-activity?days=${days}`),
      cachedFetch<ActivityGroupData>(`${apiUrl}/dashboard/activity-groups?days=${days}`),
    ])
      .then(([activityData, activityGroupData]) => {
        if (!cancelled) {
          setData(activityData);
          setGroupData(activityGroupData);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiUrl, days]);

  // Reset hovered state when switching views
  useEffect(() => {
    setHovered(null);
  }, [dataView]);

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

  const groupItems = useMemo(() => {
    if (!groupData || !groupData.groups || groupData.groups.length === 0) return [];
    const maxCount = Math.max(...groupData.groups.map((g) => g.entry_count));
    return groupData.groups.map((g) => ({
      name: g.group_name,
      count: g.entry_count,
      subtypes: g.subtypes,
      percentage: groupData.total_entries > 0 ? (g.entry_count / groupData.total_entries) * 100 : 0,
      barWidth: maxCount > 0 ? (g.entry_count / maxCount) * 100 : 0,
      color: GROUP_COLORS[g.group_name] || GROUP_COLORS['Other'],
    }));
  }, [groupData]);

  // Build conic-gradient for doughnut (types view)
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

  // Build conic-gradient for doughnut (groups view)
  const groupConicGradient = useMemo(() => {
    if (groupItems.length === 0) return '';
    let angle = 0;
    const stops = groupItems.map((item) => {
      const start = angle;
      angle += (item.percentage / 100) * 360;
      return `${item.color} ${start}deg ${angle}deg`;
    });
    return `conic-gradient(${stops.join(', ')})`;
  }, [groupItems]);

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

  const currentItems = dataView === 'types' ? items : groupItems;
  const currentGradient = dataView === 'types' ? conicGradient : groupConicGradient;

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
              {dataView === 'types' ? (
                <>
                  {totalSessions} session{totalSessions !== 1 ? 's' : ''} | {data.activities.length} types
                </>
              ) : (
                <>
                  {groupData?.total_entries ?? 0} entr{(groupData?.total_entries ?? 0) !== 1 ? 'ies' : 'y'}
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Data view toggle: Types vs Groups */}
          <div className="flex bg-secondary rounded-lg p-1">
            <button
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${dataView === 'types' ? 'bg-orange-500 text-white' : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setDataView('types')}
              aria-label="Type breakdown view"
            >
              Types
            </button>
            <button
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${dataView === 'groups' ? 'bg-orange-500 text-white' : 'text-muted-foreground hover:text-foreground'}`}
              onClick={() => setDataView('groups')}
              aria-label="Sport groups view"
            >
              Groups
            </button>
          </div>

          {/* Chart type toggle: Bar vs Pie */}
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
      </div>

      {chartType === 'bar' ? (
        /* Horizontal bar chart */
        <div className="space-y-2 h-56 overflow-y-auto">
          {currentItems.map((item, i) => (
            <button
              key={dataView === 'types' ? (item as typeof items[number]).type : item.name}
              className="w-full flex items-center gap-3 group"
              onClick={() => {
                if (dataView === 'types') {
                  onActivityClick?.((item as typeof items[number]).type);
                }
              }}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              <span className="text-xs text-muted-foreground w-24 text-right shrink-0 group-hover:text-foreground transition-colors">
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
                    {dataView === 'types' ? (
                      <>
                        {item.count} session{item.count !== 1 ? 's' : ''} &middot; {formatDuration((item as typeof items[number]).duration)} &middot; {item.percentage.toFixed(0)}%
                      </>
                    ) : (
                      <>
                        {item.count} entr{item.count !== 1 ? 'ies' : 'y'} &middot; {item.percentage.toFixed(0)}%
                      </>
                    )}
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
                background: currentGradient,
                mask: 'radial-gradient(circle at center, transparent 55%, black 55%)',
                WebkitMask: 'radial-gradient(circle at center, transparent 55%, black 55%)',
              }}
            />
            {hovered !== null && currentItems[hovered] && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-foreground text-sm font-medium">{currentItems[hovered].name}</span>
                <span className="text-muted-foreground text-xs">{currentItems[hovered].percentage.toFixed(0)}%</span>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            {currentItems.map((item, i) => (
              <button
                key={dataView === 'types' ? (item as typeof items[number]).type : item.name}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                onClick={() => {
                  if (dataView === 'types') {
                    onActivityClick?.((item as typeof items[number]).type);
                  }
                }}
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
          <span>{dataView === 'types' ? 'Click a bar to filter' : `${groupData?.groups.length ?? 0} sport groups`}</span>
          <span>
            {dataView === 'types' && totalSessions > 0
              ? `Avg ${Math.round(data.total_duration_minutes / totalSessions)} min/session`
              : dataView === 'groups' && groupData
                ? `${groupData.total_entries} total entries`
                : ''}
          </span>
        </div>
      )}
    </div>
  );
}
