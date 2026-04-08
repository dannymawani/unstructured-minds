import { useState, useEffect, useCallback, type ReactElement } from 'react';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface DayInfo {
  day: number;
  date: string;
  has_note: boolean;
  activity_level: number; // 0-3
}

interface MonthData {
  year: number;
  month: number;
  days: DayInfo[];
}

interface CalendarViewProps {
  apiUrl?: string;
  onDaySelect?: (date: string, hasNote: boolean) => void;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const DAY_NAMES = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

export function CalendarView({ apiUrl = 'http://localhost:8000', onDaySelect }: CalendarViewProps) {
  const today = new Date();
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1); // 1-indexed
  const [monthData, setMonthData] = useState<MonthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMonthData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${apiUrl}/calendar/month?year=${currentYear}&month=${currentMonth}`
      );
      if (!response.ok) {
        throw new Error('Failed to fetch calendar data');
      }
      const data = await response.json();
      setMonthData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [apiUrl, currentYear, currentMonth]);

  useEffect(() => {
    fetchMonthData();
  }, [fetchMonthData]);

  const goToPreviousMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12);
      setCurrentYear(currentYear - 1);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  };

  const goToNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1);
      setCurrentYear(currentYear + 1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  };

  const goToToday = () => {
    setCurrentYear(today.getFullYear());
    setCurrentMonth(today.getMonth() + 1);
  };

  const handleDayClick = async (day: DayInfo) => {
    if (onDaySelect) {
      onDaySelect(day.date, day.has_note);
    }
  };

  // Calculate the first day of the month (0 = Sunday, 6 = Saturday)
  const getFirstDayOfMonth = (year: number, month: number): number => {
    return new Date(year, month - 1, 1).getDay();
  };

  // Get activity level color class
  const getActivityColor = (level: number): string => {
    switch (level) {
      case 0:
        return 'bg-transparent';
      case 1:
        return 'bg-green-900/40';
      case 2:
        return 'bg-green-700/60';
      case 3:
        return 'bg-green-500/80';
      default:
        return 'bg-transparent';
    }
  };

  // Check if a day is today
  const isToday = (date: string): boolean => {
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    return date === todayStr;
  };

  // Render calendar grid
  const renderCalendar = () => {
    if (!monthData) return null;

    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);

    // Create array of day cells including empty cells for alignment
    const cells: (DayInfo | null)[] = [];

    // Add empty cells for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
      cells.push(null);
    }

    // Add actual days
    for (const day of monthData.days) {
      cells.push(day);
    }

    // Render rows of 7 days
    const rows: ReactElement[] = [];
    for (let i = 0; i < cells.length; i += 7) {
      const week = cells.slice(i, i + 7);
      rows.push(
        <tr key={i}>
          {week.map((day, index) => (
            <td key={index} className="p-1">
              {day ? (
                <button
                  onClick={() => handleDayClick(day)}
                  className={`
                    w-full aspect-square rounded-md flex flex-col items-center justify-center
                    text-sm transition-all hover:ring-2 hover:ring-blue-400
                    ${isToday(day.date) ? 'ring-2 ring-blue-500 font-bold' : ''}
                    ${getActivityColor(day.activity_level)}
                    ${day.has_note ? 'text-foreground font-medium' : 'text-muted-foreground'}
                  `}
                  title={`${day.date}${day.has_note ? ' (has note)' : ''}${day.activity_level > 0 ? ` - Activity level: ${day.activity_level}` : ''}`}
                >
                  <span>{day.day}</span>
                  {day.has_note && (
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-0.5" />
                  )}
                </button>
              ) : (
                <div className="w-full aspect-square" />
              )}
            </td>
          ))}
          {/* Fill remaining cells in the last row */}
          {week.length < 7 &&
            Array.from({ length: 7 - week.length }).map((_, index) => (
              <td key={`empty-${index}`} className="p-1">
                <div className="w-full aspect-square" />
              </td>
            ))}
        </tr>
      );
    }

    return rows;
  };

  return (
    <div className="p-3 sm:p-4" data-testid="calendar-view">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4 sm:mb-6">
        <Calendar className="w-5 h-5 sm:w-6 sm:h-6 text-blue-400" />
        <h1 className="text-xl sm:text-2xl font-bold text-foreground">Calendar</h1>
      </div>

      {/* Navigation */}
      <div className="bg-card rounded-md shadow-sm p-3 sm:p-4 mb-3 sm:mb-4">
        <div className="flex items-center justify-between mb-3 sm:mb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={goToPreviousMonth}
            aria-label="Previous month"
            className="min-w-[44px] min-h-[44px] p-0"
          >
            <ChevronLeft className="w-5 h-5" />
          </Button>

          <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-3">
            <h2 className="text-base sm:text-xl font-semibold text-foreground">
              {MONTH_NAMES[currentMonth - 1]} {currentYear}
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={goToToday}
              className="text-xs min-h-[36px]"
            >
              Today
            </Button>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={goToNextMonth}
            aria-label="Next month"
            className="min-w-[44px] min-h-[44px] p-0"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        {/* Calendar Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-pulse text-muted-foreground">Loading...</div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-64 text-red-400">
            Error: {error}
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {DAY_NAMES.map((day) => (
                  <th
                    key={day}
                    className="p-2 text-center text-sm font-medium text-muted-foreground"
                  >
                    {day}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>{renderCalendar()}</tbody>
          </table>
        )}
      </div>

      {/* Legend */}
      <div className="bg-card rounded-md shadow-sm p-3 sm:p-4">
        <h3 className="text-xs sm:text-sm font-medium text-muted-foreground mb-2 sm:mb-3">Legend</h3>
        <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2 sm:gap-4 text-xs sm:text-sm">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-400 flex-shrink-0" />
            <span className="text-muted-foreground">Has note</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded ring-2 ring-blue-500 flex-shrink-0" />
            <span className="text-muted-foreground">Today</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-green-900/40 flex-shrink-0" />
            <span className="text-muted-foreground">Low</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-green-700/60 flex-shrink-0" />
            <span className="text-muted-foreground">Medium</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-green-500/80 flex-shrink-0" />
            <span className="text-muted-foreground">High</span>
          </div>
        </div>
      </div>
    </div>
  );
}
