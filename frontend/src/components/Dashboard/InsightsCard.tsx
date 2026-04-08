import { useEffect, useState, useCallback } from 'react';
import { Lightbulb, RefreshCw, X, TrendingUp, Clock, CheckSquare, Sparkles } from 'lucide-react';

interface Insight {
  id: string;
  type: 'pattern' | 'trend' | 'reminder' | 'follow_up';
  title: string;
  message: string;
  priority: number;
  data_source?: string;
}

interface InsightsData {
  insights: Insight[];
  generated_at: string;
}

interface InsightsCardProps {
  apiUrl?: string;
}

const INSIGHT_ICONS: Record<string, typeof Lightbulb> = {
  pattern: Sparkles,
  trend: TrendingUp,
  reminder: Clock,
  follow_up: CheckSquare,
};

const PRIORITY_COLORS: Record<number, string> = {
  1: 'border-l-red-400',
  2: 'border-l-yellow-400',
  3: 'border-l-green-400',
};

const DISMISSED_KEY = 'insights-dismissed';

function getDismissedInsights(): Set<string> {
  try {
    const stored = localStorage.getItem(DISMISSED_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Clean up entries older than 24 hours
      const now = Date.now();
      const valid = Object.entries(parsed).filter(
        ([, timestamp]) => now - (timestamp as number) < 24 * 60 * 60 * 1000
      );
      const cleaned = Object.fromEntries(valid);
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(cleaned));
      return new Set(valid.map(([id]) => id));
    }
  } catch {
    // Ignore localStorage errors
  }
  return new Set();
}

function dismissInsight(id: string): void {
  try {
    const stored = localStorage.getItem(DISMISSED_KEY);
    const dismissed = stored ? JSON.parse(stored) : {};
    dismissed[id] = Date.now();
    localStorage.setItem(DISMISSED_KEY, JSON.stringify(dismissed));
  } catch {
    // Ignore localStorage errors
  }
}

export function InsightsCard({ apiUrl = 'http://localhost:8000' }: InsightsCardProps) {
  const [data, setData] = useState<InsightsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<Set<string>>(() => getDismissedInsights());
  const [refreshing, setRefreshing] = useState(false);

  const fetchInsights = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/insights/daily`);
      if (!response.ok) throw new Error('Failed to fetch insights');
      const result = await response.json();
      setData(result);

      if (isRefresh) {
        // Clear dismissed insights on refresh
        setDismissed(new Set());
        localStorage.removeItem(DISMISSED_KEY);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  const handleDismiss = (id: string) => {
    dismissInsight(id);
    setDismissed((prev) => new Set([...prev, id]));

    // Optionally notify backend
    fetch(`${apiUrl}/insights/dismiss/${id}`, { method: 'POST' }).catch(() => {
      // Ignore errors
    });
  };

  const handleRefresh = () => {
    fetchInsights(true);
  };

  // Filter out dismissed insights
  const visibleInsights = data?.insights.filter((i) => !dismissed.has(i.id)) || [];

  if (loading) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="insights-loading">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="w-5 h-5 text-yellow-400" />
          <h3 className="text-lg font-semibold text-foreground">Insights</h3>
        </div>
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="insights-error">
        <div className="flex items-center gap-2 mb-2">
          <Lightbulb className="w-5 h-5 text-yellow-400" />
          <h3 className="text-lg font-semibold text-foreground">Insights</h3>
        </div>
        <p className="text-destructive text-sm">Failed to load insights</p>
        <button
          onClick={() => fetchInsights()}
          className="mt-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="insights-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-400" />
          <h3 className="text-lg font-semibold text-foreground">Insights</h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="p-1.5 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
          aria-label="Refresh insights"
          title="Refresh insights"
        >
          <RefreshCw className={`w-4 h-4 text-muted-foreground ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {visibleInsights.length === 0 ? (
        <div className="text-center py-6 text-muted-foreground" data-testid="insights-empty">
          <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No new insights</p>
          <p className="text-xs mt-1">Check back later or refresh for updates</p>
        </div>
      ) : (
        <div className="space-y-3">
          {visibleInsights.map((insight) => {
            const Icon = INSIGHT_ICONS[insight.type] || Lightbulb;
            const priorityClass = PRIORITY_COLORS[insight.priority] || PRIORITY_COLORS[3];

            return (
              <div
                key={insight.id}
                className={`relative bg-muted/50 rounded-lg p-3 border-l-4 ${priorityClass} group`}
                data-testid={`insight-${insight.id}`}
              >
                <button
                  onClick={() => handleDismiss(insight.id)}
                  className="absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                  aria-label="Dismiss insight"
                  title="Dismiss"
                >
                  <X className="w-3.5 h-3.5 text-muted-foreground" />
                </button>

                <div className="flex items-start gap-3 pr-6">
                  <div className="flex-shrink-0 mt-0.5">
                    <Icon className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-medium text-foreground truncate">
                      {insight.title}
                    </h4>
                    <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                      {insight.message}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
