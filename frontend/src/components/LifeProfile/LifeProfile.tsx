import { useState, useEffect, useCallback } from 'react';
import { User, Briefcase, Dumbbell, Target, TrendingUp, Heart } from 'lucide-react';
import { ProfileSection } from './ProfileSection';
import { OverviewSection } from './OverviewSection';
import { PersonalSection } from './PersonalSection';
import { WorkSection } from './WorkSection';
import { TrainingSection } from './TrainingSection';
import { GoalsSection } from './GoalsSection';
import { ProgressReviews } from './ProgressReviews';

interface Overview {
  name: string;
  age: number | null;
  location: string;
  company: string;
  role: string;
  summary: string;
}

interface PersonalData {
  family: string[];
  friends: string[];
  interests: string[];
  patterns: string[];
  notes: string;
}

interface WorkData {
  role: string;
  company: string;
  projects: string[];
  colleagues: string[];
  skills: string[];
  notes: string;
}

interface TrainingData {
  disciplines: string[];
  current_lifts: Record<string, string>;
  recovery: string;
  goals: string[];
  notes: string;
}

interface Goal {
  id: string;
  category: string;
  description: string;
  status: string;
  target_date: string | null;
  progress: number | null;
}

interface LifeProfileData {
  overview: Overview;
  personal: PersonalData;
  work: WorkData;
  training: TrainingData;
  goals: Goal[];
}

interface LifeProfileProps {
  apiUrl?: string;
}

export function LifeProfile({ apiUrl = 'http://localhost:8000' }: LifeProfileProps) {
  const [profile, setProfile] = useState<LifeProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/profile`);
      if (!response.ok) throw new Error('Failed to load profile');
      const data = await response.json();
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const saveSection = useCallback(
    async (section: string, data: unknown) => {
      setSaveStatus('saving');
      try {
        const response = await fetch(`${apiUrl}/profile/${section}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error(`Failed to save ${section}`);
        const updated = await response.json();

        setProfile((prev) => {
          if (!prev) return prev;
          return { ...prev, ...updated };
        });

        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 2000);
      } catch {
        setSaveStatus('error');
        setTimeout(() => setSaveStatus('idle'), 3000);
      }
    },
    [apiUrl]
  );

  const handleOverviewSave = useCallback(
    (data: Overview) => saveSection('overview', data),
    [saveSection]
  );

  const handlePersonalSave = useCallback(
    (data: PersonalData) => saveSection('personal', data),
    [saveSection]
  );

  const handleWorkSave = useCallback(
    (data: WorkData) => saveSection('work', data),
    [saveSection]
  );

  const handleTrainingSave = useCallback(
    (data: TrainingData) => saveSection('training', data),
    [saveSection]
  );

  const handleGoalsSave = useCallback(
    (goals: Goal[]) => saveSection('goals', goals),
    [saveSection]
  );

  if (loading) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-4">
        <div className="flex items-center gap-2.5 mb-4">
          <User className="w-5 h-5 text-accent" />
          <h1 className="text-lg sm:text-xl font-semibold tracking-tight text-foreground">
            Life Profile
          </h1>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-card rounded-md shadow-sm h-32 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2.5 mb-4">
          <User className="w-5 h-5 text-accent" />
          <h1 className="text-lg sm:text-xl font-semibold tracking-tight text-foreground">
            Life Profile
          </h1>
        </div>
        <div className="bg-card rounded-md shadow-sm p-6 text-center">
          <p className="text-destructive text-sm mb-2">{error}</p>
          <button
            onClick={fetchProfile}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 sm:mb-5">
        <div className="flex items-center gap-2.5">
          <User className="w-5 h-5 text-accent" />
          <h1 className="text-lg sm:text-xl font-semibold tracking-tight text-foreground">
            Life Profile
          </h1>
        </div>

        {/* Save status indicator */}
        {saveStatus !== 'idle' && (
          <span
            className={`text-xs px-2 py-1 rounded-full transition-opacity ${
              saveStatus === 'saving'
                ? 'text-muted-foreground bg-muted'
                : saveStatus === 'saved'
                  ? 'text-green-400 bg-green-500/10'
                  : 'text-destructive bg-destructive/10'
            }`}
          >
            {saveStatus === 'saving'
              ? 'Saving...'
              : saveStatus === 'saved'
                ? 'Saved'
                : 'Save failed'}
          </span>
        )}
      </div>

      {/* Overview — full width hero card */}
      <div className="mb-4">
        <ProfileSection title="Overview" icon={User} defaultOpen>
          <OverviewSection data={profile.overview} onSave={handleOverviewSave} />
        </ProfileSection>
      </div>

      {/* Two-column grid for desktop, single column for mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left column */}
        <div className="space-y-4">
          <ProfileSection title="Personal" icon={Heart} defaultOpen>
            <PersonalSection data={profile.personal} onSave={handlePersonalSave} />
          </ProfileSection>

          <ProfileSection title="Training" icon={Dumbbell} defaultOpen>
            <TrainingSection data={profile.training} onSave={handleTrainingSave} />
          </ProfileSection>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          <ProfileSection title="Work" icon={Briefcase} defaultOpen>
            <WorkSection data={profile.work} onSave={handleWorkSave} />
          </ProfileSection>

          <ProfileSection title="Goals" icon={Target} defaultOpen>
            <GoalsSection goals={profile.goals} onSave={handleGoalsSave} />
          </ProfileSection>
        </div>
      </div>

      {/* Progress Reviews — full width below grid */}
      <div className="mt-4">
        <ProfileSection title="Progress Reviews" icon={TrendingUp} defaultOpen={false}>
          <ProgressReviews apiUrl={apiUrl} />
        </ProfileSection>
      </div>
    </div>
  );
}
