import { useState } from 'react';
import { Info, PenLine, Trash2, X } from 'lucide-react';

interface DemoBannerProps {
  apiUrl: string;
  onCreateNote: () => void;
  onDemoCleared: () => void;
}

export function DemoBanner({ apiUrl, onCreateNote, onDemoCleared }: DemoBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const [clearing, setClearing] = useState(false);

  if (dismissed) return null;

  const handleClear = async () => {
    setClearing(true);
    try {
      const resp = await fetch(`${apiUrl}/onboarding/clear-demo`, { method: 'POST' });
      if (resp.ok) {
        onDemoCleared();
      }
    } catch {
      // Silently fail
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 rounded-md bg-accent/10 border border-accent/20 text-sm">
      <Info className="w-4 h-4 text-accent shrink-0" />
      <span className="text-muted-foreground flex-1">
        Viewing demo data. Create your first daily note to start tracking.
      </span>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={onCreateNote}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-accent text-accent-foreground text-xs font-medium hover:opacity-90 transition-opacity"
        >
          <PenLine className="w-3 h-3" />
          Create Daily Note
        </button>

        <button
          onClick={handleClear}
          disabled={clearing}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md border border-border text-muted-foreground text-xs font-medium hover:bg-muted transition-colors disabled:opacity-50"
        >
          <Trash2 className="w-3 h-3" />
          {clearing ? 'Clearing...' : 'Clear Demo Data'}
        </button>

        <button
          onClick={() => setDismissed(true)}
          className="p-1 rounded-md text-muted-foreground hover:bg-muted transition-colors"
          aria-label="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
