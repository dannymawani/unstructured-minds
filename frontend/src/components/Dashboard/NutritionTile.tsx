import { useEffect, useState, useMemo } from 'react';
import { UtensilsCrossed } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface DayEntry {
  date: string;
  total_calories: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  meal_count: number;
}

interface NutritionSummary {
  avg_calories: number;
  avg_protein_g: number;
  avg_carbs_g: number;
  avg_fat_g: number;
  total_days_tracked: number;
  total_meals: number;
}

interface NutritionData {
  days: DayEntry[];
  summary: NutritionSummary;
  period: { start_date: string; end_date: string; days: number };
}

interface NutritionTileProps {
  apiUrl?: string;
  days?: number;
}

const MACRO_COLORS = { protein: '#3b82f6', carbs: '#f59e0b', fat: '#ef4444' } as const;

// Calorie estimation adjustment — accounts for untracked snacks, cooking oils, etc.
const CALORIE_ADJUSTMENT = 1.23;

// Bar chart layout
const BAR_W = 400;
const BAR_H = 120;
const BAR_PAD = { t: 6, r: 8, b: 20, l: 36 };
const barPlotW = BAR_W - BAR_PAD.l - BAR_PAD.r;
const barPlotH = BAR_H - BAR_PAD.t - BAR_PAD.b;

