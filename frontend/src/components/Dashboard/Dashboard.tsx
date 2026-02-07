import { useState, useMemo } from 'react';
import { LayoutDashboard } from 'lucide-react';
import { DashboardSummary } from './DashboardSummary';
import { WeeklyActivityChart } from './WeeklyActivityChart';
import { MetricsTrends } from './MetricsTrends';
import { ExerciseProgress } from './ExerciseProgress';
import { ActivityHeatmap } from './ActivityHeatmap';
import { SleepTrends } from './SleepTrends';
import { MoodCorrelation } from './MoodCorrelation';
import { DateRangeSelector } from './DateRangeSelector';
import { InsightsCard } from './InsightsCard';
import { WidgetConfigPanel, useWidgetConfig } from './WidgetConfig';

interface DashboardProps {
  apiUrl?: string;
}

export function Dashboard({ apiUrl = 'http://localhost:8000' }: DashboardProps) {
  const [trackedExercise, setTrackedExercise] = useState('Squat');
  const [dateRange, setDateRange] = useState(30);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [widgets, setWidgets] = useWidgetConfig();

  const commonExercises = ['Squat', 'Bench Press', 'Deadlift', 'Overhead Press', 'Row'];

  // Get visible widgets sorted by order
  const visibleWidgets = useMemo(() => {
    return widgets
      .filter((w) => w.visible)
      .sort((a, b) => a.order - b.order)
      .map((w) => w.id);
  }, [widgets]);

  const isVisible = (widgetId: string) => visibleWidgets.includes(widgetId);

  // Handle heatmap day click - could navigate to daily note
  const handleHeatmapDayClick = (date: string, data: { count: number; duration_minutes: number } | null) => {
    console.log('Clicked day:', date, data);
    // Could dispatch to open daily note or show details
  };

  // Handle sleep chart day click
  const handleSleepDayClick = (date: string) => {
    console.log('Clicked sleep day:', date);
  };

  return (
    <div className="p-4 sm:p-6 space-y-5 sm:space-y-6" data-testid="dashboard">
      {/* Header with controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-2 sm:mb-4">
        <div className="flex items-center gap-2.5">
          <LayoutDashboard className="w-5 h-5 text-accent" />
          <h1 className="text-lg sm:text-xl font-semibold tracking-tight text-foreground">Dashboard</h1>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <DateRangeSelector value={dateRange} onChange={setDateRange} />
          <WidgetConfigPanel widgets={widgets} onChange={setWidgets} />
        </div>
      </div>

      {/* Summary Cards */}
      {isVisible('summary') && <DashboardSummary apiUrl={apiUrl} />}

      {/* AI Insights */}
      {isVisible('insights') && <InsightsCard apiUrl={apiUrl} />}

      {/* Activity Heatmap - Full width */}
      {isVisible('heatmap') && (
        <div className="relative">
          {/* Year selector for heatmap */}
          <div className="absolute top-4 right-4 z-10">
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="bg-secondary text-foreground text-sm rounded px-2 py-1 border-none focus:ring-2 focus:ring-ring"
            >
              {[...Array(3)].map((_, i) => {
                const year = new Date().getFullYear() - i;
                return (
                  <option key={year} value={year}>
                    {year}
                  </option>
                );
              })}
            </select>
          </div>
          <ActivityHeatmap
            apiUrl={apiUrl}
            year={selectedYear}
            onDayClick={handleHeatmapDayClick}
          />
        </div>
      )}

      {/* Charts Grid - Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {isVisible('weeklyActivity') && <WeeklyActivityChart apiUrl={apiUrl} days={dateRange} />}
        {isVisible('metricsTrends') && <MetricsTrends apiUrl={apiUrl} days={dateRange} />}
      </div>

      {/* Charts Grid - Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {isVisible('sleepTrends') && (
          <SleepTrends apiUrl={apiUrl} days={dateRange} onDayClick={handleSleepDayClick} />
        )}
        {isVisible('moodCorrelation') && <MoodCorrelation apiUrl={apiUrl} days={dateRange} />}
      </div>

      {/* Exercise Progress */}
      {isVisible('exerciseProgress') && (
        <div className="bg-card rounded-md shadow-sm p-3 sm:p-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 mb-3 sm:mb-4">
            <h3 className="text-base sm:text-lg font-semibold text-foreground">Track Exercise</h3>
            <select
              value={trackedExercise}
              onChange={(e) => setTrackedExercise(e.target.value)}
              className="bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring min-h-[44px] sm:min-h-0"
              data-testid="exercise-select"
            >
              {commonExercises.map((ex) => (
                <option key={ex} value={ex}>
                  {ex}
                </option>
              ))}
            </select>
          </div>
          <ExerciseProgress exercise={trackedExercise} apiUrl={apiUrl} days={dateRange} />
        </div>
      )}

      {/* Empty state when no widgets visible */}
      {visibleWidgets.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <p className="mb-2">No widgets visible</p>
          <p className="text-sm">
            Click the Customize button to add widgets to your dashboard.
          </p>
        </div>
      )}
    </div>
  );
}
