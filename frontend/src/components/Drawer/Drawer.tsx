import { useEffect, useCallback, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

type DrawerPosition = 'left' | 'right' | 'bottom'

interface DrawerProps {
  isOpen: boolean
  onClose: () => void
  position?: DrawerPosition
  title?: string
  children: ReactNode
  className?: string
}

const positionClasses: Record<DrawerPosition, string> = {
  left: 'inset-y-0 left-0 w-80 max-w-[85vw]',
  right: 'inset-y-0 right-0 w-80 max-w-[85vw]',
  bottom: 'inset-x-0 bottom-0 h-[70vh] max-h-[70vh] rounded-t-xl',
}

const slideInClasses: Record<DrawerPosition, { open: string; closed: string }> = {
  left: {
    open: 'translate-x-0',
    closed: '-translate-x-full',
  },
  right: {
    open: 'translate-x-0',
    closed: 'translate-x-full',
  },
  bottom: {
    open: 'translate-y-0',
    closed: 'translate-y-full',
  },
}

export function Drawer({
  isOpen,
  onClose,
  position = 'left',
  title,
  children,
  className,
}: DrawerProps) {
  // Handle escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    },
    [onClose]
  )

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      // Prevent body scroll when drawer is open
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  const slideClasses = slideInClasses[position]

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/50 z-40 transition-opacity',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        className={cn(
          'fixed z-50 bg-background shadow-lg transition-transform duration-300 ease-in-out',
          positionClasses[position],
          isOpen ? slideClasses.open : slideClasses.closed,
          className
        )}
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Drawer'}
      >
        {/* Header with close button */}
        {title && (
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button
              onClick={onClose}
              className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-md hover:bg-accent"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Drawer content */}
        <div className={cn('flex-1 overflow-auto', title ? 'h-[calc(100%-57px)]' : 'h-full')}>
          {children}
        </div>
      </div>
    </>
  )
}
