import { useEffect, useState } from 'react';
import { User } from 'lucide-react';
import { cachedFetch } from '../../lib/cachedFetch';

interface MuscleGroupEntry {
  muscle_group: string;
  sessions: number;
  total_sets: number;
  exercises: string[];
}

interface MuscleGroupsData {
  muscle_groups: MuscleGroupEntry[];
}

interface MuscleGroupMapProps {
  apiUrl?: string;
  days?: number;
}

// Map muscle group names to display labels
const MUSCLE_LABELS: Record<string, string> = {
  chest: 'Chest',
  back: 'Back',
  shoulders: 'Shoulders',
  biceps: 'Biceps',
  triceps: 'Triceps',
  forearms: 'Forearms',
  core: 'Core',
  lower_back: 'Lower Back',
  quads: 'Quads',
  hamstrings: 'Hamstrings',
  glutes: 'Glutes',
  adductors: 'Adductors',
  abductors: 'Abductors',
  rear_delts: 'Rear Delts',
  upper_back: 'Upper Back',
};

// Color intensity based on how many sets hit this muscle group
function getHeatColor(sets: number, maxSets: number): string {
  if (sets === 0) return 'rgba(100, 116, 139, 0.15)'; // untrained - dim slate
  const intensity = Math.min(sets / Math.max(maxSets, 1), 1);
  // Gradient from teal-400/30 to teal-400/90
  const alpha = 0.25 + intensity * 0.65;
  return `rgba(45, 212, 191, ${alpha})`;
}

function getStrokeColor(sets: number): string {
  if (sets === 0) return 'rgba(100, 116, 139, 0.3)';
  return 'rgba(45, 212, 191, 0.8)';
}

// ─── SVG Body Paths (front view) ─────────────────────────────────────────────
// Simplified anatomical body map in a 200x400 viewBox
// Each path represents a muscle group region

interface MuscleRegion {
  id: string;
  paths: string[];
  side: 'front' | 'back';
}

const FRONT_REGIONS: MuscleRegion[] = [
  // Shoulders (front deltoids) - left and right
  {
    id: 'shoulders',
    side: 'front',
    paths: [
      'M 58,95 Q 52,88 48,95 Q 44,102 48,110 Q 52,108 58,105 Z',
      'M 142,95 Q 148,88 152,95 Q 156,102 152,110 Q 148,108 142,105 Z',
    ],
  },
  // Chest - left and right pecs
  {
    id: 'chest',
    side: 'front',
    paths: [
      'M 68,100 Q 62,98 58,105 Q 58,120 65,128 Q 72,132 80,128 L 80,100 Q 74,98 68,100 Z',
      'M 132,100 Q 138,98 142,105 Q 142,120 135,128 Q 128,132 120,128 L 120,100 Q 126,98 132,100 Z',
    ],
  },
  // Biceps - left and right
  {
    id: 'biceps',
    side: 'front',
    paths: [
      'M 48,112 Q 44,115 42,128 Q 40,142 43,152 Q 48,150 52,142 Q 54,130 52,115 Z',
      'M 152,112 Q 156,115 158,128 Q 160,142 157,152 Q 152,150 148,142 Q 146,130 148,115 Z',
    ],
  },
  // Forearms - left and right
  {
    id: 'forearms',
    side: 'front',
    paths: [
      'M 43,154 Q 40,158 38,172 Q 36,186 37,195 Q 42,194 44,186 Q 47,172 46,158 Z',
      'M 157,154 Q 160,158 162,172 Q 164,186 163,195 Q 158,194 156,186 Q 153,172 154,158 Z',
    ],
  },
  // Core / Abs
  {
    id: 'core',
    side: 'front',
    paths: [
      'M 80,130 L 80,195 Q 85,200 100,200 Q 115,200 120,195 L 120,130 Q 110,134 100,134 Q 90,134 80,130 Z',
    ],
  },
  // Quads - left and right
  {
    id: 'quads',
    side: 'front',
    paths: [
      'M 72,202 Q 68,220 66,248 Q 65,268 68,285 Q 75,288 82,285 Q 86,268 86,248 Q 86,225 84,202 Z',
      'M 128,202 Q 132,220 134,248 Q 135,268 132,285 Q 125,288 118,285 Q 114,268 114,248 Q 114,225 116,202 Z',
    ],
  },
  // Adductors (inner thigh) - left and right
  {
    id: 'adductors',
    side: 'front',
    paths: [
      'M 86,205 Q 90,215 92,235 Q 93,250 90,260 Q 87,258 86,250 Q 86,230 86,205 Z',
      'M 114,205 Q 110,215 108,235 Q 107,250 110,260 Q 113,258 114,250 Q 114,230 114,205 Z',
    ],
  },
];