function formatDateShort(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getYTicks(yMax: number): number[] {
  const step = yMax <= 1500 ? 500 : yMax <= 3000 ? 500 : 1000;
  const ticks: number[] = [0];
  let v = step;
  while (v <= yMax) { ticks.push(v); v += step; }
  return ticks;
}

export function NutritionTile({ apiUrl = 'http://localhost:8000', days = 30 }: NutritionTileProps) {
  const [data, setData] = useState<NutritionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    cachedFetch<NutritionData>(`${apiUrl}/dashboard/nutrition?days=${days}`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, days]);

  const barChartData = useMemo(() => {
    if (!data || data.days.length === 0) return null;
    const adjustedCalories = data.days.map((d) => d.total_calories * CALORIE_ADJUSTMENT);
    const maxCal = Math.max(...adjustedCalories);
    const yMax = Math.ceil(maxCal / 500) * 500 || 2500;
    const n = data.days.length;
    const barWidth = Math.max(2, (barPlotW / n) * 0.7);
    const gap = barPlotW / n;
    return {
      yMax, n, barWidth, gap,
      entries: data.days.map((d, i) => {
        const cal = Math.round(d.total_calories * CALORIE_ADJUSTMENT);
        return {
          ...d,
          total_calories: cal,
          x: BAR_PAD.l + i * gap + gap / 2,
          height: (cal / yMax) * barPlotH,
        };
      }),
    };
  }, [data]);

  const xTicks = useMemo(() => {
    if (!barChartData || !data) return [];
    const n = barChartData.n;
    const tickCount = Math.min(6, n);
    if (tickCount <= 1) {
      return data.days[0] ? [{ x: barChartData.entries[0].x, label: formatDateShort(data.days[0].date) }] : [];
    }
    return Array.from({ length: tickCount }, (_, i) => {
      const idx = Math.round((i / (tickCount - 1)) * (n - 1));
      return { x: barChartData.entries[idx].x, label: formatDateShort(data.days[idx].date) };
    });
  }, [barChartData, data]);

  if (loading) {
    return <div className="bg-card rounded-md shadow-sm p-4 h-48 animate-pulse" data-testid="nutrition-loading" />;
  }
  if (error) {
    return <div className="text-red-400 p-4" data-testid="nutrition-error">Error: {error}</div>;
  }
  if (!data || data.days.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4" data-testid="nutrition-empty">
        <div className="flex items-center gap-2 mb-2">
          <UtensilsCrossed className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-foreground">Eating Habits</h3>
        </div>
        <p className="text-muted-foreground">No nutrition data recorded yet.</p>
      </div>
    );
  }

  const { summary } = data;
  const adjAvgCalories = Math.round(summary.avg_calories * CALORIE_ADJUSTMENT);

  const hoveredEntry = hoveredBar !== null && barChartData ? barChartData.entries[hoveredBar] : null;

  return (
    <div className="bg-card rounded-md shadow-sm p-4" data-testid="nutrition-tile">
      {/* Header + Summary row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-amber-500/20 rounded-lg">
            <UtensilsCrossed className="w-4 h-4 text-amber-400" />
          </div>
          <h3 className="text-lg font-semibold text-foreground">Eating Habits</h3>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-foreground font-semibold">{adjAvgCalories.toLocaleString()} <span className="text-xs text-muted-foreground font-normal">kcal/day</span></span>
          <span style={{ color: MACRO_COLORS.protein }} className="font-medium">{Math.round(summary.avg_protein_g)}g <span className="text-xs text-muted-foreground font-normal">P</span></span>
          <span style={{ color: MACRO_COLORS.carbs }} className="font-medium">{Math.round(summary.avg_carbs_g)}g <span className="text-xs text-muted-foreground font-normal">C</span></span>
          <span style={{ color: MACRO_COLORS.fat }} className="font-medium">{Math.round(summary.avg_fat_g)}g <span className="text-xs text-muted-foreground font-normal">F</span></span>
        </div>
      </div>

      {/* Daily Calorie Bar Chart */}
      {barChartData && (
        <div className="relative">
          <svg viewBox={`0 0 ${BAR_W} ${BAR_H}`} className="w-full" style={{ aspectRatio: `${BAR_W}/${BAR_H}` }}>
            {getYTicks(barChartData.yMax).map((v) => (
              <line key={v} x1={BAR_PAD.l} x2={BAR_W - BAR_PAD.r}
                y1={BAR_PAD.t + barPlotH - (v / barChartData.yMax) * barPlotH}
                y2={BAR_PAD.t + barPlotH - (v / barChartData.yMax) * barPlotH}
                stroke="#3f3f46" strokeWidth="0.5" />
            ))}
            {getYTicks(barChartData.yMax).map((v) => (
              <text key={`yl-${v}`} x={BAR_PAD.l - 4}
                y={BAR_PAD.t + barPlotH - (v / barChartData.yMax) * barPlotH + 3}
                fill="#71717a" fontSize="7" textAnchor="end">
                {v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}
              </text>
            ))}
            {barChartData.entries.map((entry, i) => (
              <g key={entry.date}>
                <rect x={entry.x - barChartData.barWidth / 2} y={BAR_PAD.t + barPlotH - entry.height}
                  width={barChartData.barWidth} height={entry.height} rx={1} fill="#f59e0b"
                  opacity={hoveredBar === null || hoveredBar === i ? 0.85 : 0.3}
                  style={{ transition: 'opacity 0.15s' }} />
                <rect x={entry.x - barChartData.gap / 2} y={BAR_PAD.t} width={barChartData.gap} height={barPlotH}
                  fill="transparent" style={{ cursor: 'pointer' }}
                  onMouseEnter={() => setHoveredBar(i)} onMouseLeave={() => setHoveredBar(null)} />
              </g>
            ))}
            {(() => {
              const avgY = BAR_PAD.t + barPlotH - (adjAvgCalories / barChartData.yMax) * barPlotH;
              return <line x1={BAR_PAD.l} x2={BAR_W - BAR_PAD.r} y1={avgY} y2={avgY}
                stroke="#14b8a6" strokeWidth="0.8" strokeDasharray="4 3" />;
            })()}
            {xTicks.map((t, i) => (
              <text key={i} x={t.x} y={BAR_H - 4} fill="#71717a" fontSize="7" textAnchor="middle">{t.label}</text>
            ))}
          </svg>
          {hoveredEntry && hoveredBar !== null && (
            <div className="absolute pointer-events-none bg-popover text-popover-foreground rounded-md shadow-lg border border-border px-2 py-1.5 text-xs z-10"
              style={{
                left: `${(hoveredEntry.x / BAR_W) * 100}%`,
                top: `${((BAR_PAD.t + barPlotH - hoveredEntry.height) / BAR_H) * 100}%`,
                transform: 'translate(-50%, -110%)',
              }}>
              <div className="font-medium text-foreground">
                {new Date(hoveredEntry.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
              </div>
              <div className="text-amber-400">{hoveredEntry.total_calories.toLocaleString()} kcal</div>
              <div className="text-muted-foreground">P:{hoveredEntry.total_protein_g}g C:{hoveredEntry.total_carbs_g}g F:{hoveredEntry.total_fat_g}g</div>
            </div>
          )}
        </div>
      )}

      {/* Compact footer */}
      <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
        <span>{summary.total_days_tracked} days | {summary.total_meals} meals</span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0 inline-block border-t border-dashed border-teal-500" />
          avg
        </span>
      </div>
    </div>
  );
}
