import { useEffect, useState, useMemo } from 'react';
import { Grid3x3 } from 'lucide-react';

interface HeatmapDay {
  date: string;
  count: number;
  duration_minutes: number;
  has_note: boolean;
  has_workout: boolean;
}

interface HeatmapData {
  days: HeatmapDay[];
  year: number;
  max_count: number;
  max_duration: number;
}

interface ActivityHeatmapProps {
  apiUrl?: string;
  onDayClick?: (date: string, data: HeatmapDay | null) => void;
}

// Green intensity scale for active days (has workout)
const ACTIVE_COLORS = [
  'bg-muted',                   // 0 - no activity
  'bg-green-900/60',            // 1 - light
  'bg-green-700/70',            // 2 - moderate
  'bg-green-500/80',            // 3 - active
  'bg-green-400',               // 4 - very active
];


function formatLocalDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getIntensityLevel(duration: number, maxDuration: number): number {
  if (duration === 0 || maxDuration === 0) return 0;
  const ratio = duration / maxDuration;
  if (ratio < 0.25) return 1;
  if (ratio < 0.5) return 2;
  if (ratio < 0.75) return 3;
  return 4;
}

function getDayColor(day: HeatmapDay | null, maxDuration: number): string {
  if (!day) return ACTIVE_COLORS[0];
  if (day.has_workout) {
    return ACTIVE_COLORS[getIntensityLevel(day.duration_minutes, maxDuration)];
  }
  if (day.has_note) {
    return 'bg-blue-500/50';
  }
  return ACTIVE_COLORS[0];
}

function getDayTypeLabel(day: HeatmapDay | null): string {
  if (!day) return 'No entries';
  if (day.has_workout) return 'Active';
  if (day.has_note) return 'Note only';
  return 'No entries';
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  date: string;
  duration: number;
  count: number;
  dayType: string;
}

