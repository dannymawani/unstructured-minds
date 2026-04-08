import { useState, useEffect, useCallback } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  X,
  Calendar,
  Trophy,
  AlertTriangle,
  Sparkles,
  PenLine,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Review {
  id: string;
  period_start: string;
  period_end: string;
  key_wins: string[];
  challenges: string[];
  work_highlights: string;
  training_summary: string;
  personal_wins: string[];
  health_metrics: Record<string, unknown> | null;
  goal_progress: Record<string, unknown> | null;
  focus_next: string[];
  created_at: string;
  updated_at: string;
}

interface ProgressReviewsProps {
  apiUrl: string;
}

function emptyReview(): Omit<Review, 'id' | 'created_at' | 'updated_at'> {
  const today = new Date().toISOString().slice(0, 10);
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);
  return {
    period_start: thirtyDaysAgo,
    period_end: today,
    key_wins: [],
    challenges: [],
    work_highlights: '',
    training_summary: '',
    personal_wins: [],
    health_metrics: null,
    goal_progress: null,
    focus_next: [],
  };
}

interface ListEditorProps {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
}

function ListEditor({ label, items, onChange }: ListEditorProps) {
  const [inputValue, setInputValue] = useState('');

  const add = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed) {
      onChange([...items, trimmed]);
      setInputValue('');
    }
  }, [inputValue, items, onChange]);

  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1.5">
        {label}
      </label>
      <div className="space-y-1">
        {items.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            <span className="flex-1 text-sm text-foreground">{item}</span>
            <button
              type="button"
              onClick={() => onChange(items.filter((_, i) => i !== index))}
              className="p-0.5 hover:text-destructive transition-colors text-muted-foreground"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                add();
              }
            }}
            placeholder={`Add ${label.toLowerCase()}...`}
            className="flex-1 bg-muted rounded-md px-2.5 py-1.5 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
          />
          <button
            type="button"
            onClick={add}
            className="p-1 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function ProgressReviews({ apiUrl }: ProgressReviewsProps) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [choosing, setChoosing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [newReview, setNewReview] = useState(emptyReview());
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/profile/reviews`);
      if (!response.ok) throw new Error('Failed to fetch reviews');
      const data = await response.json();
      setReviews(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const handleCreate = useCallback(async () => {
    setSaving(true);
    try {
      const response = await fetch(`${apiUrl}/profile/reviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newReview),
      });
      if (!response.ok) throw new Error('Failed to create review');
      const created = await response.json();
      setReviews((prev) => [created, ...prev]);
      setCreating(false);
      setNewReview(emptyReview());
      setExpandedId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create review');
    } finally {
      setSaving(false);
    }
  }, [apiUrl, newReview]);

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        const response = await fetch(`${apiUrl}/profile/reviews/${id}`, {
          method: 'DELETE',
        });
        if (!response.ok) throw new Error('Failed to delete review');
        setReviews((prev) => prev.filter((r) => r.id !== id));
        setDeleteConfirm(null);
        if (expandedId === id) setExpandedId(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete review');
      }
    },
    [apiUrl, expandedId]
  );

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setChoosing(false);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/profile/reviews/generate`, {
        method: 'POST',
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: 'Failed to generate review' }));
        throw new Error(errData.detail || 'Failed to generate review');
      }
      const data = await response.json();
      setNewReview({
        period_start: data.period_start || emptyReview().period_start,
        period_end: data.period_end || emptyReview().period_end,
        key_wins: data.key_wins || [],
        challenges: data.challenges || [],
        work_highlights: data.work_highlights || '',
        training_summary: data.training_summary || '',
        personal_wins: data.personal_wins || [],
        health_metrics: data.health_metrics || null,
        goal_progress: data.goal_progress || null,
        focus_next: data.focus_next || [],
      });
      setCreating(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate review');
    } finally {
      setGenerating(false);
    }
  }, [apiUrl]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="h-16 bg-muted rounded-md animate-pulse" />
        ))}
      </div>
    );
  }

  if (error && reviews.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-destructive text-sm">{error}</p>
        <button
          onClick={fetchReviews}
          className="mt-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Error banner */}
      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-3 py-2 rounded-md flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="p-0.5">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Create new review */}
      {creating ? (
        <div className="border border-border/50 rounded-md p-4 space-y-4">
          <h4 className="text-sm font-semibold text-foreground">New Progress Review</h4>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Period Start</label>
              <input
                type="date"
                value={newReview.period_start}
                onChange={(e) =>
                  setNewReview({ ...newReview, period_start: e.target.value })
                }
                className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Period End</label>
              <input
                type="date"
                value={newReview.period_end}
                onChange={(e) =>
                  setNewReview({ ...newReview, period_end: e.target.value })
                }
                className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
            </div>
          </div>

          <ListEditor
            label="Key Wins"
            items={newReview.key_wins}
            onChange={(key_wins) => setNewReview({ ...newReview, key_wins })}
          />

          <ListEditor
            label="Challenges"
            items={newReview.challenges}
            onChange={(challenges) => setNewReview({ ...newReview, challenges })}
          />

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              Work Highlights
            </label>
            <textarea
              value={newReview.work_highlights}
              onChange={(e) =>
                setNewReview({ ...newReview, work_highlights: e.target.value })
              }
              rows={2}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none resize-none"
              placeholder="Work highlights..."
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              Training Summary
            </label>
            <textarea
              value={newReview.training_summary}
              onChange={(e) =>
                setNewReview({ ...newReview, training_summary: e.target.value })
              }
              rows={2}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none resize-none"
              placeholder="Training summary..."
            />
          </div>

          <ListEditor
            label="Personal Wins"
            items={newReview.personal_wins}
            onChange={(personal_wins) =>
              setNewReview({ ...newReview, personal_wins })
            }
          />

          <ListEditor
            label="Focus Next"
            items={newReview.focus_next}
            onChange={(focus_next) => setNewReview({ ...newReview, focus_next })}
          />

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => {
                setCreating(false);
                setNewReview(emptyReview());
              }}
              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <Button onClick={handleCreate} disabled={saving} size="sm">
              {saving ? 'Saving...' : 'Create Review'}
            </Button>
          </div>
        </div>
      ) : generating ? (
        <div className="border border-border/50 rounded-md p-6 flex flex-col items-center gap-3">
          <Loader2 className="w-6 h-6 text-teal-500 animate-spin" />
          <p className="text-sm text-muted-foreground">Generating review...</p>
          <p className="text-xs text-muted-foreground/70">
            Analyzing your activities, exercises, metrics, and tasks
          </p>
        </div>
      ) : choosing ? (
        <div className="border border-border/50 rounded-md p-4 space-y-3">
          <h4 className="text-sm font-semibold text-foreground">New Progress Review</h4>
          <p className="text-xs text-muted-foreground">
            How would you like to create your review?
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <Button
              onClick={handleGenerate}
              size="sm"
              className="flex-1 bg-teal-600 hover:bg-teal-700 text-white"
            >
              <Sparkles className="w-4 h-4 mr-1.5" />
              Generate with AI
            </Button>
            <Button
              onClick={() => {
                setChoosing(false);
                setCreating(true);
                setNewReview(emptyReview());
              }}
              variant="outline"
              size="sm"
              className="flex-1"
            >
              <PenLine className="w-4 h-4 mr-1.5" />
              Write Manually
            </Button>
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setChoosing(false)}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <Button
          onClick={() => setChoosing(true)}
          variant="outline"
          size="sm"
          className="w-full"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          New Review
        </Button>
      )}

      {/* Reviews list */}
      {reviews.length === 0 && !creating && (
        <div className="text-center py-6 text-muted-foreground">
          <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No reviews yet</p>
          <p className="text-xs mt-1">Create your first progress review</p>
        </div>
      )}

      {reviews.map((review) => {
        const isExpanded = expandedId === review.id;
        const isDeleting = deleteConfirm === review.id;

        return (
          <div
            key={review.id}
            className="border border-border/50 rounded-md overflow-hidden"
          >
            {/* Header */}
            <button
              type="button"
              onClick={() => toggleExpand(review.id)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-2.5 text-left">
                <Calendar className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {review.period_start} to {review.period_end}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {review.key_wins.length} win{review.key_wins.length !== 1 ? 's' : ''}
                    {' / '}
                    {review.challenges.length} challenge{review.challenges.length !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
              {isExpanded ? (
                <ChevronUp className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              )}
            </button>

            {/* Expanded content */}
            {isExpanded && (
              <div className="px-4 pb-4 space-y-3 border-t border-border/30">
                {/* Key Wins */}
                {review.key_wins.length > 0 && (
                  <div className="pt-3">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Trophy className="w-3.5 h-3.5 text-green-400" />
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Key Wins
                      </span>
                    </div>
                    <ul className="space-y-1">
                      {review.key_wins.map((win, i) => (
                        <li key={i} className="text-sm text-foreground pl-5 relative before:content-[''] before:absolute before:left-1.5 before:top-2 before:w-1 before:h-1 before:rounded-full before:bg-green-400">
                          {win}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Challenges */}
                {review.challenges.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Challenges
                      </span>
                    </div>
                    <ul className="space-y-1">
                      {review.challenges.map((challenge, i) => (
                        <li key={i} className="text-sm text-foreground pl-5 relative before:content-[''] before:absolute before:left-1.5 before:top-2 before:w-1 before:h-1 before:rounded-full before:bg-amber-400">
                          {challenge}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Work Highlights */}
                {review.work_highlights && (
                  <div>
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Work Highlights
                    </span>
                    <p className="text-sm text-foreground mt-1 leading-relaxed">
                      {review.work_highlights}
                    </p>
                  </div>
                )}

                {/* Training Summary */}
                {review.training_summary && (
                  <div>
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Training Summary
                    </span>
                    <p className="text-sm text-foreground mt-1 leading-relaxed">
                      {review.training_summary}
                    </p>
                  </div>
                )}

                {/* Personal Wins */}
                {review.personal_wins.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Personal Wins
                    </span>
                    <ul className="space-y-1 mt-1">
                      {review.personal_wins.map((win, i) => (
                        <li key={i} className="text-sm text-foreground pl-5 relative before:content-[''] before:absolute before:left-1.5 before:top-2 before:w-1 before:h-1 before:rounded-full before:bg-teal-400">
                          {win}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Focus Next */}
                {review.focus_next.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Focus Next
                    </span>
                    <ul className="space-y-1 mt-1">
                      {review.focus_next.map((item, i) => (
                        <li key={i} className="text-sm text-foreground pl-5 relative before:content-[''] before:absolute before:left-1.5 before:top-2 before:w-1 before:h-1 before:rounded-full before:bg-indigo-400">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Delete */}
                <div className="pt-2 border-t border-border/30 flex justify-end">
                  {isDeleting ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Delete this review?</span>
                      <button
                        type="button"
                        onClick={() => setDeleteConfirm(null)}
                        className="px-2 py-1 text-xs text-muted-foreground hover:text-foreground rounded transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(review.id)}
                        className="px-2 py-1 text-xs bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setDeleteConfirm(review.id)}
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <Trash2 className="w-3 h-3" />
                      Delete
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
