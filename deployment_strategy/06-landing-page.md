# 06 - Landing Page

## URL Structure

```
unstructuredminds.com/           → Landing page (public)
unstructuredminds.com/pricing    → Pricing page (public)
unstructuredminds.com/login      → Clerk sign-in (public)
unstructuredminds.com/app        → Main app (authenticated)
unstructuredminds.com/app/*      → All app routes (authenticated)
```

## Landing Page Sections

### Above the Fold (Hero)

```
┌─────────────────────────────────────────────────────────────┐
│  UM                                    [Login]  [Get Started]│
│                                                              │
│                                                              │
│        Your thoughts, structured.                            │
│        Your data, queryable.                                 │
│                                                              │
│        Write in natural language.                            │
│        AI extracts the structure.                            │
│        Ask questions. Get answers.                           │
│                                                              │
│              [Get Started Free →]                            │
│              No credit card required                         │
│                                                              │
│        ┌──────────────────────────────────┐                  │
│        │  (Screenshot/demo of the app)    │                  │
│        │  Dark theme, editor + dashboard  │                  │
│        │  Animated or video               │                  │
│        └──────────────────────────────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Headline**: "Your thoughts, structured. Your data, queryable."
**Sub**: One line explaining the concept.
**CTA**: "Get Started Free" → Clerk signup with Google.

### How It Works (3 Steps)

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│                    How it works                              │
│                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │  1.Write  │    │2.Extract │    │ 3.Query  │             │
│   │          │    │          │    │          │             │
│   │ Write    │    │ AI pulls │    │ Ask any  │             │
│   │ your     │    │ out the  │    │ question │             │
│   │ notes    │    │ data     │    │ about    │             │
│   │ naturally│    │ points   │    │ your     │             │
│   │          │    │          │    │ data     │             │
│   └──────────┘    └──────────┘    └──────────┘             │
│                                                              │
│   "Trained legs today.     →  exercise: squats    "How much │
│    Squats 3x8 at 225.         weight: 225 lbs     did I     │
│    Felt great."                reps: 8, sets: 3    squat     │
│                                                    last      │
│                                                    month?"   │
│                                                    → Chart   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Feature Highlights

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌────────────────────┐  ┌────────────────────┐             │
│  │ Rich Editor         │  │ Smart Extraction    │             │
│  │ Milkdown-powered    │  │ Claude AI reads     │             │
│  │ markdown editor     │  │ your notes and      │             │
│  │ with templates,     │  │ extracts workouts,  │             │
│  │ WYSIWYG toolbar,    │  │ meals, moods,       │             │
│  │ and autosave        │  │ tasks, and more     │             │
│  └────────────────────┘  └────────────────────┘             │
│                                                              │
│  ┌────────────────────┐  ┌────────────────────┐             │
│  │ Visual Dashboard    │  │ Your Data, Your     │             │
│  │ Charts, heatmaps,   │  │ Control             │             │
│  │ trends. See your    │  │ Notes stored in     │             │
│  │ life data at a      │  │ YOUR Google Drive.  │             │
│  │ glance.             │  │ Export anytime.     │             │
│  └────────────────────┘  └────────────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

Key features to highlight:
1. **Rich markdown editor** - Write naturally, not in forms
2. **AI extraction** - Turns prose into structured data automatically
3. **Natural language queries** - "How did I sleep this week?" → chart
4. **Dashboard** - Visual analytics of your life data
5. **Your data** - Stored in your Google Drive, export anytime
6. **Privacy** - Your notes are yours. No shared databases.

### Use Cases

```
"I use it for..."

🏋️ Fitness Tracking       → Log workouts in prose, get progression charts
😴 Sleep & Wellness        → Track sleep, energy, mood over time
🍽️ Nutrition              → Log meals naturally, see macro trends
📋 Task Management         → Capture tasks in notes, see them on kanban
📊 Life Analytics          → Ask questions about any aspect of your daily life
```

### Social Proof (Later)

```
"Trusted by X people tracking their lives"

[Testimonial cards - add after launch]
```

### Pricing Section

```
┌─────────────────────────────────────────────────────────────┐
│                        Pricing                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Free       │  │   BYO Key    │  │     Pro      │      │
│  │              │  │              │  │              │      │
│  │  $0/month    │  │  $0/month    │  │  $12/month   │      │
│  │              │  │              │  │              │      │
│  │ 50 AI ops    │  │ Unlimited    │  │ 500 AI ops   │      │
│  │ Google login │  │ Your API key │  │ Priority     │      │
│  │ Google Drive │  │ All features │  │ All features │      │
│  │ Dashboard    │  │ Full control │  │ Support      │      │
│  │              │  │              │  │              │      │
│  │ [Start Free] │  │ [Start Free] │  │ [Go Pro]     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Footer

```
┌─────────────────────────────────────────────────────────────┐
│  Unstructured Minds                                         │
│                                                              │
│  Product        Resources        Legal                      │
│  Features       Docs             Privacy Policy             │
│  Pricing        Blog             Terms of Service           │
│  Changelog      GitHub           Cookie Policy              │
│                                                              │
│  © 2026 Unstructured Minds. Your data, structured.          │
└─────────────────────────────────────────────────────────────┘
```

## Copy Guidelines

- **Tone**: Confident but approachable. Not corporate. Not overly casual.
- **Voice**: Second person ("your notes", "your data"). Direct.
- **Avoid**: "Revolutionary", "game-changing", "leverage", "synergy". Just explain what it does.
- **Emphasize**: Privacy, ownership, simplicity, power of natural language.

## Technical Implementation

The landing page is part of the same React SPA. New routes, no separate project.

```tsx
// New files to create:
src/
├── pages/
│   ├── Landing.tsx           // Main landing page
│   ├── Pricing.tsx           // Pricing breakdown
│   └── Login.tsx             // Clerk sign-in wrapper
├── components/
│   └── landing/
│       ├── Hero.tsx
│       ├── HowItWorks.tsx
│       ├── Features.tsx
│       ├── UseCases.tsx
│       ├── PricingCards.tsx
│       └── Footer.tsx
```

### SEO Considerations

Since this is a Vite SPA (not SSR), we need:

1. **Pre-rendering** for the landing page (Vite plugin: `vite-plugin-ssr` or `vite-ssg`)
2. **Meta tags** via `react-helmet-async`
3. **Open Graph tags** for social sharing
4. **Sitemap** generation

```tsx
// Landing.tsx
import { Helmet } from 'react-helmet-async'

function Landing() {
  return (
    <>
      <Helmet>
        <title>Unstructured Minds - Your thoughts, structured</title>
        <meta name="description" content="Write naturally. AI extracts the data. Query your life." />
        <meta property="og:title" content="Unstructured Minds" />
        <meta property="og:description" content="Turn natural language notes into queryable data" />
        <meta property="og:image" content="https://unstructuredminds.com/og-image.png" />
      </Helmet>
      <Hero />
      <HowItWorks />
      <Features />
      <UseCases />
      <PricingCards />
      <Footer />
    </>
  )
}
```

### Performance

- Landing page should load in <2 seconds
- Lazy-load the app bundle (don't ship editor code on landing page)
- Use Vercel's edge CDN for static assets
- Optimize images with `@vercel/og` for dynamic OG images

## Design

Use the existing brand colors from CLAUDE.md:

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark slate | `#0f172a` |
| Text | Light | `#f8fafc` |
| CTA buttons | Teal | `#14b8a6` |
| Links | Indigo | `#6366f1` |
| Highlights | Amber | `#f59e0b` |
| Destructive | Rose | `#f43f5e` |

Dark theme by default (matches the app). Optional light mode toggle on landing page.
