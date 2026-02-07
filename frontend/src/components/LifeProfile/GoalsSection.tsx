import { useState, useCallback, useMemo } from 'react';
import { Plus, Pencil, Check, X, Trash2 } from 'lucide-react';

interface Goal {
  id: string;
  category: string;
  description: string;
  status: string;
  target_date: string | null;
  progress: number | null;
}

interface GoalsSectionProps {
  goals: Goal[];
  onSave: (goals: Goal[]) => void;
}

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-teal-500/10 text-teal-400',
  completed: 'bg-green-500/10 text-green-400',
  paused: 'bg-amber-500/10 text-amber-400',
};

const STATUS_OPTIONS = ['active', 'completed', 'paused'];

function generateId(): string {
  return `goal_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function emptyGoal(): Goal {
  return {
    id: generateId(),
    category: '',
    description: '',
    status: 'active',
    target_date: null,
    progress: null,
  };
}

export function GoalsSection({ goals, onSave }: GoalsSectionProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Goal[]>(goals);
  const [adding, setAdding] = useState(false);
  const [newGoal, setNewGoal] = useState<Goal>(emptyGoal());

  const startEditing = useCallback(() => {
    setDraft(goals);
    setEditing(true);
  }, [goals]);

  const save = useCallback(() => {
    onSave(draft);
    setEditing(false);
    setAdding(false);
  }, [draft, onSave]);

  const addGoal = useCallback(() => {
    if (newGoal.description.trim() && newGoal.category.trim()) {
      setDraft((prev) => [...prev, { ...newGoal, id: generateId() }]);
      setNewGoal(emptyGoal());
      setAdding(false);
    }
  }, [newGoal]);

  const removeGoal = useCallback((id: string) => {
    setDraft((prev) => prev.filter((g) => g.id !== id));
  }, []);

  const updateGoal = useCallback((id: string, updates: Partial<Goal>) => {
    setDraft((prev) =>
      prev.map((g) => (g.id === id ? { ...g, ...updates } : g))
    );
  }, []);

  const displayGoals = editing ? draft : goals;

  const grouped = useMemo(() => {
    const groups: Record<string, Goal[]> = {};
    for (const goal of displayGoals) {
      const cat = goal.category || 'Uncategorized';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(goal);
    }
    return groups;
  }, [displayGoals]);

  const categories = Object.keys(grouped).sort();

  return (
    <div className="group relative">
      {!editing && (
        <button
          type="button"
          onClick={startEditing}
          className="absolute top-0 right-0 p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
          aria-label="Edit goals"
          title="Edit"
        >
          <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
      )}

      <div className="space-y-4">
        {categories.length === 0 && !editing && (
          <div className="text-center py-6 text-muted-foreground">
            <p className="text-sm">No goals yet</p>
            <p className="text-xs mt-1">Click the edit button to add goals</p>
          </div>
        )}

        {categories.map((category) => (
          <div key={category}>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
              {category}
            </h4>
            <div className="space-y-2">
              {grouped[category].map((goal) => (
                <div
                  key={goal.id}
                  className="flex items-start gap-3 bg-muted/50 rounded-md px-3 py-2.5"
                >
                  <div className="flex-1 min-w-0">
                    {editing ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={goal.description}
                          onChange={(e) =>
                            updateGoal(goal.id, { description: e.target.value })
                          }
                          className="w-full bg-muted rounded-md px-2 py-1 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
                          placeholder="Goal description"
                        />
                        <div className="flex items-center gap-2 flex-wrap">
                          <select
                            value={goal.status}
                            onChange={(e) =>
                              updateGoal(goal.id, { status: e.target.value })
                            }
                            className="bg-muted rounded-md px-2 py-1 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
                          >
                            {STATUS_OPTIONS.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                          <input
                            type="text"
                            value={goal.category}
                            onChange={(e) =>
                              updateGoal(goal.id, { category: e.target.value })
                            }
                            className="w-24 bg-muted rounded-md px-2 py-1 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
                            placeholder="Category"
                          />
                          <input
                            type="date"
                            value={goal.target_date || ''}
                            onChange={(e) =>
                              updateGoal(goal.id, {
                                target_date: e.target.value || null,
                              })
                            }
                            className="bg-muted rounded-md px-2 py-1 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
                          />
                          <input
                            type="number"
                            value={goal.progress ?? ''}
                            onChange={(e) =>
                              updateGoal(goal.id, {
                                progress: e.target.value
                                  ? Math.min(100, Math.max(0, Number(e.target.value)))
                                  : null,
                              })
                            }
                            placeholder="%"
                            min={0}
                            max={100}
                            className="w-16 bg-muted rounded-md px-2 py-1 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
                          />
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-2">
                          <p className="text-sm text-foreground">{goal.description}</p>
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wide ${
                              STATUS_STYLES[goal.status] || STATUS_STYLES.active
                            }`}
                          >
                            {goal.status}
                          </span>
                        </div>
                        {goal.target_date && (
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Target: {goal.target_date}
                          </p>
                        )}
                        {goal.progress != null && (
                          <div className="mt-1.5 flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-teal-500 rounded-full transition-all"
                                style={{ width: `${goal.progress}%` }}
                              />
                            </div>
                            <span className="text-[10px] text-muted-foreground font-medium">
                              {goal.progress}%
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                  {editing && (
                    <button
                      type="button"
                      onClick={() => removeGoal(goal.id)}
                      className="p-1 hover:text-destructive transition-colors text-muted-foreground flex-shrink-0 mt-0.5"
                      aria-label="Remove goal"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Add new goal form */}
        {editing && adding && (
          <div className="border border-border/50 rounded-md p-3 space-y-2">
            <input
              type="text"
              value={newGoal.description}
              onChange={(e) => setNewGoal({ ...newGoal, description: e.target.value })}
              placeholder="Goal description"
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') { e.preventDefault(); addGoal(); }
                if (e.key === 'Escape') setAdding(false);
              }}
            />
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="text"
                value={newGoal.category}
                onChange={(e) => setNewGoal({ ...newGoal, category: e.target.value })}
                placeholder="Category"
                className="w-28 bg-muted rounded-md px-2 py-1.5 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
              <select
                value={newGoal.status}
                onChange={(e) => setNewGoal({ ...newGoal, status: e.target.value })}
                className="bg-muted rounded-md px-2 py-1.5 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <input
                type="date"
                value={newGoal.target_date || ''}
                onChange={(e) => setNewGoal({ ...newGoal, target_date: e.target.value || null })}
                className="bg-muted rounded-md px-2 py-1.5 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
              <div className="flex items-center gap-1 ml-auto">
                <button
                  type="button"
                  onClick={() => setAdding(false)}
                  className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground"
                >
                  <X className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={addGoal}
                  className="p-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  <Check className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {editing && !adding && (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add goal
          </button>
        )}

        {editing && (
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => { setEditing(false); setAdding(false); }}
              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={save}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              Save
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