const BACK_REGIONS: MuscleRegion[] = [
  // Rear delts - left and right
  {
    id: 'rear_delts',
    side: 'back',
    paths: [
      'M 58,95 Q 52,88 48,95 Q 44,102 48,110 Q 52,108 58,105 Z',
      'M 142,95 Q 148,88 152,95 Q 156,102 152,110 Q 148,108 142,105 Z',
    ],
  },
  // Upper back / Traps
  {
    id: 'upper_back',
    side: 'back',
    paths: [
      'M 72,92 L 80,100 L 80,118 Q 75,120 68,118 Q 62,114 60,106 Z',
      'M 128,92 L 120,100 L 120,118 Q 125,120 132,118 Q 138,114 140,106 Z',
    ],
  },
  // Back (lats)
  {
    id: 'back',
    side: 'back',
    paths: [
      'M 62,108 Q 58,120 60,135 Q 62,148 68,155 Q 74,158 80,155 L 80,120 Q 70,118 62,108 Z',
      'M 138,108 Q 142,120 140,135 Q 138,148 132,155 Q 126,158 120,155 L 120,120 Q 130,118 138,108 Z',
    ],
  },
  // Lower back
  {
    id: 'lower_back',
    side: 'back',
    paths: [
      'M 80,155 L 80,195 Q 90,200 100,200 Q 110,200 120,195 L 120,155 Q 110,160 100,160 Q 90,160 80,155 Z',
    ],
  },
  // Triceps - left and right
  {
    id: 'triceps',
    side: 'back',
    paths: [
      'M 48,112 Q 44,115 42,128 Q 40,142 43,152 Q 48,150 52,142 Q 54,130 52,115 Z',
      'M 152,112 Q 156,115 158,128 Q 160,142 157,152 Q 152,150 148,142 Q 146,130 148,115 Z',
    ],
  },
  // Glutes - left and right
  {
    id: 'glutes',
    side: 'back',
    paths: [
      'M 72,196 Q 68,200 70,215 Q 73,222 82,222 Q 88,220 88,210 Q 88,202 84,196 Z',
      'M 128,196 Q 132,200 130,215 Q 127,222 118,222 Q 112,220 112,210 Q 112,202 116,196 Z',
    ],
  },
  // Hamstrings - left and right
  {
    id: 'hamstrings',
    side: 'back',
    paths: [
      'M 68,224 Q 66,245 66,265 Q 67,280 70,288 Q 77,290 82,287 Q 86,275 86,255 Q 86,235 84,224 Z',
      'M 132,224 Q 134,245 134,265 Q 133,280 130,288 Q 123,290 118,287 Q 114,275 114,255 Q 114,235 116,224 Z',
    ],
  },
  // Abductors (outer hip/thigh)
  {
    id: 'abductors',
    side: 'back',
    paths: [
      'M 68,200 Q 64,210 63,225 Q 62,235 64,240 Q 67,238 68,230 Q 69,218 70,205 Z',
      'M 132,200 Q 136,210 137,225 Q 138,235 136,240 Q 133,238 132,230 Q 131,218 130,205 Z',
    ],
  },
];

