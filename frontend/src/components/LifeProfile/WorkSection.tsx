import { useState, useCallback } from 'react';
import { X, Plus, Pencil, Check } from 'lucide-react';

interface WorkData {
  role: string;
  company: string;
  projects: string[];
  colleagues: string[];
  skills: string[];
  notes: string;
}

interface WorkSectionProps {
  data: WorkData;
  onSave: (data: WorkData) => void;
}

interface TagInputProps {
  label: string;
  items: string[];
  editing: boolean;
  onAdd: (item: string) => void;
  onRemove: (index: number) => void;
  color?: string;
}

function TagInput({ label, items, editing, onAdd, onRemove, color = 'bg-accent/10 text-accent-foreground' }: TagInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleAdd = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed && !items.includes(trimmed)) {
      onAdd(trimmed);
      setInputValue('');
    }
  }, [inputValue, items, onAdd]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleAdd();
      }
    },
    [handleAdd]
  );

  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
        {label}
      </label>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, index) => (
          <span
            key={`${item}-${index}`}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${color}`}
          >
            {item}
            {editing && (
              <button
                type="button"
                onClick={() => onRemove(index)}
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
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Add ${label.toLowerCase()}...`}
              className="w-28 bg-muted rounded-full px-2.5 py-1 text-xs text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
            />
            <button
              type="button"
              onClick={handleAdd}
              className="p-1 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              aria-label={`Add ${label.toLowerCase()}`}
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
        )}
        {!editing && items.length === 0 && (
          <span className="text-xs text-muted-foreground italic">None added</span>
        )}
      </div>
    </div>
  );
}

export function WorkSection({ data, onSave }: WorkSectionProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<WorkData>(data);

  const startEditing = useCallback(() => {
    setDraft(data);
    setEditing(true);
  }, [data]);

  const save = useCallback(() => {
    onSave(draft);
    setEditing(false);
  }, [draft, onSave]);

  const addItem = useCallback(
    (field: 'projects' | 'colleagues' | 'skills') => (item: string) => {
      setDraft((prev) => ({ ...prev, [field]: [...prev[field], item] }));
    },
    []
  );

  const removeItem = useCallback(
    (field: 'projects' | 'colleagues' | 'skills') => (index: number) => {
      setDraft((prev) => ({
        ...prev,
        [field]: prev[field].filter((_, i) => i !== index),
      }));
    },
    []
  );

  const displayData = editing ? draft : data;

  return (
    <div className="group relative">
      {!editing && (
        <button
          type="button"
          onClick={startEditing}
          className="absolute top-0 right-0 p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
          aria-label="Edit work"
          title="Edit"
        >
          <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
      )}

      <div className="space-y-4">
        {/* Role and Company */}
        {editing ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Role</label>
              <input
                type="text"
                value={draft.role}
                onChange={(e) => setDraft({ ...draft, role: e.target.value })}
                className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Company</label>
              <input
                type="text"
                value={draft.company}
                onChange={(e) => setDraft({ ...draft, company: e.target.value })}
                className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              />
            </div>
          </div>
        ) : (
          (displayData.role || displayData.company) && (
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1 uppercase tracking-wider">
                Position
              </label>
              <p className="text-sm text-foreground">
                {displayData.role}
                {displayData.role && displayData.company && ' @ '}
                {displayData.company}
              </p>
            </div>
          )
        )}

        <TagInput
          label="Projects"
          items={displayData.projects}
          editing={editing}
          onAdd={addItem('projects')}
          onRemove={removeItem('projects')}
          color="bg-indigo-500/10 text-indigo-400"
        />
        <TagInput
          label="Colleagues"
          items={displayData.colleagues}
          editing={editing}
          onAdd={addItem('colleagues')}
          onRemove={removeItem('colleagues')}
          color="bg-blue-500/10 text-blue-400"
        />
        <TagInput
          label="Skills"
          items={displayData.skills}
          editing={editing}
          onAdd={addItem('skills')}
          onRemove={removeItem('skills')}
          color="bg-green-500/10 text-green-400"
        />

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
              placeholder="Work notes..."
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
