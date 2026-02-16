import { useState, useMemo, useEffect, useCallback } from 'react';
import { LayoutDashboard } from 'lucide-react';
import { DashboardSummary } from './DashboardSummary';
import { WeeklyActivityChart } from './WeeklyActivityChart';
import { MetricsTrends } from './MetricsTrends';
import { ExerciseTable } from './ExerciseTable';
import { ActivityHeatmap } from './ActivityHeatmap';
import { SleepTrends } from './SleepTrends';
import { MoodCorrelation } from './MoodCorrelation';
import { NutritionTile } from './NutritionTile';
import { DateRangeSelector } from './DateRangeSelector';
import { InsightsCard } from './InsightsCard';
import { WidgetConfigPanel, useWidgetConfig } from './WidgetConfig';
import { DemoBanner } from './DemoBanner';
import { OnboardingOverlay } from '../Onboarding/OnboardingOverlay';

interface OnboardingStatus {
  is_new_user: boolean;
  demo_active: boolean;
  onboarding_completed: boolean;
  demo_data_count: number;
  real_data_count: number;
}

interface DashboardProps {
  apiUrl?: string;
  onCreateNote?: () => void;
}

export function Dashboard({ apiUrl = 'http://localhost:8000', onCreateNote }: DashboardProps) {
  const [dateRange, setDateRange] = useState(30);
  const [widgets, setWidgets] = useWidgetConfig();
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Fetch onboarding status on mount
  useEffect(() => {
    async function fetchStatus() {
      try {
        const resp = await fetch(`${apiUrl}/onboarding/status`);
        if (resp.ok) {
          setOnboarding(await resp.json());
        }
      } catch {
        // Non-critical — dashboard works without onboarding status
      }
    }
    fetchStatus();
  }, [apiUrl, refreshKey]);

  const refresh = useCallback(() => {
    setRefreshKey(k => k + 1);
  }, []);

  const handleSeedDemo = useCallback(() => {
    setOnboarding(prev => prev ? { ...prev, is_new_user: false, demo_active: true, demo_data_count: 1 } : prev);
    refresh();
  }, [refresh]);

  const handleStartWriting = useCallback(() => {
    setOnboarding(prev => prev ? { ...prev, is_new_user: false, onboarding_completed: true } : prev);
    onCreateNote?.();
  }, [onCreateNote]);

  const handleDemoCleared = useCallback(() => {
    setOnboarding(prev => prev ? { ...prev, demo_active: false, demo_data_count: 0 } : prev);
    refresh();
  }, [refresh]);

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

  // Show new user overlay
  const showOverlay = onboarding?.is_new_user && !onboarding?.onboarding_completed;
  // Show demo banner when demo data is active
  const showBanner = onboarding?.demo_active && !onboarding?.is_new_user;

  return (
    <div className="p-4 sm:p-6 space-y-5 sm:space-y-6" data-testid="dashboard">
      {/* Onboarding overlay for new users */}
      {showOverlay && (
        <OnboardingOverlay
          apiUrl={apiUrl}
          onSeedDemo={handleSeedDemo}
          onStartWriting={handleStartWriting}
        />
      )}

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

      {/* Demo data banner */}
      {showBanner && (
        <DemoBanner
          apiUrl={apiUrl}
          onCreateNote={onCreateNote ?? (() => {})}
          onDemoCleared={handleDemoCleared}
        />
      )}

      {/* Summary Cards */}
      {isVisible('summary') && <DashboardSummary apiUrl={apiUrl} days={dateRange} key={`summary-${refreshKey}`} />}

      {/* AI Insights */}
      {isVisible('insights') && <InsightsCard apiUrl={apiUrl} key={`insights-${refreshKey}`} />}

      {/* Heatmap + Nutrition - Side by side */}
      {(isVisible('heatmap') || isVisible('nutrition')) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {isVisible('heatmap') && (
              <ActivityHeatmap
                apiUrl={apiUrl}
                onDayClick={handleHeatmapDayClick}
                key={`heatmap-${refreshKey}`}
              />
          )}
          {isVisible('nutrition') && <NutritionTile apiUrl={apiUrl} days={dateRange} key={`nutrition-${refreshKey}`} />}
        </div>
      )}

      {/* Charts Grid - Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {isVisible('weeklyActivity') && <WeeklyActivityChart apiUrl={apiUrl} days={dateRange} key={`weekly-${refreshKey}`} />}
        {isVisible('metricsTrends') && <MetricsTrends apiUrl={apiUrl} days={dateRange} key={`metrics-${refreshKey}`} />}
      </div>

      {/* Charts Grid - Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {isVisible('sleepTrends') && (
          <SleepTrends apiUrl={apiUrl} days={dateRange} onDayClick={handleSleepDayClick} key={`sleep-${refreshKey}`} />
        )}
        {isVisible('moodCorrelation') && <MoodCorrelation apiUrl={apiUrl} days={dateRange} key={`mood-${refreshKey}`} />}
      </div>

      {/* Exercise Table */}
      {isVisible('exerciseProgress') && (
        <ExerciseTable apiUrl={apiUrl} key={`exercise-${refreshKey}`} />
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
