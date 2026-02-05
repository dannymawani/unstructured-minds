import { useState, useRef, useEffect } from 'react';
import { Settings, Eye, EyeOff, GripVertical, X } from 'lucide-react';

export interface WidgetDefinition {
  id: string;
  name: string;
  description: string;
  defaultVisible: boolean;
}

export const AVAILABLE_WIDGETS: WidgetDefinition[] = [
  { id: 'summary', name: 'Summary Cards', description: 'Activity counts, streaks, and quick stats', defaultVisible: true },
  { id: 'insights', name: 'AI Insights', description: 'Smart suggestions based on your data', defaultVisible: true },
  { id: 'heatmap', name: 'Activity Heatmap', description: 'GitHub-style yearly activity calendar', defaultVisible: true },
  { id: 'weeklyActivity', name: 'Weekly Activity', description: 'Bar chart of activity types', defaultVisible: true },
  { id: 'metricsTrends', name: 'Daily Metrics', description: 'Energy, mood, and stress trends', defaultVisible: true },
  { id: 'sleepTrends', name: 'Sleep Trends', description: 'Sleep duration over time', defaultVisible: true },
  { id: 'moodCorrelation', name: 'Mood Correlations', description: 'Scatter plot showing metric relationships', defaultVisible: true },
  { id: 'exerciseProgress', name: 'Exercise Progress', description: 'Track specific exercise progress', defaultVisible: true },
];

export interface WidgetConfig {
  id: string;
  visible: boolean;
  order: number;
}

interface WidgetConfigPanelProps {
  widgets: WidgetConfig[];
  onChange: (widgets: WidgetConfig[]) => void;
}

export function WidgetConfigPanel({ widgets, onChange }: WidgetConfigPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  // Close panel when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get sorted widgets with their definitions
  const sortedWidgets = [...widgets]
    .sort((a, b) => a.order - b.order)
    .map((w) => ({
      config: w,
      definition: AVAILABLE_WIDGETS.find((d) => d.id === w.id)!,
    }));

  const toggleWidget = (id: string) => {
    const updated = widgets.map((w) =>
      w.id === id ? { ...w, visible: !w.visible } : w
    );
    onChange(updated);
  };

  const handleDragStart = (e: React.DragEvent, id: string) => {
    setDraggedId(id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    if (!draggedId || draggedId === targetId) return;

    const draggedIndex = widgets.findIndex((w) => w.id === draggedId);
    const targetIndex = widgets.findIndex((w) => w.id === targetId);

    if (draggedIndex === -1 || targetIndex === -1) return;

    // Reorder
    const newWidgets = [...widgets];
    const [removed] = newWidgets.splice(draggedIndex, 1);
    newWidgets.splice(targetIndex, 0, removed);

    // Update order values
    const reordered = newWidgets.map((w, idx) => ({ ...w, order: idx }));
    onChange(reordered);
  };

  const handleDragEnd = () => {
    setDraggedId(null);
  };

  const resetToDefault = () => {
    const defaultConfig = AVAILABLE_WIDGETS.map((w, idx) => ({
      id: w.id,
      visible: w.defaultVisible,
      order: idx,
    }));
    onChange(defaultConfig);
  };

  return (
    <div className="relative" ref={panelRef}>
      <button
        className="flex items-center gap-2 bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-3 py-2 rounded-lg transition-colors min-h-[40px]"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Configure widgets"
      >
        <Settings className="w-4 h-4" />
        <span className="hidden sm:inline">Customize</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-30 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700">
            <h4 className="font-medium text-white">Dashboard Widgets</h4>
            <button
              onClick={() => setIsOpen(false)}
              className="text-zinc-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Widget list */}
          <div className="max-h-80 overflow-y-auto">
            {sortedWidgets.map(({ config, definition }) => (
              <div
                key={config.id}
                draggable
                onDragStart={(e) => handleDragStart(e, config.id)}
                onDragOver={(e) => handleDragOver(e, config.id)}
                onDragEnd={handleDragEnd}
                className={`flex items-center gap-3 px-4 py-3 hover:bg-zinc-700/50 cursor-move transition-colors ${
                  draggedId === config.id ? 'opacity-50 bg-zinc-700' : ''
                }`}
              >
                <GripVertical className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-white text-sm truncate">
                    {definition.name}
                  </div>
                  <div className="text-xs text-zinc-400 truncate">
                    {definition.description}
                  </div>
                </div>
                <button
                  onClick={() => toggleWidget(config.id)}
                  className={`p-1.5 rounded transition-colors ${
                    config.visible
                      ? 'text-green-400 hover:bg-green-400/20'
                      : 'text-zinc-500 hover:bg-zinc-600'
                  }`}
                  aria-label={config.visible ? 'Hide widget' : 'Show widget'}
                >
                  {config.visible ? (
                    <Eye className="w-4 h-4" />
                  ) : (
                    <EyeOff className="w-4 h-4" />
                  )}
                </button>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-zinc-700">
            <button
              onClick={resetToDefault}
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Reset to defaults
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Hook to manage widget configuration with localStorage persistence
export function useWidgetConfig(): [WidgetConfig[], (config: WidgetConfig[]) => void] {
  const [widgets, setWidgets] = useState<WidgetConfig[]>(() => {
    // Try to load from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('dashboard-widgets');
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch {
          // Invalid JSON, use defaults
        }
      }
    }

    // Return defaults
    return AVAILABLE_WIDGETS.map((w, idx) => ({
      id: w.id,
      visible: w.defaultVisible,
      order: idx,
    }));
  });

  const updateWidgets = (newConfig: WidgetConfig[]) => {
    setWidgets(newConfig);
    if (typeof window !== 'undefined') {
      localStorage.setItem('dashboard-widgets', JSON.stringify(newConfig));
    }
  };

  return [widgets, updateWidgets];
}
