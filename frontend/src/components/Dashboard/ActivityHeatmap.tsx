import { useEffect, useState, useMemo } from 'react';
import { Grid3x3 } from 'lucide-react';

interface HeatmapDay {
  date: string;
  count: number;
  duration_minutes: number;
}

interface HeatmapData {
  days: HeatmapDay[];
  year: number;
  max_count: number;
  max_duration: number;
}

interface ActivityHeatmapProps {
  apiUrl?: string;
  year?: number;
  onDayClick?: (date: string, data: HeatmapDay | null) => void;
}

// Color scale based on activity intensity (using duration)
const INTENSITY_COLORS = [
  'bg-muted',                              // 0 - no activity
  'bg-green-900/60 dark:bg-green-900/60', // 1 - light
  'bg-green-700/70 dark:bg-green-700/70', // 2 - moderate
  'bg-green-500/80 dark:bg-green-500/80', // 3 - active
  'bg-green-400 dark:bg-green-400',       // 4 - very active
];

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function getIntensityLevel(duration: number, maxDuration: number): number {
  if (duration === 0 || maxDuration === 0) return 0;
  const ratio = duration / maxDuration;
  if (ratio < 0.25) return 1;
  if (ratio < 0.5) return 2;
  if (ratio < 0.75) return 3;
  return 4;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  date: string;
  duration: number;
  count: number;
}

