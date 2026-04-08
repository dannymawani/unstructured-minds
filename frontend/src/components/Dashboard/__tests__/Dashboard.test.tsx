import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

// Mock cachedFetch to use the mocked global fetch
vi.mock('../../../lib/cachedFetch', () => ({
  cachedFetch: async (url: string) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Failed to fetch ${url}`);
    return response.json();
  },
  clearCache: vi.fn(),
}));

import { Dashboard } from '../Dashboard';
import { DashboardSummary } from '../DashboardSummary';
import { WeeklyActivityChart } from '../WeeklyActivityChart';
import { MetricsTrends } from '../MetricsTrends';
import { ExerciseProgress } from '../ExerciseProgress';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

beforeEach(() => {
  mockFetch.mockReset();
  mockLocalStorage.getItem.mockReturnValue(null);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Dashboard', () => {
  it('renders dashboard layout', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        total_activities: 10,
        total_daily_notes: 5,
        streak_days: 5,
        last_activity_date: '2026-02-01',
        last_daily_note_date: '2026-02-01',
        activities: [],
        groups: [],
        total_entries: 0,
        metrics: [],
        progress: [],
        summary: { current_max: null, all_time_max: null, total_volume: 0, total_sessions: 0 },
      }),
    });

    render(<Dashboard />);

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });
});

describe('DashboardSummary', () => {
  it('displays loading state', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));

    render(<DashboardSummary />);

    expect(screen.getByTestId('summary-loading')).toBeInTheDocument();
  });

  it('displays summary data', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        total_activities: 10,
        total_daily_notes: 8,
        streak_days: 5,
        last_activity_date: '2026-02-01',
        last_daily_note_date: '2026-02-01',
      }),
    });

    render(<DashboardSummary />);

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-summary')).toBeInTheDocument();
    });

    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('displays error state', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
    });

    render(<DashboardSummary />);

    await waitFor(() => {
      expect(screen.getByTestId('summary-error')).toBeInTheDocument();
    });
  });
});

describe('WeeklyActivityChart', () => {
  it('displays loading state', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));

    render(<WeeklyActivityChart />);

    expect(screen.getByTestId('activity-loading')).toBeInTheDocument();
  });

  it('displays empty state when no data', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('activity-groups')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ groups: [], total_entries: 0, period: '7d' }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ activities: [], total_duration_minutes: 0 }),
      });
    });

    render(<WeeklyActivityChart />);

    await waitFor(() => {
      expect(screen.getByTestId('activity-empty')).toBeInTheDocument();
    });

    expect(screen.getByText('No activities recorded yet.')).toBeInTheDocument();
  });

  it('displays chart with data', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('activity-groups')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            groups: [
              { group_name: 'Strength Training', entry_count: 3, subtypes: ['strength'] },
              { group_name: 'Running / Cardio', entry_count: 2, subtypes: ['cardio'] },
            ],
            total_entries: 5,
            period: '7d',
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({
          activities: [
            { activity_type: 'strength', count: 3, total_duration_minutes: 180 },
            { activity_type: 'cardio', count: 2, total_duration_minutes: 60 },
          ],
          total_duration_minutes: 240,
        }),
      });
    });

    render(<WeeklyActivityChart />);

    await waitFor(() => {
      expect(screen.getByTestId('weekly-activity-chart')).toBeInTheDocument();
    });

    expect(screen.getByText('Activity Breakdown')).toBeInTheDocument();
  });
});

describe('MetricsTrends', () => {
  it('displays loading state', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));

    render(<MetricsTrends />);

    expect(screen.getByTestId('metrics-loading')).toBeInTheDocument();
  });

  it('displays empty state when no data', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        metrics: [],
      }),
    });

    render(<MetricsTrends />);

    await waitFor(() => {
      expect(screen.getByTestId('metrics-empty')).toBeInTheDocument();
    });
  });

  it('displays chart with data', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        metrics: [
          { date: '2026-02-01', sleep_hours: 7, energy: 8, mood: 7, stress: 3 },
          { date: '2026-02-02', sleep_hours: 8, energy: 9, mood: 8, stress: 2 },
        ],
      }),
    });

    render(<MetricsTrends />);

    await waitFor(() => {
      expect(screen.getByTestId('metrics-trends')).toBeInTheDocument();
    });

    expect(screen.getByText('Daily Metrics')).toBeInTheDocument();
  });
});

describe('ExerciseProgress', () => {
  it('displays loading state', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));

    render(<ExerciseProgress exercise="Squat" />);

    expect(screen.getByTestId('exercise-loading')).toBeInTheDocument();
  });

  it('displays empty state when no data', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        exercise: 'Squat',
        progress: [],
        summary: { current_max: null, all_time_max: null, total_volume: 0, total_sessions: 0 },
      }),
    });

    render(<ExerciseProgress exercise="Squat" />);

    await waitFor(() => {
      expect(screen.getByTestId('exercise-empty')).toBeInTheDocument();
    });
  });

  it('displays progress data', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        exercise: 'Squat',
        progress: [
          { date: '2026-02-01', max_weight_kg: 100, total_reps: 15, total_sets: 3 },
          { date: '2026-02-02', max_weight_kg: 105, total_reps: 15, total_sets: 3 },
        ],
        summary: { current_max: 105, all_time_max: 110, total_volume: 3000, total_sessions: 10 },
      }),
    });

    render(<ExerciseProgress exercise="Squat" />);

    await waitFor(() => {
      expect(screen.getByTestId('exercise-progress')).toBeInTheDocument();
    });

    expect(screen.getByText('Squat Progress')).toBeInTheDocument();
    expect(screen.getByText('105 kg')).toBeInTheDocument();
    expect(screen.getByText('10 sessions')).toBeInTheDocument();
  });
});
