import { useEffect, useState, useCallback } from 'react';
import { Dumbbell, Plus, X, Loader2, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { clearCache } from '../../lib/cachedFetch';

interface ExerciseTableEntry {
  exercise_name: string;
  last_trained_date: string;
  last_weight_kg: number | null;
  max_weight_kg: number | null;
  total_sessions: number;
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

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatWeight(kg: number | null): string {
  if (kg === null) return '-';
  return `${kg} kg`;
}

type SortColumn = 'total_sessions' | 'last_trained_date' | 'max_weight_kg' | 'last_weight_kg';
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
  }, [apiUrl, sortBy, sortOrder]);

  useEffect(() => {
    fetchData(search);
  }, [apiUrl, search, sortBy, sortOrder, fetchData]);

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

      clearCache();
      resetForm();
      setShowForm(false);
      fetchData(search);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to add exercise');
    } finally {
      setSubmitting(false);
    }
  };

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

      {/* Table */}
      {exercises.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Dumbbell className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p>{search ? 'No exercises match your search.' : 'No exercises tracked yet.'}</p>
          {!search && <p className="text-sm mt-1">Add your first exercise using the button above.</p>}
        </div>
      ) : (
        <>
          <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border text-muted-foreground text-left">
                  <th className="pb-2 pr-4 font-medium">Exercise</th>
                  {([
                    ['last_trained_date', 'Last Trained', ''],
                    ['last_weight_kg', 'Recent Weight', 'text-right'],
                    ['max_weight_kg', 'Best Weight', 'text-right'],
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
                  const isPR =
                    exercise.last_weight_kg !== null &&
                    exercise.max_weight_kg !== null &&
                    exercise.last_weight_kg >= exercise.max_weight_kg;

                  return (
                    <tr
                      key={exercise.exercise_name}
                      className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                    >
                      <td className="py-2.5 pr-4">
                        <span className="font-medium text-foreground">
                          {formatExerciseName(exercise.exercise_name)}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-muted-foreground">
                        {formatDate(exercise.last_trained_date)}
                      </td>
                      <td className="py-2.5 pr-4 text-right text-foreground">
                        {formatWeight(exercise.last_weight_kg)}
                        {isPR && (
                          <span className="ml-1.5 text-xs text-amber-400 font-medium">PR</span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-right text-teal-400 font-medium">
                        {formatWeight(exercise.max_weight_kg)}
                      </td>
                      <td className="py-2.5 text-right text-muted-foreground">
                        {exercise.total_sessions}
                      </td>
                    </tr>
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
