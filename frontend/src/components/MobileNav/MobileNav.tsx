import { FileText, LayoutDashboard, Kanban, User } from 'lucide-react'

type View = 'editor' | 'dashboard' | 'kanban' | 'calendar' | 'profile'

interface MobileNavProps {
  currentView: View
  onViewChange: (view: View) => void
}

const navItems: { view: View; label: string; icon: typeof FileText }[] = [
  { view: 'editor', label: 'Editor', icon: FileText },
  { view: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { view: 'kanban', label: 'Kanban', icon: Kanban },
  { view: 'profile', label: 'Profile', icon: User },
]

export function MobileNav({ currentView, onViewChange }: MobileNavProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-background border-t z-50 safe-area-bottom">
      <div className="flex items-center justify-around h-16">
        {navItems.map(({ view, label, icon: Icon }) => {
          const isActive = currentView === view
          return (
            <button
              key={view}
              onClick={() => onViewChange(view)}
              className={`
                flex flex-col items-center justify-center
                w-full h-full min-h-[44px] min-w-[44px]
                transition-colors
                ${isActive
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
                }
              `}
              aria-label={label}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs mt-1">{label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
