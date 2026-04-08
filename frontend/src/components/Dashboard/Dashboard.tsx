import { useState, useMemo, useEffect, useCallback, Component, type ReactNode } from 'react';
import { LayoutDashboard, AlertTriangle } from 'lucide-react';
import { DashboardSummary } from './DashboardSummary';
import { WeeklyActivityChart } from './WeeklyActivityChart';
import { MetricsTrends } from './MetricsTrends';
import { ExerciseTable } from './ExerciseTable';
import { EnduranceLog } from './EnduranceLog';
import { ActivityHeatmap } from './ActivityHeatmap';
import { SleepTrends } from './SleepTrends';
import { BodyWeightChart } from './BodyWeightChart';
import { MoodCorrelation } from './MoodCorrelation';
import { MuscleGroupMap } from './MuscleGroupMap';
import { NutritionTile } from './NutritionTile';
import { DateRangeSelector } from './DateRangeSelector';
import { InsightsCard } from './InsightsCard';
import { WidgetConfigPanel, useWidgetConfig } from './WidgetConfig';
import { DemoBanner } from './DemoBanner';
import { OnboardingOverlay } from '../Onboarding/OnboardingOverlay';

class WidgetErrorBoundary extends Component<{ name: string; children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error) { console.error(`Widget "${this.props.name}" crashed:`, error); }
  render() {
    if (this.state.error) {
      return (
        <div className="bg-card rounded-md shadow-sm p-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-destructive" />
            <span className="font-medium text-foreground">{this.props.name} failed to load</span>
          </div>
          <p className="text-xs">{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

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

  // Handle heatmap day click - navigate to daily note
  const handleHeatmapDayClick = (_date: string, _data: { count: number; duration_minutes: number } | null) => {
    // TODO: navigate to daily note for the clicked date
  };

  // Handle sleep chart day click
  const handleSleepDayClick = (_date: string) => {
    // TODO: navigate to daily note for the clicked date
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
      {isVisible('summary') && <WidgetErrorBoundary name="Summary"><DashboardSummary apiUrl={apiUrl} days={dateRange} key={`summary-${refreshKey}`} /></WidgetErrorBoundary>}

      {/* AI Insights */}
      {isVisible('insights') && <WidgetErrorBoundary name="Insights"><InsightsCard apiUrl={apiUrl} key={`insights-${refreshKey}`} /></WidgetErrorBoundary>}

      {/* Heatmap + Nutrition - Side by side */}
      {(isVisible('heatmap') || isVisible('nutrition')) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {isVisible('heatmap') && (
              <WidgetErrorBoundary name="Activity Heatmap"><ActivityHeatmap
                apiUrl={apiUrl}
                onDayClick={handleHeatmapDayClick}
                key={`heatmap-${refreshKey}`}
              /></WidgetErrorBoundary>
          )}
          {isVisible('nutrition') && <WidgetErrorBoundary name="Nutrition"><NutritionTile apiUrl={apiUrl} days={dateRange} key={`nutrition-${refreshKey}`} /></WidgetErrorBoundary>}
        </div>
      )}

      {/* Charts Grid - Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {isVisible('weeklyActivity') && <WidgetErrorBoundary name="Weekly Activity"><WeeklyActivityChart apiUrl={apiUrl} days={dateRange} key={`weekly-${refreshKey}`} /></WidgetErrorBoundary>}
        {isVisible('metricsTrends') && <WidgetErrorBoundary name="Metrics Trends"><MetricsTrends apiUrl={apiUrl} days={dateRange} key={`metrics-${refreshKey}`} /></WidgetErrorBoundary>}
      </div>

      {/* Charts Grid - Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {isVisible('sleepTrends') && (
          <WidgetErrorBoundary name="Sleep Trends"><SleepTrends apiUrl={apiUrl} days={dateRange} onDayClick={handleSleepDayClick} key={`sleep-${refreshKey}`} /></WidgetErrorBoundary>
        )}
        {isVisible('moodCorrelation') && <WidgetErrorBoundary name="Mood Correlation"><MoodCorrelation apiUrl={apiUrl} days={dateRange} key={`mood-${refreshKey}`} /></WidgetErrorBoundary>}
      </div>

      {/* Muscle Groups + Body Weight */}
      {(isVisible('muscleGroups') || isVisible('bodyWeight')) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {isVisible('muscleGroups') && <WidgetErrorBoundary name="Muscle Groups"><MuscleGroupMap apiUrl={apiUrl} days={dateRange} key={`muscles-${refreshKey}`} /></WidgetErrorBoundary>}
          {isVisible('bodyWeight') && <WidgetErrorBoundary name="Body Weight"><BodyWeightChart apiUrl={apiUrl} days={dateRange} key={`weight-${refreshKey}`} /></WidgetErrorBoundary>}
        </div>
      )}

      {/* Exercise Table */}
      {isVisible('exerciseProgress') && (
        <WidgetErrorBoundary name="Exercise Table"><ExerciseTable apiUrl={apiUrl} key={`exercise-${refreshKey}`} /></WidgetErrorBoundary>
      )}

      {/* Endurance Log */}
      {isVisible('enduranceLog') && (
        <WidgetErrorBoundary name="Endurance Log"><EnduranceLog apiUrl={apiUrl} key={`endurance-${refreshKey}`} /></WidgetErrorBoundary>
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
