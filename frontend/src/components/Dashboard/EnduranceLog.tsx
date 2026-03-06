import { useEffect, useState, useCallback } from 'react';
import { Activity, Plus, X, Loader2, ChevronDown, ChevronUp, Timer, Route } from 'lucide-react';
import { clearCache } from '../../lib/cachedFetch';
import { EnduranceProgress } from './EnduranceProgress';

interface EnduranceEntry {
  date: string;
  sport: string;
  distance_km: number | null;
  duration_minutes: number | null;
  pace_min_per_km: number | null;
  speed_kmh: number | null;
  notes: string | null;
}

interface EnduranceTableData {
  entries: EnduranceEntry[];
  total_count: number;
  offset: number;
  limit: number;
}

interface EnduranceLogProps {
  apiUrl?: string;
}

type SportFilter = 'all' | 'running' | 'cycling' | 'swimming';
type SortColumn = 'date' | 'distance_km' | 'duration_minutes' | 'pace_min_per_km';
type SortOrder = 'asc' | 'desc';

const SPORT_ICONS: Record<string, string> = {
  running: '🏃',
  cycling: '🚴',
  swimming: '🏊',
};

const SPORT_COLORS: Record<string, string> = {
  running: 'text-orange-400',
  cycling: 'text-lime-400',
  swimming: 'text-cyan-400',
};

const PAGE_SIZE = 20;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatPace(pace: number | null): string {
  if (pace === null) return '-';
  const mins = Math.floor(pace);
  const secs = Math.round((pace - mins) * 60);
  return `${mins}:${secs.toString().padStart(2, '0')} /km`;
}

function formatSpeed(speed: number | null): string {
  if (speed === null) return '-';
  return `${speed.toFixed(1)} km/h`;
}

function formatDistance(km: number | null): string {
  if (km === null) return '-';
  return `${km.toFixed(1)} km`;
}

