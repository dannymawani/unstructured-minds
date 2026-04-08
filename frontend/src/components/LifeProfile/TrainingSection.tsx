import { useState, useCallback } from 'react';
import { X, Plus, Pencil, Check, Trash2 } from 'lucide-react';

interface TrainingData {
  disciplines: string[];
  current_lifts: Record<string, string>;
  recovery: string;
  goals: string[];
  notes: string;
}

interface TrainingSectionProps {
  data: TrainingData;
  onSave: (data: TrainingData) => void;
}

export function TrainingSection({ data, onSave }: TrainingSectionProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<TrainingData>(data);
  const [newDiscipline, setNewDiscipline] = useState('');
  const [newGoal, setNewGoal] = useState('');
  const [newLiftName, setNewLiftName] = useState('');
  const [newLiftValue, setNewLiftValue] = useState('');

  const startEditing = useCallback(() => {
    setDraft(data);
    setEditing(true);
  }, [data]);

  const save = useCallback(() => {
    onSave(draft);
    setEditing(false);
  }, [draft, onSave]);

  const addDiscipline = useCallback(() => {
    const trimmed = newDiscipline.trim();
    if (trimmed && !draft.disciplines.includes(trimmed)) {
      setDraft((prev) => ({ ...prev, disciplines: [...prev.disciplines, trimmed] }));
      setNewDiscipline('');
    }
  }, [newDiscipline, draft.disciplines]);

  const removeDiscipline = useCallback((index: number) => {
    setDraft((prev) => ({
      ...prev,
      disciplines: prev.disciplines.filter((_, i) => i !== index),
    }));
  }, []);

  const addGoal = useCallback(() => {
    const trimmed = newGoal.trim();
    if (trimmed && !draft.goals.includes(trimmed)) {
      setDraft((prev) => ({ ...prev, goals: [...prev.goals, trimmed] }));
      setNewGoal('');
    }
  }, [newGoal, draft.goals]);

  const removeGoal = useCallback((index: number) => {
    setDraft((prev) => ({
      ...prev,
      goals: prev.goals.filter((_, i) => i !== index),
    }));
  }, []);

  const addLift = useCallback(() => {
    const name = newLiftName.trim();
    const value = newLiftValue.trim();
    if (name && value) {
      setDraft((prev) => ({
        ...prev,
        current_lifts: { ...prev.current_lifts, [name]: value },
      }));
      setNewLiftName('');
      setNewLiftValue('');
    }
  }, [newLiftName, newLiftValue]);

  const removeLift = useCallback((key: string) => {
    setDraft((prev) => {
      const lifts = { ...prev.current_lifts };
      delete lifts[key];
      return { ...prev, current_lifts: lifts };
    });
  }, []);

  const updateLiftValue = useCallback((key: string, value: string) => {
    setDraft((prev) => ({
      ...prev,
      current_lifts: { ...prev.current_lifts, [key]: value },
    }));
  }, []);

  const displayData = editing ? draft : data;
  const liftEntries = Object.entries(displayData.current_lifts);

  return (
    <div className="group relative">
      {!editing && (
        <button
          type="button"
          onClick={startEditing}
          className="absolute top-0 right-0 p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
          aria-label="Edit training"
          title="Edit"
        >
          <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
      )}

      <div className="space-y-4">
        {/* Disciplines */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
            Disciplines
          </label>
          <div className="flex flex-wrap gap-1.5">
            {displayData.disciplines.map((item, index) => (
              <span
                key={`${item}-${index}`}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-teal-500/10 text-teal-400"
              >
                {item}
                {editing && (
                  <button
                    type="button"
                    onClick={() => removeDiscipline(index)}
                    className="ml-0.5 hover:text-destructive transition-colors"
                    aria-label={`Remove ${item}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            ))}
            {editing && (
              <div className="inline-flex items-center gap-1">
                <input
                  type="text"
                  value={newDiscipline}
                  onChange={(e) => setNewDiscipline(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addDiscipline(); } }}
                  placeholder="Add discipline..."
                  className="w-28 bg-muted rounded-full px-2.5 py-1 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
                />
                <button
                  type="button"
                  onClick={addDiscipline}
                  className="p-1 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                >
                  <Plus className="w-3 h-3" />
                </button>
              </div>
            )}
            {!editing && displayData.disciplines.length === 0 && (
              <span className="text-xs text-muted-foreground italic">None added</span>
            )}
          </div>
        </div>

        {/* Current Lifts */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
            Current Lifts
          </label>
          {liftEntries.length > 0 ? (
            <div className="space-y-1.5">
              {liftEntries.map(([exercise, weight]) => (
                <div
                  key={exercise}
                  className="flex items-center justify-between bg-muted/50 rounded-md px-3 py-2"
                >
                  <span className="text-sm text-foreground font-medium">{exercise}</span>
                  {editing ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={weight}
                        onChange={(e) => updateLiftValue(exercise, e.target.value)}
                        className="w-24 bg-muted rounded-md px-2 py-1 text-sm text-foreground text-right border-none focus:ring-2 focus:ring-ring outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => removeLift(exercise)}
                        className="p-1 hover:text-destructive transition-colors text-muted-foreground"
                        aria-label={`Remove ${exercise}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">{weight}</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            !editing && (
              <span className="text-xs text-muted-foreground italic">No lifts recorded</span>
            )
          )}
          {editing && (
            <div className="flex items-center gap-2 mt-2">
              <input
                type="text"
                value={newLiftName}
                onChange={(e) => setNewLiftName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addLift(); } }}
                placeholder="Exercise name"
                className="flex-1 bg-muted rounded-md px-3 py-1.5 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
              <input
                type="text"
                value={newLiftValue}
                onChange={(e) => setNewLiftValue(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addLift(); } }}
                placeholder="Weight / PR"
                className="w-28 bg-muted rounded-md px-3 py-1.5 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
              <button
                type="button"
                onClick={addLift}
                className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                aria-label="Add lift"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Recovery */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
            Recovery
          </label>
          {editing ? (
            <input
              type="text"
              value={draft.recovery}
              onChange={(e) => setDraft({ ...draft, recovery: e.target.value })}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              placeholder="Recovery approach..."
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              {data.recovery || <span className="italic">Not specified</span>}
            </p>
          )}
        </div>

        {/* Training Goals */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
            Training Goals
          </label>
          <div className="flex flex-wrap gap-1.5">
            {displayData.goals.map((goal, index) => (
              <span
                key={`${goal}-${index}`}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400"
              >
                {goal}
                {editing && (
                  <button
                    type="button"
                    onClick={() => removeGoal(index)}
                    className="ml-0.5 hover:text-destructive transition-colors"
                    aria-label={`Remove ${goal}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            ))}
            {editing && (
              <div className="inline-flex items-center gap-1">
                <input
                  type="text"
                  value={newGoal}
                  onChange={(e) => setNewGoal(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addGoal(); } }}
                  placeholder="Add goal..."
                  className="w-28 bg-muted rounded-full px-2.5 py-1 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
                />
                <button
                  type="button"
                  onClick={addGoal}
                  className="p-1 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                >
                  <Plus className="w-3 h-3" />
                </button>
              </div>
            )}
            {!editing && displayData.goals.length === 0 && (
              <span className="text-xs text-muted-foreground italic">None added</span>
            )}
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
            Notes
          </label>
          {editing ? (
            <textarea
              value={draft.notes}
              onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
              rows={3}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none resize-none"
              placeholder="Training notes..."
            />
          ) : (
            <p className="text-sm text-muted-foreground leading-relaxed">
              {data.notes || <span className="italic">No notes</span>}
            </p>
          )}
        </div>

        {editing && (
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setEditing(false)}
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
