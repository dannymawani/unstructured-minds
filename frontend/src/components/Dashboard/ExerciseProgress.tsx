import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Brush,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, Dumbbell, Target } from 'lucide-react';

interface ProgressEntry {
  date: string;
  max_weight_kg: number | null;
  total_reps: number;
  total_sets: number;
}

interface ExerciseSummary {
  current_max: number | null;
  all_time_max: number | null;
  total_volume: number;
  total_sessions: number;
}

interface ExerciseProgressData {
  exercise: string;
  progress: ProgressEntry[];
  summary: ExerciseSummary;
}

interface ExerciseProgressProps {
  exercise: string;
  apiUrl?: string;
  days?: number;
  onDayClick?: (date: string) => void;
}

interface ChartDataPoint {
  date: string;
  fullDate: string;
  rawDate: string;
  weight: number | null;
  reps: number;
  sets: number;
  volume: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: ChartDataPoint;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm shadow-xl">
      <div className="font-medium text-white mb-2">{data.fullDate}</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {data.weight !== null && (
          <>
            <span className="text-zinc-400">Max Weight:</span>
            <span className="text-purple-400 font-medium">{data.weight} kg</span>
          </>
        )}
        <span className="text-zinc-400">Total Reps:</span>
        <span className="text-white">{data.reps}</span>
        <span className="text-zinc-400">Sets:</span>
        <span className="text-white">{data.sets}</span>
        {data.weight && (
          <>
            <span className="text-zinc-400">Volume:</span>
            <span className="text-white">{data.volume.toLocaleString()} kg</span>
          </>
        )}
      </div>
    </div>
  );
}

export function ExerciseProgress({
  exercise,
  apiUrl = 'http://localhost:8000',
  days = 30,
  onDayClick,
}: ExerciseProgressProps) {
  const [data, setData] = useState<ExerciseProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showReps, setShowReps] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const response = await fetch(
          `${apiUrl}/dashboard/exercise-progress?exercise=${encodeURIComponent(exercise)}&days=${days}`
        );
        if (!response.ok) throw new Error('Failed to fetch exercise progress');
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [apiUrl, exercise, days]);

  if (loading) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4 h-64 animate-pulse" data-testid="exercise-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="exercise-error">
        Error: {error}
      </div>
    );
  }

  if (!data || data.progress.length === 0) {
    return (
      <div className="bg-zinc-800 rounded-lg p-4" data-testid="exercise-empty">
        <h3 className="text-lg font-semibold text-white mb-2">{exercise} Progress</h3>
        <p className="text-zinc-400">No data for this exercise yet.</p>
      </div>
    );
  }

  const chartData: ChartDataPoint[] = data.progress.map((p) => ({
    date: new Date(p.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    fullDate: new Date(p.date).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }),
    rawDate: p.date,
    weight: p.max_weight_kg,
    reps: p.total_reps,
    sets: p.total_sets,
    volume: (p.max_weight_kg || 0) * p.total_reps,
  }));

  // Calculate trend
  const firstWeight = data.progress[0]?.max_weight_kg;
  const lastWeight = data.progress[data.progress.length - 1]?.max_weight_kg;
  let trend: 'up' | 'down' | 'flat' = 'flat';
  let trendPercent = 0;

  if (firstWeight && lastWeight) {
    if (lastWeight > firstWeight) {
      trend = 'up';
      trendPercent = ((lastWeight - firstWeight) / firstWeight) * 100;
    } else if (lastWeight < firstWeight) {
      trend = 'down';
      trendPercent = ((firstWeight - lastWeight) / firstWeight) * 100;
    }
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-zinc-400';

  // Calculate PR (personal record) within this period
  const periodMax = Math.max(...data.progress.filter((p) => p.max_weight_kg !== null).map((p) => p.max_weight_kg!), 0);
  const isPR = periodMax === data.summary.all_time_max;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleChartClick = (chartData: any) => {
    if (chartData?.activePayload?.[0]?.payload?.rawDate) {
      onDayClick?.(chartData.activePayload[0].payload.rawDate);
    }
  };

  return (
    <div className="bg-zinc-800 rounded-lg p-4" data-testid="exercise-progress">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3 mb-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Dumbbell className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{data.exercise} Progress</h3>
            <p className="text-sm text-zinc-400">{data.summary.total_sessions} sessions</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Toggle between weight and reps */}
          <div className="flex bg-zinc-700 rounded-lg p-1">
            <button
              className={`px-2 py-1 text-xs rounded transition-colors ${
                !showReps ? 'bg-purple-500 text-white' : 'text-zinc-400 hover:text-white'
              }`}
              onClick={() => setShowReps(false)}
            >
              Weight
            </button>
            <button
              className={`px-2 py-1 text-xs rounded transition-colors ${
                showReps ? 'bg-purple-500 text-white' : 'text-zinc-400 hover:text-white'
              }`}
              onClick={() => setShowReps(true)}
            >
              Reps
            </button>
          </div>

          <div className="text-right">
            <div className="flex items-center gap-1">
              <TrendIcon className={`w-4 h-4 ${trendColor}`} />
              <span className="text-xl font-bold text-white">
                {data.summary.current_max ?? '-'} kg
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              {trend !== 'flat' && (
                <span className={trendColor}>
                  {trend === 'up' ? '+' : '-'}{trendPercent.toFixed(1)}%
                </span>
              )}
              {' '}All-time: {data.summary.all_time_max ?? '-'} kg
              {isPR && periodMax > 0 && (
                <span className="ml-1 text-yellow-400">PR!</span>
              )}
            </p>
          </div>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            onClick={handleChartClick}
          >
            <defs>
              <linearGradient id="weightGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="date" stroke="#71717a" fontSize={12} tickLine={false} />
            <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />

            {/* Target line at all-time max */}
            {data.summary.all_time_max && !showReps && (
              <ReferenceLine
                y={data.summary.all_time_max}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                strokeOpacity={0.5}
                label={{
                  value: 'PR',
                  position: 'right',
                  fill: '#f59e0b',
                  fontSize: 10,
                }}
              />
            )}

            <Line
              type="monotone"
              dataKey={showReps ? 'reps' : 'weight'}
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={{ fill: '#8b5cf6', r: 4, strokeWidth: 0 }}
              activeDot={{
                fill: '#a78bfa',
                r: 6,
                strokeWidth: 2,
                stroke: '#fff',
                cursor: 'pointer',
              }}
              connectNulls
            />

            {/* Brush for data range selection on larger datasets */}
            {chartData.length > 14 && (
              <Brush
                dataKey="date"
                height={20}
                stroke="#8b5cf6"
                fill="#27272a"
                tickFormatter={(value) => value}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Stats footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-700 text-xs text-zinc-400">
        <div className="flex items-center gap-4">
          <span>
            <Target className="w-3 h-3 inline mr-1" />
            Total Volume: {data.summary.total_volume.toLocaleString()} kg
          </span>
        </div>
        <span>Click a point to view details</span>
      </div>
    </div>
  );
}