function formatDuration(minutes: number | null): string {
  if (minutes === null) return '-';
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function EnduranceLog({ apiUrl = 'http://localhost:8000' }: EnduranceLogProps) {
  const [entries, setEntries] = useState<EnduranceEntry[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [sportFilter, setSportFilter] = useState<SportFilter>('all');
  const [sortBy, setSortBy] = useState<SortColumn>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const today = new Date().toISOString().split('T')[0];
  const [formData, setFormData] = useState({
    sport: 'running' as 'running' | 'cycling' | 'swimming',
    date: today,
    distance_km: '',
    duration_minutes: '',
    notes: '',
  });

  const fetchData = useCallback(async (offset = 0, append = false) => {
    if (!append) setLoading(true);
    else setLoadingMore(true);

    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
        sort_by: sortBy,
        sort_order: sortOrder,
        days: '365',
      });
      if (sportFilter !== 'all') params.set('sport', sportFilter);

      const response = await fetch(`${apiUrl}/dashboard/endurance-table?${params}`);
      if (!response.ok) throw new Error('Failed to fetch endurance data');
      const result: EnduranceTableData = await response.json();

      if (append) {
        setEntries((prev) => [...prev, ...result.entries]);
      } else {
        setEntries(result.entries);
      }
      setTotalCount(result.total_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [apiUrl, sportFilter, sortBy, sortOrder]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSort = (column: SortColumn) => {
    if (column === sortBy) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const loadMore = () => {
    fetchData(entries.length, true);
  };

  const resetForm = () => {
    setFormData({ sport: 'running', date: today, distance_km: '', duration_minutes: '', notes: '' });
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.distance_km && !formData.duration_minutes) {
      setFormError('Enter at least distance or duration');
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const body: Record<string, unknown> = {
        sport: formData.sport,
        date: formData.date,
      };
      if (formData.distance_km) body.distance_km = parseFloat(formData.distance_km);
      if (formData.duration_minutes) body.duration_minutes = parseInt(formData.duration_minutes);
      if (formData.notes.trim()) body.notes = formData.notes.trim();

      const response = await fetch(`${apiUrl}/dashboard/endurance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to log activity (${response.status})`);
      }

      clearCache();
      resetForm();
      setShowForm(false);
      fetchData();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to log activity');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && entries.length === 0) {
    return <div className="bg-card rounded-md shadow-sm p-4 h-64 animate-pulse" data-testid="endurance-log-loading" />;
  }

  if (error) {
    return <div className="text-red-400 p-4" data-testid="endurance-log-error">Error: {error}</div>;
  }

  const hasMore = entries.length < totalCount;
  const showChart = sportFilter !== 'all';

  return (
    <div className="space-y-4" data-testid="endurance-log">
      <div className="bg-card rounded-md shadow-sm p-3 sm:p-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 mb-3 sm:mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-orange-500/20 rounded-lg">
              <Activity className="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-semibold text-foreground">Endurance Log</h3>
              <p className="text-sm text-muted-foreground">
                {totalCount} session{totalCount !== 1 ? 's' : ''} tracked
              </p>
            </div>
          </div>
          <button
            onClick={() => { setShowForm(!showForm); if (showForm) resetForm(); }}
            className="flex items-center gap-1.5 bg-orange-500 hover:bg-orange-600 text-white text-sm px-3 py-2 rounded-lg transition-colors min-h-[40px] sm:min-h-0"
          >
            {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showForm ? 'Cancel' : 'Log Activity'}
          </button>
        </div>

        {/* Sport filter tabs */}
        <div className="flex gap-1 mb-3 bg-secondary rounded-lg p-1">
          {(['all', 'running', 'cycling', 'swimming'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSportFilter(s)}
              className={`flex-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                sportFilter === s
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {s === 'all' ? 'All' : `${SPORT_ICONS[s]} ${s.charAt(0).toUpperCase() + s.slice(1)}`}
            </button>
          ))}
        </div>

        {/* Inline Add Form */}
        {showForm && (
          <form onSubmit={handleSubmit} className="mb-4 p-3 bg-secondary/50 rounded-lg border border-border">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Sport *</label>
                <select
                  value={formData.sport}
                  onChange={(e) => setFormData({ ...formData, sport: e.target.value as typeof formData.sport })}
                  className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
                >
                  <option value="running">🏃 Running</option>
                  <option value="cycling">🚴 Cycling</option>
                  <option value="swimming">🏊 Swimming</option>
                </select>
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
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Distance (km)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={formData.distance_km}
                  onChange={(e) => setFormData({ ...formData, distance_km: e.target.value })}
                  placeholder="e.g. 5.0"
                  className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Duration (min)</label>
                <input
                  type="number"
                  min="1"
                  value={formData.duration_minutes}
                  onChange={(e) => setFormData({ ...formData, duration_minutes: e.target.value })}
                  placeholder="e.g. 25"
                  className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Notes</label>
                <input
                  type="text"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Optional"
                  className="w-full bg-muted text-foreground rounded px-3 py-2 text-sm border-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
            {formError && <p className="text-red-400 text-xs mt-2">{formError}</p>}
            <div className="flex justify-end mt-3">
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-1.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors"
              >
                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                {submitting ? 'Logging...' : 'Log'}
              </button>
            </div>
          </form>
        )}

        {/* Table */}
        {entries.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p>{sportFilter !== 'all' ? `No ${sportFilter} sessions yet.` : 'No endurance sessions tracked yet.'}</p>
            <p className="text-sm mt-1">Log your first activity using the button above.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border text-muted-foreground text-left">
                    <th
                      className="pb-2 pr-4 font-medium cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => handleSort('date')}
                    >
                      <span className="inline-flex items-center gap-0.5">
                        Date
                        {sortBy === 'date' && (sortOrder === 'desc' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />)}
                      </span>
                    </th>
                    <th className="pb-2 pr-4 font-medium">Sport</th>
                    <th
                      className="pb-2 pr-4 font-medium text-right cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => handleSort('distance_km')}
                    >
                      <span className="inline-flex items-center gap-0.5 justify-end">
                        Distance
                        {sortBy === 'distance_km' && (sortOrder === 'desc' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />)}
                      </span>
                    </th>
                    <th
                      className="pb-2 pr-4 font-medium text-right cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => handleSort('duration_minutes')}
                    >
                      <span className="inline-flex items-center gap-0.5 justify-end">
                        Duration
                        {sortBy === 'duration_minutes' && (sortOrder === 'desc' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />)}
                      </span>
                    </th>
                    <th
                      className="pb-2 pr-4 font-medium text-right cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => handleSort('pace_min_per_km')}
                    >
                      <span className="inline-flex items-center gap-0.5 justify-end">
                        <Timer className="w-3.5 h-3.5" /> Pace / Speed
                        {sortBy === 'pace_min_per_km' && (sortOrder === 'desc' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />)}
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry, idx) => (
                    <tr key={`${entry.date}-${entry.sport}-${idx}`} className="border-b border-border/50 hover:bg-secondary/30 transition-colors">
                      <td className="py-2.5 pr-4 text-muted-foreground">{formatDate(entry.date)}</td>
                      <td className="py-2.5 pr-4">
                        <span className={`font-medium ${SPORT_COLORS[entry.sport] || 'text-foreground'}`}>
                          {SPORT_ICONS[entry.sport] || ''} {entry.sport.charAt(0).toUpperCase() + entry.sport.slice(1)}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-right text-foreground">
                        <span className="inline-flex items-center gap-1">
                          <Route className="w-3.5 h-3.5 text-muted-foreground" />
                          {formatDistance(entry.distance_km)}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-right text-foreground">{formatDuration(entry.duration_minutes)}</td>
                      <td className="py-2.5 text-right text-foreground">
                        {entry.sport === 'cycling'
                          ? formatSpeed(entry.speed_kmh)
                          : entry.sport === 'swimming'
                            ? formatDuration(entry.duration_minutes)
                            : formatPace(entry.pace_min_per_km)}
                      </td>
                    </tr>
                  ))}
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
                  {loadingMore ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronDown className="w-4 h-4" />}
                  {loadingMore ? 'Loading...' : `Show more (${entries.length} of ${totalCount})`}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Progress chart when a specific sport is selected */}
      {showChart && (
        <EnduranceProgress sport={sportFilter} apiUrl={apiUrl} days={90} />
      )}
    </div>
  );
}
