import { useState, useEffect } from 'react'

// Mobile breakpoint matches Tailwind's sm: 640px
const MOBILE_BREAKPOINT = 640

// Tablet breakpoint matches Tailwind's lg: 1024px
const TABLET_BREAKPOINT = 1024

export interface MobileState {
  isMobile: boolean // < 640px
  isTablet: boolean // 640px - 1024px
  isDesktop: boolean // >= 1024px
  width: number
}

export function useMobile(): MobileState {
  const [state, setState] = useState<MobileState>(() => {
    if (typeof window === 'undefined') {
      return { isMobile: false, isTablet: false, isDesktop: true, width: 1200 }
    }
    const width = window.innerWidth
    return {
      isMobile: width < MOBILE_BREAKPOINT,
      isTablet: width >= MOBILE_BREAKPOINT && width < TABLET_BREAKPOINT,
      isDesktop: width >= TABLET_BREAKPOINT,
      width,
    }
  })

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      setState({
        isMobile: width < MOBILE_BREAKPOINT,
        isTablet: width >= MOBILE_BREAKPOINT && width < TABLET_BREAKPOINT,
        isDesktop: width >= TABLET_BREAKPOINT,
        width,
      })
    }

    // Use resize observer for better performance
    window.addEventListener('resize', handleResize)

    // Initial check
    handleResize()

    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return state
}