export function ActivityHeatmap({
  apiUrl = 'http://localhost:8000',
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
    dayType: '',
  });

  // Rolling 4-month window: 3 months back + current month
  const { windowStart, windowEnd, yearsNeeded } = useMemo(() => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth() - 3, 1);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0); // last day of current month
    const years = new Set([start.getFullYear(), end.getFullYear()]);
    return { windowStart: start, windowEnd: end, yearsNeeded: Array.from(years) };
  }, []);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const allDays: HeatmapDay[] = [];
        let maxCount = 0;
        let maxDuration = 0;

        for (const y of yearsNeeded) {
          const response = await fetch(`${apiUrl}/dashboard/heatmap?year=${y}`);
          if (!response.ok) throw new Error('Failed to fetch heatmap data');
          const result: HeatmapData = await response.json();
          allDays.push(...result.days);
          maxCount = Math.max(maxCount, result.max_count);
          maxDuration = Math.max(maxDuration, result.max_duration);
        }

        // Filter to only days within the 4-month window
        const startStr = formatLocalDate(windowStart);
        const endStr = formatLocalDate(windowEnd);
        const filtered = allDays.filter(d => d.date >= startStr && d.date <= endStr);

        setData({
          days: filtered,
          year: windowEnd.getFullYear(),
          max_count: maxCount,
          max_duration: maxDuration,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [apiUrl, yearsNeeded, windowStart, windowEnd]);

  // Map date string -> data for quick lookup
  const dayMap = useMemo(() => {
    if (!data) return new Map<string, HeatmapDay>();
    return new Map(data.days.map((d) => [d.date, d]));
  }, [data]);

  // Generate weeks for the 4-month window only
  const weeks = useMemo(() => {
    const result: { date: Date; data: HeatmapDay | null }[][] = [];

    // Start from the Sunday before or on windowStart
    const firstDay = new Date(windowStart);
    firstDay.setDate(firstDay.getDate() - firstDay.getDay());

    // End at the Saturday after or on windowEnd
    const lastDay = new Date(windowEnd);
    if (lastDay.getDay() < 6) {
      lastDay.setDate(lastDay.getDate() + (6 - lastDay.getDay()));
    }

    const currentDate = new Date(firstDay);
    let currentWeek: { date: Date; data: HeatmapDay | null }[] = [];

    while (currentDate <= lastDay) {
      const dateStr = formatLocalDate(currentDate);
      const inRange = currentDate >= windowStart && currentDate <= windowEnd;

      currentWeek.push({
        date: new Date(currentDate),
        data: inRange ? dayMap.get(dateStr) || null : null,
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
  }, [windowStart, windowEnd, dayMap]);

  // Month labels positioned at the first week that falls in each month
  const monthLabels = useMemo(() => {
    const labels: { weekIdx: number; label: string }[] = [];
    let lastMonth = -1;
    weeks.forEach((week, weekIdx) => {
      // Use the first in-range day of the week to determine month
      const representative = week.find(d => d.date >= windowStart && d.date <= windowEnd);
      if (!representative) return;
      const month = representative.date.getMonth();
      if (month !== lastMonth) {
        labels.push({
          weekIdx,
          label: representative.date.toLocaleDateString('en-US', { month: 'short' }),
        });
        lastMonth = month;
      }
    });
    return labels;
  }, [weeks, windowStart, windowEnd]);

  const handleMouseEnter = (
    e: React.MouseEvent<HTMLDivElement>,
    day: { date: Date; data: HeatmapDay | null }
  ) => {
    if (day.date < windowStart || day.date > windowEnd) return;

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
      dayType: getDayTypeLabel(day.data),
    });
  };

  const handleMouseLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  };

  const handleDayClick = (day: { date: Date; data: HeatmapDay | null }) => {
    if (day.date < windowStart || day.date > windowEnd) return;
    const dateStr = formatLocalDate(day.date);
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

  const activeDays = data?.days.filter((d) => d.has_note || d.has_workout).length || 0;

  return (
    <div className="bg-card shadow-sm px-3 sm:px-5 py-4 w-full" data-testid="activity-heatmap">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Grid3x3 className="w-5 h-5 text-green-400" />
          <h3 className="text-lg font-semibold text-foreground">Activity Heatmap</h3>
        </div>
        <div className="text-sm text-muted-foreground">
          <span>{activeDays} active days</span>
        </div>
      </div>

      {/* Month labels */}
      <div className="flex gap-[2px] mb-1 ml-[28px]">
        {weeks.map((_, weekIdx) => {
          const label = monthLabels.find(m => m.weekIdx === weekIdx);
          return (
            <div key={weekIdx} className="flex-1 min-w-0 text-[10px] text-muted-foreground">
              {label ? label.label : ''}
            </div>
          );
        })}
      </div>

      {/* Heatmap grid with day-of-week labels */}
      <div className="flex gap-[2px] w-full">
        {/* Day-of-week labels */}
        <div className="flex flex-col gap-[2px] shrink-0 w-[26px] mr-px">
          {['', 'Mon', '', 'Wed', '', 'Fri', ''].map((label, i) => (
            <div key={i} className="aspect-square flex items-center">
              <span className="text-[9px] text-muted-foreground leading-none">{label}</span>
            </div>
          ))}
        </div>

        {/* Weeks */}
        <div className="flex gap-[2px] flex-1 min-w-0">
          {weeks.map((week, weekIdx) => (
            <div key={weekIdx} className="flex flex-col gap-[2px] flex-1 min-w-0">
              {week.map((day, dayIdx) => {
                const inRange = day.date >= windowStart && day.date <= windowEnd;
                const color = inRange
                  ? getDayColor(day.data, data?.max_duration || 1)
                  : 'bg-transparent';

                return (
                  <div
                    key={dayIdx}
                    className={`aspect-square w-full rounded-sm cursor-pointer transition-all hover:ring-1 hover:ring-muted-foreground ${color}`}
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
        {/* Note only indicator */}
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-sm bg-blue-500/50" />
          <span>Note only</span>
        </div>

        {/* Activity intensity gradient */}
        <div className="flex items-center gap-1.5">
          <span>Less active</span>
          <div className="flex gap-[2px]">
            <div className="w-2.5 h-2.5 rounded-sm bg-muted" />
            <div className="w-2.5 h-2.5 rounded-sm bg-green-900/60" />
            <div className="w-2.5 h-2.5 rounded-sm bg-green-700/70" />
            <div className="w-2.5 h-2.5 rounded-sm bg-green-500/80" />
            <div className="w-2.5 h-2.5 rounded-sm bg-green-400" />
          </div>
          <span>More active</span>
        </div>
      </div>

      {/* Tooltip */}
      {tooltip.visible && (
        <div
          className="fixed z-50 bg-popover text-popover-foreground rounded-md shadow-lg border border-border px-3 py-2 text-sm pointer-events-none transform -translate-x-1/2 -translate-y-full"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className="font-medium text-foreground">{tooltip.date}</div>
          <div className="text-muted-foreground">{tooltip.dayType}</div>
          {tooltip.duration > 0 && (
            <div className="text-muted-foreground">
              {tooltip.duration} min
            </div>
          )}
        </div>
      )}
    </div>
  );
}