export function ActivityHeatmap({
  apiUrl = 'http://localhost:8000',
  year = new Date().getFullYear(),
  onDayClick,
}: ActivityHeatmapProps) {
  const [data, setData] = useState<HeatmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    date: '',
    duration: 0,
    count: 0,
  });

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const response = await fetch(`${apiUrl}/dashboard/heatmap?year=${year}`);
        if (!response.ok) throw new Error('Failed to fetch heatmap data');
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [apiUrl, year]);

  // Create a map of date -> data for quick lookup
  const dayMap = useMemo(() => {
    if (!data) return new Map<string, HeatmapDay>();
    return new Map(data.days.map((d) => [d.date, d]));
  }, [data]);

  // Generate all days for the year organized by week
  const weeks = useMemo(() => {
    const result: { date: Date; data: HeatmapDay | null }[][] = [];
    const startDate = new Date(year, 0, 1);
    const endDate = new Date(year, 11, 31);

    // Adjust to start from the first Sunday before or on Jan 1
    const firstDay = new Date(startDate);
    firstDay.setDate(firstDay.getDate() - firstDay.getDay());

    const currentDate = new Date(firstDay);
    let currentWeek: { date: Date; data: HeatmapDay | null }[] = [];

    while (currentDate <= endDate || (currentWeek.length > 0 && currentWeek.length < 7)) {
      const dateStr = currentDate.toISOString().split('T')[0];
      const isInYear = currentDate.getFullYear() === year;

      currentWeek.push({
        date: new Date(currentDate),
        data: isInYear ? dayMap.get(dateStr) || null : null,
      });

      if (currentWeek.length === 7) {
        result.push(currentWeek);
        currentWeek = [];
      }

      currentDate.setDate(currentDate.getDate() + 1);
    }

    if (currentWeek.length > 0) {
      result.push(currentWeek);
    }

    return result;
  }, [year, dayMap]);

  // Calculate month labels with their starting week positions
  const monthLabels = useMemo(() => {
    const labels: { month: string; weekIndex: number }[] = [];
    let lastMonth = -1;

    weeks.forEach((week, weekIndex) => {
      // Find the first day of the week that's in our target year
      const firstDayInYear = week.find((d) => d.date.getFullYear() === year);
      if (firstDayInYear) {
        const month = firstDayInYear.date.getMonth();
        if (month !== lastMonth) {
          labels.push({ month: MONTHS[month], weekIndex });
          lastMonth = month;
        }
      }
    });

    return labels;
  }, [weeks, year]);

  const handleMouseEnter = (
    e: React.MouseEvent<HTMLDivElement>,
    day: { date: Date; data: HeatmapDay | null }
  ) => {
    if (day.date.getFullYear() !== year) return;

    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      visible: true,
      x: rect.left + rect.width / 2,
      y: rect.top - 10,
      date: day.date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }),
      duration: day.data?.duration_minutes || 0,
      count: day.data?.count || 0,
    });
  };

  const handleMouseLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  };

  const handleDayClick = (day: { date: Date; data: HeatmapDay | null }) => {
    if (day.date.getFullYear() !== year) return;
    const dateStr = day.date.toISOString().split('T')[0];
    onDayClick?.(dateStr, day.data);
  };

  if (loading) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4 h-48 animate-pulse" data-testid="heatmap-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="heatmap-error">
        Error: {error}
      </div>
    );
  }

  const totalActivities = data?.days.reduce((sum, d) => sum + d.count, 0) || 0;
  const totalDuration = data?.days.reduce((sum, d) => sum + d.duration_minutes, 0) || 0;

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="activity-heatmap">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Grid3x3 className="w-5 h-5 text-green-400" />
          <h3 className="text-lg font-semibold text-foreground">Activity Heatmap</h3>
        </div>
        <div className="flex gap-4 text-sm text-muted-foreground">
          <span>{totalActivities} activities</span>
          <span>{Math.round(totalDuration / 60)} hrs total</span>
        </div>
      </div>

      {/* Month labels */}
      <div className="flex mb-1 ml-8">
        {monthLabels.map((label, idx) => (
          <div
            key={idx}
            className="text-xs text-muted-foreground"
            style={{
              position: 'relative',
              left: `${label.weekIndex * 14}px`,
              marginRight: idx < monthLabels.length - 1 ? '-14px' : 0,
            }}
          >
            {label.month}
          </div>
        ))}
      </div>

      {/* Heatmap grid */}
      <div className="flex gap-1 overflow-x-auto pb-2">
        {/* Day labels */}
        <div className="flex flex-col gap-[3px] mr-1 flex-shrink-0">
          {DAYS.map((day, idx) => (
            <div
              key={day}
              className="text-xs text-muted-foreground h-[12px] flex items-center"
              style={{ visibility: idx % 2 === 0 ? 'hidden' : 'visible' }}
            >
              {day.slice(0, 3)}
            </div>
          ))}
        </div>

        {/* Weeks */}
        <div className="flex gap-[3px]">
          {weeks.map((week, weekIdx) => (
            <div key={weekIdx} className="flex flex-col gap-[3px]">
              {week.map((day, dayIdx) => {
                const isInYear = day.date.getFullYear() === year;
                const intensity = isInYear
                  ? getIntensityLevel(
                      day.data?.duration_minutes || 0,
                      data?.max_duration || 1
                    )
                  : 0;

                return (
                  <div
                    key={dayIdx}
                    className={`w-[12px] h-[12px] rounded-sm cursor-pointer transition-all hover:ring-1 hover:ring-muted-foreground ${
                      isInYear ? INTENSITY_COLORS[intensity] : 'bg-transparent'
                    }`}
                    onMouseEnter={(e) => handleMouseEnter(e, day)}
                    onMouseLeave={handleMouseLeave}
                    onClick={() => handleDayClick(day)}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
        <span>Less</span>
        {INTENSITY_COLORS.map((color, idx) => (
          <div key={idx} className={`w-[12px] h-[12px] rounded-sm ${color}`} />
        ))}
        <span>More</span>
      </div>

      {/* Tooltip */}
      {tooltip.visible && (
        <div
          className="fixed z-50 bg-popover text-popover-foreground rounded-md shadow-lg border border-border px-3 py-2 text-sm pointer-events-none transform -translate-x-1/2 -translate-y-full"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className="font-medium text-foreground">{tooltip.date}</div>
          {tooltip.count > 0 ? (
            <div className="text-muted-foreground">
              {tooltip.count} {tooltip.count === 1 ? 'activity' : 'activities'} ({tooltip.duration} min)
            </div>
          ) : (
            <div className="text-muted-foreground">No activities</div>
          )}
        </div>
      )}
    </div>
  );
}
