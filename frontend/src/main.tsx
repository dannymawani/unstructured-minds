import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { ClerkProvider } from '@clerk/clerk-react'
import './index.css'
import App from './App.tsx'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

const app = (
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)

createRoot(document.getElementById('root')!).render(
  PUBLISHABLE_KEY
    ? <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">{app}</ClerkProvider>
    : app,
)
