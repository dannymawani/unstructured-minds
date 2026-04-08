import { useState, useCallback } from 'react';
import { MapPin, Building2, Pencil, Check } from 'lucide-react';

interface Overview {
  name: string;
  age: number | null;
  location: string;
  company: string;
  role: string;
  summary: string;
}

interface OverviewSectionProps {
  data: Overview;
  onSave: (data: Overview) => void;
}

export function OverviewSection({ data, onSave }: OverviewSectionProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Overview>(data);

  const startEditing = useCallback(() => {
    setDraft(data);
    setEditing(true);
  }, [data]);

  const save = useCallback(() => {
    onSave(draft);
    setEditing(false);
  }, [draft, onSave]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        save();
      }
      if (e.key === 'Escape') {
        setEditing(false);
      }
    },
    [save]
  );

  if (editing) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Name</label>
            <input
              type="text"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              onKeyDown={handleKeyDown}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Age</label>
            <input
              type="number"
              value={draft.age ?? ''}
              onChange={(e) =>
                setDraft({ ...draft, age: e.target.value ? Number(e.target.value) : null })
              }
              onKeyDown={handleKeyDown}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Role</label>
            <input
              type="text"
              value={draft.role}
              onChange={(e) => setDraft({ ...draft, role: e.target.value })}
              onKeyDown={handleKeyDown}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Company</label>
            <input
              type="text"
              value={draft.company}
              onChange={(e) => setDraft({ ...draft, company: e.target.value })}
              onKeyDown={handleKeyDown}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs text-muted-foreground mb-1">Location</label>
            <input
              type="text"
              value={draft.location}
              onChange={(e) => setDraft({ ...draft, location: e.target.value })}
              onKeyDown={handleKeyDown}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs text-muted-foreground mb-1">Summary</label>
            <textarea
              value={draft.summary}
              onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setEditing(false);
              }}
              rows={3}
              className="w-full bg-muted rounded-md px-3 py-2 text-sm text-foreground border-none focus:ring-2 focus:ring-ring outline-none resize-none"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
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
      </div>
    );
  }

  return (
    <div className="group relative">
      <button
        type="button"
        onClick={startEditing}
        className="absolute top-0 right-0 p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
        aria-label="Edit overview"
        title="Edit"
      >
        <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
      </button>

      <div className="space-y-2">
        <div>
          <h3 className="text-xl sm:text-2xl font-bold text-foreground">
            {data.name || 'Unnamed'}
            {data.age != null && (
              <span className="text-muted-foreground font-normal text-base ml-2">
                {data.age}
              </span>
            )}
          </h3>
        </div>

        {(data.role || data.company) && (
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Building2 className="w-3.5 h-3.5 flex-shrink-0" />
            <span>
              {data.role}
              {data.role && data.company && ' @ '}
              {data.company}
            </span>
          </div>
        )}

        {data.location && (
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{data.location}</span>
          </div>
        )}

        {data.summary && (
          <p className="text-sm text-muted-foreground mt-3 leading-relaxed">
            {data.summary}
          </p>
        )}
      </div>
    </div>
  );
}
