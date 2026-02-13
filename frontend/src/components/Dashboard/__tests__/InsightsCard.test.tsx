import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { InsightsCard, _resetInsightsCache } from '../InsightsCard';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

beforeEach(() => {
  _resetInsightsCache();
  mockFetch.mockReset();
  mockLocalStorage.getItem.mockReset();
  mockLocalStorage.setItem.mockReset();
  mockLocalStorage.removeItem.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('InsightsCard', () => {
  it('displays loading state', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));

    render(<InsightsCard />);

    expect(screen.getByTestId('insights-loading')).toBeInTheDocument();
    expect(screen.getByText('Insights')).toBeInTheDocument();
  });

  it('displays insights when data is loaded', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        insights: [
          {
            id: 'insight_0',
            type: 'pattern',
            title: 'Monday Workouts',
            message: 'You usually log strength training on Mondays.',
            priority: 3,
          },
          {
            id: 'insight_1',
            type: 'reminder',
            title: 'Food Log',
            message: "You haven't logged any food today.",
            priority: 2,
          },
        ],
        generated_at: '2026-02-05',
      }),
    });

    render(<InsightsCard />);

    await waitFor(() => {
      expect(screen.getByTestId('insights-card')).toBeInTheDocument();
    });

    expect(screen.getByText('Monday Workouts')).toBeInTheDocument();
    expect(screen.getByText('You usually log strength training on Mondays.')).toBeInTheDocument();
    expect(screen.getByText('Food Log')).toBeInTheDocument();
  });

  it('displays empty state when no insights', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        insights: [],
        generated_at: '2026-02-05',
      }),
    });

    render(<InsightsCard />);

    await waitFor(() => {
      expect(screen.getByTestId('insights-empty')).toBeInTheDocument();
    });

    expect(screen.getByText('No new insights')).toBeInTheDocument();
  });

  it('displays error state on fetch failure', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
    });

    render(<InsightsCard />);

    await waitFor(() => {
      expect(screen.getByTestId('insights-error')).toBeInTheDocument();
    });

    expect(screen.getByText('Failed to load insights')).toBeInTheDocument();
  });

  it('can dismiss an insight', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        insights: [
          {
            id: 'insight_0',
            type: 'pattern',
            title: 'Test Insight',
            message: 'This is a test insight.',
            priority: 2,
          },
        ],
        generated_at: '2026-02-05',
      }),
    });

    render(<InsightsCard />);

    await waitFor(() => {
      expect(screen.getByText('Test Insight')).toBeInTheDocument();
    });

    // Find and click the dismiss button
    const dismissButton = screen.getByLabelText('Dismiss insight');
    fireEvent.click(dismissButton);

    // Insight should be hidden
    await waitFor(() => {
      expect(screen.queryByText('Test Insight')).not.toBeInTheDocument();
    });

    // Should show empty state since all insights dismissed
    expect(screen.getByTestId('insights-empty')).toBeInTheDocument();
  });

  it('can refresh insights', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        insights: [
          {
            id: 'insight_0',
            type: 'trend',
            title: 'Sleep Improved',
            message: 'Your sleep improved 15% this week.',
            priority: 3,
          },
        ],
        generated_at: '2026-02-05',
      }),
    });

    render(<InsightsCard />);

    await waitFor(() => {
      expect(screen.getByTestId('insights-card')).toBeInTheDocument();
    });

    // Click refresh button
    const refreshButton = screen.getByLabelText('Refresh insights');
    fireEvent.click(refreshButton);

    // Should call fetch again
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  it('restores dismissed insights from localStorage', async () => {
    // Set up localStorage to have a dismissed insight
    mockLocalStorage.getItem.mockReturnValue(
      JSON.stringify({ insight_0: Date.now() })
    );

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        insights: [
          {
            id: 'insight_0',
            type: 'pattern',
            title: 'Dismissed Insight',
            message: 'This was dismissed.',
            priority: 2,
          },
          {
            id: 'insight_1',
            type: 'trend',
            title: 'Visible Insight',
            message: 'This should be visible.',
            priority: 2,
          },
        ],
        generated_at: '2026-02-05',
      }),
    });

    render(<InsightsCard />);

    await waitFor(() => {
      expect(screen.getByTestId('insights-card')).toBeInTheDocument();
    });

    // Dismissed insight should not be visible
    expect(screen.queryByText('Dismissed Insight')).not.toBeInTheDocument();

    // Other insight should be visible
    expect(screen.getByText('Visible Insight')).toBeInTheDocument();
  });
});
