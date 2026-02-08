import { useEffect, useState } from 'react';
import { Dumbbell, Plus, X, Loader2 } from 'lucide-react';
import { cachedFetch, clearCache } from '../../lib/cachedFetch';

interface ExerciseTableEntry {
  exercise_name: string;
  last_trained_date: string;
  last_weight_kg: number | null;
  max_weight_kg: number | null;
  total_sessions: number;
  last_reps: number | null;
  last_sets: number | null;
}

interface ExerciseTableData {
  exercises: ExerciseTableEntry[];
  total_exercises: number;
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

export function ExerciseTable({ apiUrl = 'http://localhost:8000' }: ExerciseTableProps) {
  const [data, setData] = useState<ExerciseTableData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form state
  const today = new Date().toISOString().split('T')[0];
  const [formData, setFormData] = useState({
    exercise_name: '',
    weight_kg: '',
    reps: '',
    set_number: '1',
    date: today,
  });

  const fetchData = () => {
    setLoading(true);
    cachedFetch<ExerciseTableData>(`${apiUrl}/dashboard/exercise-table`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [apiUrl]);

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

      // Clear the cache and refetch
      clearCache();
      resetForm();
      setShowForm(false);
      fetchData();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to add exercise');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
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
              {data?.total_exercises ?? 0} exercise{(data?.total_exercises ?? 0) !== 1 ? 's' : ''} tracked
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
      {!data || data.exercises.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Dumbbell className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p>No exercises tracked yet.</p>
          <p className="text-sm mt-1">Add your first exercise using the button above.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground text-left">
                <th className="pb-2 pr-4 font-medium">Exercise</th>
                <th className="pb-2 pr-4 font-medium">Last Trained</th>
                <th className="pb-2 pr-4 font-medium text-right">Recent Weight</th>
                <th className="pb-2 pr-4 font-medium text-right">Best Weight</th>
                <th className="pb-2 font-medium text-right">Sessions</th>
              </tr>
            </thead>
            <tbody>
              {data.exercises.map((exercise) => {
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
                      {exercise.last_reps !== null && exercise.last_sets !== null && (
                        <span className="text-xs text-muted-foreground ml-2">
                          {exercise.last_sets}x{exercise.last_reps}
                        </span>
                      )}
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
      )}
    </div>
  );
}
