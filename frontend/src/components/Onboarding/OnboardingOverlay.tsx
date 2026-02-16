import { useState } from 'react';
import { Sparkles, PenLine } from 'lucide-react';

interface OnboardingOverlayProps {
  apiUrl: string;
  onSeedDemo: () => void;
  onStartWriting: () => void;
}

export function OnboardingOverlay({ apiUrl, onSeedDemo, onStartWriting }: OnboardingOverlayProps) {
  const [loading, setLoading] = useState(false);

  const handleSeedDemo = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${apiUrl}/onboarding/seed`, { method: 'POST' });
      if (resp.ok) {
        onSeedDemo();
      }
    } catch {
      // Silently fail — user can retry
    } finally {
      setLoading(false);
    }
  };

  const handleStartWriting = async () => {
    try {
      await fetch(`${apiUrl}/onboarding/complete`, { method: 'POST' });
    } catch {
      // Non-critical
    }
    onStartWriting();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-card rounded-lg shadow-xl max-w-md w-full mx-4 p-6 sm:p-8">
        <h2 className="text-xl font-semibold text-foreground mb-3">
          Welcome to Unstructured Minds
        </h2>

        <div className="space-y-3 text-sm text-muted-foreground mb-6">
          <p>Write daily notes in markdown.</p>
          <p>AI extracts your workouts, mood, sleep, nutrition, and tasks.</p>
          <p>Your dashboard shows the patterns.</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleSeedDemo}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-accent text-accent-foreground font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            {loading ? 'Loading...' : 'See it in action'}
          </button>

          <button
            onClick={handleStartWriting}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md border border-border text-foreground font-medium text-sm hover:bg-muted transition-colors"
          >
            <PenLine className="w-4 h-4" />
            Start writing
          </button>
        </div>
      </div>
    </div>
  );
}
