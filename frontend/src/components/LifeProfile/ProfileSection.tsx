import { useState } from 'react';
import { ChevronDown, ChevronUp, type LucideIcon } from 'lucide-react';

interface ProfileSectionProps {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function ProfileSection({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
}: ProfileSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="bg-card rounded-md shadow-sm border border-border/50 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 sm:px-6 py-3.5 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="w-4.5 h-4.5 text-accent" />
          <h2 className="text-sm sm:text-base font-semibold tracking-tight text-foreground">
            {title}
          </h2>
        </div>
        {open ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {open && (
        <div className="px-4 sm:px-6 pb-4 sm:pb-5 pt-1">
          {children}
        </div>
      )}
    </div>
  );
}
