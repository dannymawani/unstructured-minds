import { useEffect, useState, useCallback } from 'react';
import { Dumbbell, Plus, X, Loader2, Search, ChevronDown, ChevronUp, Share2, Check, TrendingUp, TrendingDown, Minus, ChevronRight } from 'lucide-react';
import { clearCache } from '../../lib/cachedFetch';

interface SetDetail {
  weight_kg: number | null;
  reps: number | null;
  set_number: number;
}

interface ExerciseTableEntry {
  exercise_name: string;
  last_trained_date: string;
  last_weight_kg: number | null;
  max_weight_kg: number | null;
  total_sessions: number;
  total_sets: number;
  is_pr: boolean;
  trend: 'up' | 'down' | 'flat' | 'insufficient';
  muscle_groups: string[];
  last_session_sets: SetDetail[];
}

interface ExerciseTableData {
  exercises: ExerciseTableEntry[];
  total_count: number;
  offset: number;
  limit: number;
}

interface ExerciseTableProps {
  apiUrl?: string;
}

function formatExerciseName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatRelativeDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks}w ago`;
  }
  if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    return `${months}mo ago`;
  }
  return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

function formatWeight(kg: number | null): string {
  if (kg === null) return '-';
  return `${kg} kg`;
}

function formatMuscleGroup(mg: string): string {
  return mg
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function TrendIcon({ trend }: { trend: ExerciseTableEntry['trend'] }) {
  switch (trend) {
    case 'up':
      return <TrendingUp className="w-3.5 h-3.5 text-green-400" />;
    case 'down':
      return <TrendingDown className="w-3.5 h-3.5 text-red-400" />;
    case 'flat':
      return <Minus className="w-3.5 h-3.5 text-muted-foreground" />;
    default:
      return null;
  }
}

// All muscle groups that can appear
const ALL_MUSCLE_GROUPS = [
  'chest', 'back', 'shoulders', 'biceps', 'triceps', 'forearms',
  'core', 'lower_back', 'upper_back', 'rear_delts',
  'quads', 'hamstrings', 'glutes', 'adductors', 'abductors',
];

type SortColumn = 'total_sessions' | 'last_trained_date' | 'max_weight_kg' | 'last_weight_kg' | 'total_sets';
type SortOrder = 'asc' | 'desc';

const PAGE_SIZE = 10;

export function ExerciseTable({ apiUrl = 'http://localhost:8000' }: ExerciseTableProps) {
  const [exercises, setExercises] = useState<ExerciseTableEntry[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [sortBy, setSortBy] = useState<SortColumn>('total_sessions');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [muscleFilter, setMuscleFilter] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  // Community share prompt state
  const [sharePrompt, setSharePrompt] = useState<{ name: string } | null>(null);
  const [sharing, setSharing] = useState(false);
  const [shareResult, setShareResult] = useState<string | null>(null);

  // Form state
  const today = new Date().toISOString().split('T')[0];
  const [formData, setFormData] = useState({
    exercise_name: '',
    weight_kg: '',
    reps: '',
    set_number: '1',
    date: today,
  });

  const fetchData = useCallback(async (searchTerm: string, offset = 0, append = false) => {
    if (!append) setLoading(true);
    else setLoadingMore(true);

    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (searchTerm) params.set('search', searchTerm);
      if (muscleFilter) params.set('muscle_group', muscleFilter);

      const response = await fetch(`${apiUrl}/dashboard/exercise-table?${params}`);
      if (!response.ok) throw new Error('Failed to fetch exercises');
      const result: ExerciseTableData = await response.json();

      if (append) {
        setExercises((prev) => [...prev, ...result.exercises]);
      } else {
        setExercises(result.exercises);
      }
      setTotalCount(result.total_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [apiUrl, sortBy, sortOrder, muscleFilter]);

  useEffect(() => {
    fetchData(search);
  }, [apiUrl, search, sortBy, sortOrder, muscleFilter, fetchData]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const handleSort = (column: SortColumn) => {
    if (column === sortBy) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const loadMore = () => {
    fetchData(search, exercises.length, true);
  };

  const resetForm = () => {
    setFormData({
      exercise_name: '',
      weight_kg: '',
      reps: '',
      set_number: '1',
      date: today,
    });
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.exercise_name.trim()) {
      setFormError('Exercise name is required');
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const body: Record<string, unknown> = {
        exercise_name: formData.exercise_name.trim(),
        date: formData.date,
        set_number: parseInt(formData.set_number) || 1,
      };
      if (formData.weight_kg) body.weight_kg = parseFloat(formData.weight_kg);
      if (formData.reps) body.reps = parseInt(formData.reps);

      const response = await fetch(`${apiUrl}/dashboard/exercises`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to add exercise (${response.status})`);
      }

      const result = await response.json();

      clearCache();
      resetForm();
      setShowForm(false);
      fetchData(search);

      // Show community share prompt for new (unmatched) exercises
      if (result.is_new && result.canonical_name) {
        setSharePrompt({ name: result.canonical_name });
        setShareResult(null);
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to add exercise');
    } finally {
      setSubmitting(false);
    }
  };

  const handleShare = async () => {
    if (!sharePrompt) return;
    setSharing(true);
    try {
      const response = await fetch(`${apiUrl}/exercises/community`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sharePrompt.name }),
      });
      if (response.ok) {
        const data = await response.json();
        setShareResult(data.message);
      } else {
        setShareResult('Failed to share exercise');
      }
    } catch {
      setShareResult('Failed to share exercise');
    } finally {
      setSharing(false);
      setTimeout(() => {
        setSharePrompt(null);
        setShareResult(null);
      }, 3000);
    }
  };

  // Collect active muscle groups from current exercises for filter chips
  const activeMuscleGroups = new Set<string>();
  for (const ex of exercises) {
    for (const mg of ex.muscle_groups) {
      activeMuscleGroups.add(mg);
    }
  }
  const filterGroups = ALL_MUSCLE_GROUPS.filter(mg => activeMuscleGroups.has(mg) || mg === muscleFilter);

  if (loading && exercises.length === 0) {
    return (
      <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="exercise-table-loading" />
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4" data-testid="exercise-table-error">
        Error: {error}
      </div>
    );
  }

  const hasMore = exercises.length < totalCount;

  return (
    <div className="bg-card rounded-md shadow-sm p-3 sm:p-4" data-testid="exercise-table">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 mb-3 sm:mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-teal-500/20 rounded-lg">
            <Dumbbell className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-foreground">Track Exercises</h3>
            <p className="text-sm text-muted-foreground">
              {totalCount} strength exercise{totalCount !== 1 ? 's' : ''} tracked
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            setShowForm(!showForm);
            if (showForm) resetForm();
          }}
          className="flex items-center gap-1.5 bg-teal-500 hover:bg-teal-600 text-white text-sm px-3 py-2 rounded-lg transition-colors min-h-[40px] sm:min-h-0"
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancel' : 'Add Exercise'}
        </button>
      </div>

      {/* Search bar */}
      <div className="relative mb-3">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search exercises..."
          className="w-full bg-muted text-foreground rounded-lg pl-9 pr-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* Muscle group filter chips */}
      {filterGroups.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          <button
            onClick={() => setMuscleFilter(null)}
            className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
              !muscleFilter
                ? 'bg-teal-500 text-white'
                : 'bg-secondary text-muted-foreground hover:text-foreground'
            }`}
          >
            All
          </button>
          {filterGroups.map((mg) => (
            <button
              key={mg}
              onClick={() => setMuscleFilter(muscleFilter === mg ? null : mg)}
              className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                muscleFilter === mg
                  ? 'bg-teal-500 text-white'
                  : 'bg-secondary text-muted-foreground hover:text-foreground'
              }`}
            >
              {formatMuscleGroup(mg)}
            </button>
          ))}
        </div>
      )}

      {/* Inline Add Form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="mb-4 p-3 bg-secondary/50 rounded-lg border border-border"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Exercise Name *</label>
              <input
                type="text"
                value={formData.exercise_name}
                onChange={(e) => setFormData({ ...formData, exercise_name: e.target.value })}
                placeholder="e.g. squat"
                className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Weight (kg)</label>
              <input
                type="number"
                step="0.5"
                min="0"
                value={formData.weight_kg}
                onChange={(e) => setFormData({ ...formData, weight_kg: e.target.value })}
                placeholder="Optional"
                className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Reps</label>
              <input
                type="number"
                min="1"
                value={formData.reps}
                onChange={(e) => setFormData({ ...formData, reps: e.target.value })}
                placeholder="Optional"
                className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Sets</label>
              <input
                type="number"
                min="1"
                value={formData.set_number}
                onChange={(e) => setFormData({ ...formData, set_number: e.target.value })}
                className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Date</label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
          {formError && (
            <p className="text-red-400 text-xs mt-2">{formError}</p>
          )}
          <div className="flex justify-end mt-3">
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-1.5 bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {submitting ? 'Adding...' : 'Add'}
            </button>
          </div>
        </form>
      )}

      {/* Community share prompt */}
      {sharePrompt && (
        <div className="mb-4 p-3 bg-teal-500/10 border border-teal-500/30 rounded-lg flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm">
            <Share2 className="w-4 h-4 text-teal-400 shrink-0" />
            <span className="text-foreground">
              {shareResult ? (
                <span className="flex items-center gap-1.5">
                  <Check className="w-4 h-4 text-teal-400" />
                  {shareResult}
                </span>
              ) : (
                <>
                  <strong>{sharePrompt.name}</strong> is a new exercise. Share it with the community?
                </>
              )}
            </span>
          </div>
          {!shareResult && (
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setSharePrompt(null)}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1"
              >
                No thanks
              </button>
              <button
                onClick={handleShare}
                disabled={sharing}
                className="flex items-center gap-1.5 bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-md transition-colors"
              >
                {sharing && <Loader2 className="w-3 h-3 animate-spin" />}
                {sharing ? 'Sharing...' : 'Share'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Table */}
      {exercises.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Dumbbell className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p>{search || muscleFilter ? 'No exercises match your filters.' : 'No exercises tracked yet.'}</p>
          {!search && !muscleFilter && <p className="text-sm mt-1">Add your first exercise using the button above.</p>}
        </div>
      ) : (
        <>
          <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border text-muted-foreground text-left">
                  <th className="pb-2 pr-4 font-medium w-5"></th>
                  <th className="pb-2 pr-4 font-medium">Exercise</th>
                  {([
                    ['last_trained_date', 'Last Trained', ''],
                    ['last_weight_kg', 'Recent', 'text-right'],
                    ['max_weight_kg', 'Best', 'text-right'],
                    ['total_sets', 'Sets', 'text-right'],
                    ['total_sessions', 'Sessions', 'text-right'],
                  ] as [SortColumn, string, string][]).map(([col, label, align]) => (
                    <th
                      key={col}
                      className={`pb-2 pr-4 font-medium ${align} cursor-pointer select-none hover:text-foreground transition-colors`}
                      onClick={() => handleSort(col)}
                    >
                      <span className={`inline-flex items-center gap-0.5 ${align === 'text-right' ? 'justify-end' : ''}`}>
                        {label}
                        {sortBy === col && (
                          sortOrder === 'desc'
                            ? <ChevronDown className="w-3.5 h-3.5" />
                            : <ChevronUp className="w-3.5 h-3.5" />
                        )}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {exercises.map((exercise) => {
                  const isExpanded = expandedRow === exercise.exercise_name;
                  const hasSets = exercise.last_session_sets.length > 0;

                  return (
                    <>
                      <tr
                        key={exercise.exercise_name}
                        className={`border-b border-border/50 transition-colors ${
                          hasSets ? 'cursor-pointer hover:bg-secondary/30' : 'hover:bg-secondary/30'
                        } ${isExpanded ? 'bg-secondary/20' : ''}`}
                        onClick={() => hasSets && setExpandedRow(isExpanded ? null : exercise.exercise_name)}
                      >
                        <td className="py-2.5 pr-1 w-5">
                          {hasSets && (
                            <ChevronRight className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                          )}
                        </td>
                        <td className="py-2.5 pr-4">
                          <div>
                            <span className="font-medium text-foreground">
                              {formatExerciseName(exercise.exercise_name)}
                            </span>
                            <span className="ml-1.5 inline-flex items-center gap-1">
                              <TrendIcon trend={exercise.trend} />
                              {exercise.is_pr && (
                                <span className="text-xs text-amber-400 font-medium">PR</span>
                              )}
                            </span>
                          </div>
                          {exercise.muscle_groups.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-0.5">
                              {exercise.muscle_groups.map((mg) => (
                                <span
                                  key={mg}
                                  className="text-[10px] px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-400"
                                >
                                  {formatMuscleGroup(mg)}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 pr-4 text-muted-foreground">
                          {formatRelativeDate(exercise.last_trained_date)}
                        </td>
                        <td className="py-2.5 pr-4 text-right text-foreground">
                          {formatWeight(exercise.last_weight_kg)}
                        </td>
                        <td className="py-2.5 pr-4 text-right text-teal-400 font-medium">
                          {formatWeight(exercise.max_weight_kg)}
                        </td>
                        <td className="py-2.5 pr-4 text-right text-muted-foreground">
                          {exercise.total_sets}
                        </td>
                        <td className="py-2.5 text-right text-muted-foreground">
                          {exercise.total_sessions}
                        </td>
                      </tr>
                      {/* Expanded row: last session sets */}
                      {isExpanded && hasSets && (
                        <tr key={`${exercise.exercise_name}-sets`} className="bg-secondary/10">
                          <td colSpan={8} className="px-4 py-2">
                            <div className="text-xs text-muted-foreground mb-1.5">
                              Last session ({exercise.last_trained_date})
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {exercise.last_session_sets.map((set, i) => (
                                <div
                                  key={i}
                                  className="bg-card px-2.5 py-1.5 rounded text-xs border border-border/50"
                                >
                                  <span className="text-muted-foreground">Set {set.set_number}</span>
                                  {set.weight_kg !== null && (
                                    <span className="text-foreground ml-1.5">{set.weight_kg} kg</span>
                                  )}
                                  {set.reps !== null && (
                                    <span className="text-muted-foreground ml-1">x{set.reps}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Load more */}
          {hasMore && (
            <div className="flex justify-center mt-3">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors px-4 py-2"
              >
                {loadingMore ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
                {loadingMore ? 'Loading...' : `Show more (${exercises.length} of ${totalCount})`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