// Simpler body outline
const HEAD = 'M 100,18 Q 86,18 83,32 Q 80,46 83,58 Q 86,68 92,74 Q 96,78 100,80 Q 104,78 108,74 Q 114,68 117,58 Q 120,46 117,32 Q 114,18 100,18 Z';
const NECK = 'M 90,78 L 90,92 Q 95,94 100,94 Q 105,94 110,92 L 110,78 Q 105,82 100,82 Q 95,82 90,78 Z';

// Legs below knees (calves/shins - not a tracked muscle group, just for silhouette)
const LOWER_LEGS = [
  'M 68,288 Q 66,305 64,320 Q 62,340 64,355 Q 66,365 68,370 Q 72,374 76,372 Q 78,368 78,360 Q 78,345 80,330 Q 82,315 82,300 Q 82,292 80,288 Z',
  'M 132,288 Q 134,305 136,320 Q 138,340 136,355 Q 134,365 132,370 Q 128,374 124,372 Q 122,368 122,360 Q 122,345 120,330 Q 118,315 118,300 Q 118,292 120,288 Z',
];

export function MuscleGroupMap({ apiUrl = 'http://localhost:8000', days = 7 }: MuscleGroupMapProps) {
  const [data, setData] = useState<MuscleGroupsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [view, setView] = useState<'front' | 'back'>('front');

  useEffect(() => {
    setLoading(true);
    cachedFetch<MuscleGroupsData>(
      `${apiUrl}/dashboard/muscle-groups?days=${days}`
    )
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, [apiUrl, days]);

  if (loading) {
    return <div className="bg-card rounded-md shadow-sm p-4 h-96 animate-pulse" />;
  }

  if (error) {
    return (
      <div className="text-red-400 p-4">Error: {error}</div>
    );
  }

  // Build lookup: muscle_group -> entry
  const muscleMap = new Map<string, MuscleGroupEntry>();
  if (data) {
    for (const entry of data.muscle_groups) {
      muscleMap.set(entry.muscle_group, entry);
    }
  }

  const maxSets = data
    ? Math.max(...data.muscle_groups.map((m) => m.total_sets), 1)
    : 1;

  const regions = view === 'front' ? FRONT_REGIONS : BACK_REGIONS;
  const hoveredEntry = hovered ? muscleMap.get(hovered) : null;

  // Count trained muscle groups
  const trainedCount = data?.muscle_groups.length ?? 0;
  const allGroups = new Set([
    ...FRONT_REGIONS.map((r) => r.id),
    ...BACK_REGIONS.map((r) => r.id),
  ]);
  const totalGroups = allGroups.size;

  return (
    <div className="bg-card rounded-md shadow-sm p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-teal-500/20 rounded-lg">
            <User className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Muscle Groups</h3>
            <p className="text-sm text-muted-foreground">
              {trainedCount}/{totalGroups} groups trained · last {days} days
            </p>
          </div>
        </div>

        {/* Front/Back toggle */}
        <div className="flex bg-secondary rounded-lg p-1">
          <button
            className={`px-3 py-1 text-xs rounded transition-colors ${
              view === 'front'
                ? 'bg-teal-500 text-white'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setView('front')}
          >
            Front
          </button>
          <button
            className={`px-3 py-1 text-xs rounded transition-colors ${
              view === 'back'
                ? 'bg-teal-500 text-white'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setView('back')}
          >
            Back
          </button>
        </div>
      </div>

      {/* Body + Legend layout */}
      <div className="flex gap-4">
        {/* SVG Body */}
        <div className="flex-1 flex justify-center">
          <svg
            viewBox="0 0 200 390"
            className="w-full max-w-[220px] h-auto"
            style={{ maxHeight: '420px' }}
          >
            {/* Head */}
            <path
              d={HEAD}
              fill="rgba(100, 116, 139, 0.1)"
              stroke="rgba(100, 116, 139, 0.3)"
              strokeWidth="0.8"
            />
            {/* Neck */}
            <path
              d={NECK}
              fill="rgba(100, 116, 139, 0.1)"
              stroke="rgba(100, 116, 139, 0.3)"
              strokeWidth="0.8"
            />

            {/* Muscle group regions */}
            {regions.map((region) => {
              const entry = muscleMap.get(region.id);
              const sets = entry?.total_sets ?? 0;
              const isHovered = hovered === region.id;
              const fill = getHeatColor(sets, maxSets);
              const stroke = getStrokeColor(sets);

              return region.paths.map((path, i) => (
                <path
                  key={`${region.id}-${i}`}
                  d={path}
                  fill={fill}
                  stroke={isHovered ? 'rgba(45, 212, 191, 1)' : stroke}
                  strokeWidth={isHovered ? '2' : '0.8'}
                  style={{ cursor: 'pointer', transition: 'all 0.15s ease' }}
                  onMouseEnter={() => setHovered(region.id)}
                  onMouseLeave={() => setHovered(null)}
                />
              ));
            })}

            {/* Lower legs (untracked, just silhouette) */}
            {LOWER_LEGS.map((path, i) => (
              <path
                key={`leg-${i}`}
                d={path}
                fill="rgba(100, 116, 139, 0.08)"
                stroke="rgba(100, 116, 139, 0.25)"
                strokeWidth="0.8"
              />
            ))}
          </svg>
        </div>

        {/* Legend / Details panel */}
        <div className="w-40 flex flex-col gap-1 text-xs overflow-y-auto max-h-[400px]">
          {hoveredEntry ? (
            // Detailed view on hover
            <div className="space-y-2">
              <div className="font-medium text-foreground text-sm">
                {MUSCLE_LABELS[hoveredEntry.muscle_group] ?? hoveredEntry.muscle_group}
              </div>
              <div className="text-muted-foreground">
                {hoveredEntry.sessions} session{hoveredEntry.sessions !== 1 ? 's' : ''} · {hoveredEntry.total_sets} sets
              </div>
              <div className="space-y-1 pt-1 border-t border-border">
                <div className="text-muted-foreground font-medium">Exercises:</div>
                {hoveredEntry.exercises.map((ex) => (
                  <div key={ex} className="text-foreground">{ex}</div>
                ))}
              </div>
            </div>
          ) : (
            // Default: show all muscle groups as mini legend
            <>
              {[...allGroups].map((groupId) => {
                const entry = muscleMap.get(groupId);
                const sets = entry?.total_sets ?? 0;
                return (
                  <div
                    key={groupId}
                    className="flex items-center gap-2 py-0.5 cursor-pointer rounded px-1 hover:bg-secondary/50"
                    onMouseEnter={() => setHovered(groupId)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <div
                      className="w-3 h-3 rounded-sm flex-shrink-0"
                      style={{ backgroundColor: getHeatColor(sets, maxSets), border: `1px solid ${getStrokeColor(sets)}` }}
                    />
                    <span className={sets > 0 ? 'text-foreground' : 'text-muted-foreground'}>
                      {MUSCLE_LABELS[groupId] ?? groupId}
                    </span>
                    {sets > 0 && (
                      <span className="text-teal-400 ml-auto">{sets}</span>
                    )}
                  </div>
                );
              })}
            </>
          )}
        </div>
      </div>

      {/* Intensity scale */}
      <div className="flex items-center justify-center gap-2 mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
        <span>Less</span>
        <div className="flex gap-0.5">
          {[0, 0.2, 0.4, 0.6, 0.8, 1].map((intensity) => (
            <div
              key={intensity}
              className="w-4 h-4 rounded-sm"
              style={{
                backgroundColor: intensity === 0
                  ? 'rgba(100, 116, 139, 0.15)'
                  : `rgba(45, 212, 191, ${0.25 + intensity * 0.65})`,
              }}
            />
          ))}
        </div>
        <span>More</span>
      </div>
    </div>
  );
}
