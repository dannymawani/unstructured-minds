import { useEffect, useState } from 'react';
import { Activity, Dumbbell, Flame, Calendar } from 'lucide-react';

interface SummaryData {
  total_activities: number;
  total_exercises: number;
  streak_days: number;
  last_activity_date: string | null;
}

interface DashboardSummaryProps {
  apiUrl?: string;
}

export function DashboardSummary({ apiUrl = 'http://localhost:8000' }: DashboardSummaryProps) {
  const [data, setData] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSummary() {
      try {
        const response = await fetch(`${apiUrl}/dashboard/summary`);
        if (!response.ok) throw new Error('Failed to fetch summary');
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchSummary();
  }, [apiUrl]);

  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" data-testid="summary-loading">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-card border rounded-lg p-3 sm:p-4 animate-pulse h-20 sm:h-24" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-destructive p-4" data-testid="summary-error">
        Error loading summary: {error}
      </div>
    );
  }

  const cards = [
    {
      label: 'Activities',
      value: data?.total_activities ?? 0,
      icon: Activity,
      color: 'text-blue-400',
    },
    {
      label: 'Exercises',
      value: data?.total_exercises ?? 0,
      icon: Dumbbell,
      color: 'text-green-400',
    },
    {
      label: 'Day Streak',
      value: data?.streak_days ?? 0,
      icon: Flame,
      color: 'text-orange-400',
    },
    {
      label: 'Last Activity',
      value: data?.last_activity_date ?? 'None',
      icon: Calendar,
      color: 'text-purple-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" data-testid="dashboard-summary">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-card border rounded-lg p-3 sm:p-4 flex flex-col"
        >
          <div className="flex items-center gap-2 text-muted-foreground text-xs sm:text-sm mb-1 sm:mb-2">
            <card.icon className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${card.color}`} />
            <span className="truncate">{card.label}</span>
          </div>
          <div className="text-lg sm:text-2xl font-bold text-foreground truncate">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
