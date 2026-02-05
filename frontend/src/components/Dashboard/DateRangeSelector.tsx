import { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';

interface DateRangeOption {
  value: number;
  label: string;
}

const DATE_RANGE_OPTIONS: DateRangeOption[] = [
  { value: 7, label: 'Last 7 days' },
  { value: 14, label: 'Last 14 days' },
  { value: 30, label: 'Last 30 days' },
  { value: 60, label: 'Last 60 days' },
  { value: 90, label: 'Last 90 days' },
  { value: 180, label: 'Last 6 months' },
  { value: 365, label: 'Last year' },
];

interface DateRangeSelectorProps {
  value: number;
  onChange: (days: number) => void;
  className?: string;
}

export function DateRangeSelector({ value, onChange, className = '' }: DateRangeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentOption = DATE_RANGE_OPTIONS.find((opt) => opt.value === value) || DATE_RANGE_OPTIONS[2];

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        className="flex items-center gap-2 bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-3 py-2 rounded-lg transition-colors min-h-[40px]"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Select date range"
      >
        <Calendar className="w-4 h-4 text-zinc-400" />
        <span>{currentOption.label}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-44 bg-zinc-700 rounded-lg shadow-lg z-20 overflow-hidden">
          {DATE_RANGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-zinc-600 transition-colors ${
                option.value === value ? 'bg-zinc-600 text-white' : 'text-zinc-300'
              }`}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
