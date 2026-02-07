import { useState, useCallback, useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { X, ChevronLeft, ArrowRight, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DailyNoteWizardProps {
  isOpen: boolean
  onClose: () => void
  onComplete: (content: string) => void
  noteContent: string
  date: string
  apiBaseUrl?: string
}

type WorkoutType = 'BJJ' | 'Strength' | 'Cardio' | 'Rest'

interface WizardAnswers {
  workout: WorkoutType | null
  sleep: number | null
  energy: number | null
  mood: number | null
  workPriorities: string
  personal: string
  adhoc: string
}

const TOTAL_STEPS = 7

export function DailyNoteWizard({ isOpen, onClose, onComplete, noteContent, date, apiBaseUrl }: DailyNoteWizardProps) {
  const [step, setStep] = useState(1)
  const [answers, setAnswers] = useState<WizardAnswers>({
    workout: null,
    sleep: null,
    energy: null,
    mood: null,
    workPriorities: '',
    personal: '',
    adhoc: '',
  })
  const [isPopulating, setIsPopulating] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Reset when opening
  useEffect(() => {
    if (isOpen) {
      setStep(1)
      setAnswers({
        workout: null,
        sleep: null,
        energy: null,
        mood: null,
        workPriorities: '',
        personal: '',
        adhoc: '',
      })
    }
  }, [isOpen])

  // Focus textarea when reaching text steps
  useEffect(() => {
    if (isOpen && step >= 5) {
      setTimeout(() => textareaRef.current?.focus(), 50)
    }
  }, [isOpen, step])

  const goNext = useCallback(async () => {
    if (step < TOTAL_STEPS) {
      setStep(s => s + 1)
    } else {
      // Final step — populate via API, fall back to client-side
      setIsPopulating(true)
      try {
        if (apiBaseUrl) {
          const res = await fetch(`${apiBaseUrl}/calendar/daily-note/populate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              date,
              template: noteContent,
              workout: answers.workout,
              sleep: answers.sleep,
              energy: answers.energy,
              mood: answers.mood,
              work_priorities: answers.workPriorities,
              personal: answers.personal,
              adhoc: answers.adhoc,
            }),
          })
          if (res.ok) {
            const data = await res.json()
            onComplete(data.content)
            return
          }
        }
      } catch {
        // Fall through to client-side fallback
      } finally {
        setIsPopulating(false)
      }

      // Client-side fallback
      const populated = populateNote(noteContent, answers)
      onComplete(populated)
    }
  }, [step, noteContent, answers, onComplete, apiBaseUrl, date])

  const goBack = useCallback(() => {
    if (step > 1) setStep(s => s - 1)
  }, [step])

  // Handle Enter key in textareas to advance
  const handleTextareaKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      goNext()
    }
  }, [goNext])

  if (!isOpen) return null

  const formattedDate = formatDate(date)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-card rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden border border-border/50 relative">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <div>
            <h2 className="text-lg font-semibold">Daily Note</h2>
            <p className="text-sm text-muted-foreground">{formattedDate}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Progress bar */}
        <div className="px-6 pb-4">
          <div className="flex items-center gap-1.5">
            {Array.from({ length: TOTAL_STEPS }, (_, i) => (
              <div
                key={i}
                className={cn(
                  'h-1 flex-1 rounded-full transition-colors',
                  i < step ? 'bg-primary' : 'bg-muted'
                )}
              />
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-1.5">Step {step} of {TOTAL_STEPS}</p>
        </div>

        {/* Populating overlay */}
        {isPopulating && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-card/90 rounded-xl">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
            <p className="text-sm text-muted-foreground">Formatting your daily note...</p>
          </div>
        )}

        {/* Step content */}
        <div className="px-6 pb-6 min-h-[200px] flex flex-col">
          {step === 1 && (
            <StepWorkout
              value={answers.workout}
              onChange={(v) => {
                setAnswers(a => ({ ...a, workout: v }))
                // Auto-advance after selection
                setTimeout(() => setStep(2), 200)
              }}
            />
          )}
          {step === 2 && (
            <StepNumber
              question="How did you sleep?"
              label="Sleep rating"
              value={answers.sleep}
              onChange={(v) => {
                setAnswers(a => ({ ...a, sleep: v }))
                setTimeout(() => setStep(3), 200)
              }}
            />
          )}
          {step === 3 && (
            <StepNumber
              question="What's your energy level?"
              label="Energy"
              value={answers.energy}
              onChange={(v) => {
                setAnswers(a => ({ ...a, energy: v }))
                setTimeout(() => setStep(4), 200)
              }}
            />
          )}
          {step === 4 && (
            <StepNumber
              question="How's your mood?"
              label="Mood"
              value={answers.mood}
              onChange={(v) => {
                setAnswers(a => ({ ...a, mood: v }))
                setTimeout(() => setStep(5), 200)
              }}
            />
          )}
          {step === 5 && (
            <StepText
              question="What are your work priorities today?"
              placeholder="e.g. Finish API integration, review PR #42, standup at 10am..."
              value={answers.workPriorities}
              onChange={(v) => setAnswers(a => ({ ...a, workPriorities: v }))}
              onKeyDown={handleTextareaKeyDown}
              ref={textareaRef}
            />
          )}
          {step === 6 && (
            <StepText
              question="Any personal items for today?"
              placeholder="e.g. Grocery shopping, call dentist, pick up package..."
              value={answers.personal}
              onChange={(v) => setAnswers(a => ({ ...a, personal: v }))}
              onKeyDown={handleTextareaKeyDown}
              ref={textareaRef}
            />
          )}
          {step === 7 && (
            <StepText
              question="Anything else on your mind?"
              placeholder="Free-form notes, thoughts, ideas..."
              value={answers.adhoc}
              onChange={(v) => setAnswers(a => ({ ...a, adhoc: v }))}
              onKeyDown={handleTextareaKeyDown}
              ref={textareaRef}
              optional
            />
          )}
        </div>

        {/* Footer navigation */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border/50 bg-muted/30">
          <Button
            variant="ghost"
            size="sm"
            onClick={goBack}
            disabled={step === 1}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>

          <div className="flex gap-2">
            {step === 7 && (
              <Button variant="ghost" size="sm" onClick={goNext}>
                Skip
              </Button>
            )}
            {step >= 5 && (
              <Button size="sm" onClick={goNext} className="gap-1">
                {step === TOTAL_STEPS ? 'Finish' : 'Next'}
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Sub-components ---

function StepWorkout({ value, onChange }: { value: WorkoutType | null; onChange: (v: WorkoutType) => void }) {
  const options: { type: WorkoutType; emoji: string }[] = [
    { type: 'BJJ', emoji: '🥋' },
    { type: 'Strength', emoji: '🏋️' },
    { type: 'Cardio', emoji: '🏃' },
    { type: 'Rest', emoji: '😴' },
  ]

  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <h3 className="text-xl font-medium text-center">Any workout planned?</h3>
      <div className="grid grid-cols-2 gap-3 w-full max-w-xs">
        {options.map(({ type, emoji }) => (
          <button
            key={type}
            onClick={() => onChange(type)}
            className={cn(
              'flex flex-col items-center gap-2 px-4 py-4 rounded-lg border-2 transition-all',
              'hover:border-primary hover:bg-primary/5',
              value === type
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border bg-card'
            )}
          >
            <span className="text-2xl">{emoji}</span>
            <span className="text-sm font-medium">{type}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function StepNumber({
  question,
  label,
  value,
  onChange,
}: {
  question: string
  label: string
  value: number | null
  onChange: (v: number) => void
}) {
  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <h3 className="text-xl font-medium text-center">{question}</h3>
      <div className="flex flex-wrap justify-center gap-2">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
          <button
            key={n}
            onClick={() => onChange(n)}
            className={cn(
              'w-10 h-10 rounded-lg text-sm font-medium transition-all',
              'hover:border-primary hover:bg-primary/5 border-2',
              value === n
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border bg-card'
            )}
          >
            {n}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{label}: 1 = low, 10 = great</p>
    </div>
  )
}

import { forwardRef } from 'react'

const StepText = forwardRef<
  HTMLTextAreaElement,
  {
    question: string
    placeholder: string
    value: string
    onChange: (v: string) => void
    onKeyDown: (e: React.KeyboardEvent) => void
    optional?: boolean
  }
>(({ question, placeholder, value, onChange, onKeyDown, optional }, ref) => {
  return (
    <div className="flex flex-col gap-4 py-2 flex-1">
      <div>
        <h3 className="text-xl font-medium">{question}</h3>
        {optional && <p className="text-sm text-muted-foreground mt-1">Optional — skip if nothing comes to mind</p>}
      </div>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        className="flex-1 min-h-[100px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
      />
      <p className="text-xs text-muted-foreground">Press Cmd+Enter to continue</p>
    </div>
  )
})

StepText.displayName = 'StepText'

// --- Content population ---

function populateNote(content: string, answers: WizardAnswers): string {
  let result = content

  // Workout type
  if (answers.workout) {
    result = replaceLine(result, '- **Type**:', `- **Type**: ${answers.workout}`)
    // Also try the escaped Milkdown variant
    result = replaceLine(result, '* **Type**:', `* **Type**: ${answers.workout}`)
  }

  // Sleep
  if (answers.sleep !== null) {
    result = replaceLine(result, '- Sleep:', `- Sleep: ${answers.sleep}/10`)
    result = replaceLine(result, '* Sleep:', `* Sleep: ${answers.sleep}/10`)
  }

  // Energy
  if (answers.energy !== null) {
    result = replaceLine(result, '- Energy Level:', `- Energy Level: ${answers.energy}/10`)
    result = replaceLine(result, '* Energy Level:', `* Energy Level: ${answers.energy}/10`)
  }

  // Mood
  if (answers.mood !== null) {
    result = replaceLine(result, '- Mood:', `- Mood: ${answers.mood}/10`)
    result = replaceLine(result, '* Mood:', `* Mood: ${answers.mood}/10`)
  }

  // Work priorities — insert after "## 💼 Work" header
  if (answers.workPriorities.trim()) {
    result = insertAfterHeader(result, '## 💼 Work', answers.workPriorities.trim())

    // Also populate Today's Focus with checklist items from work priorities
    const items = answers.workPriorities
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean)
    if (items.length > 0) {
      const checkboxes = items.map(item => `- [ ] ${item}`).join('\n')
      result = replaceSection(result, "## 🎯 Today's Focus", checkboxes)
    }
  }

  // Personal items — insert after "## 🤷🏽 Personal" header
  if (answers.personal.trim()) {
    result = insertAfterHeader(result, '## 🤷🏽 Personal', answers.personal.trim())
  }

  // Adhoc notes — insert after "## 📝 Adhoc Notes" header
  if (answers.adhoc.trim()) {
    result = insertAfterHeader(result, '## 📝 Adhoc Notes', answers.adhoc.trim())
  }

  return result
}

/** Replace a line that starts with `prefix` (with optional trailing whitespace) */
function replaceLine(content: string, prefix: string, replacement: string): string {
  const regex = new RegExp(`^(${escapeRegex(prefix)})\\s*$`, 'm')
  return content.replace(regex, replacement)
}

/** Insert text after a markdown header line */
function insertAfterHeader(content: string, header: string, text: string): string {
  const idx = content.indexOf(header)
  if (idx === -1) return content

  // Find end of header line
  const lineEnd = content.indexOf('\n', idx)
  if (lineEnd === -1) return content + '\n' + text

  return content.slice(0, lineEnd + 1) + text + '\n' + content.slice(lineEnd + 1)
}

/** Replace the content between a header and the next header (or end) */
function replaceSection(content: string, header: string, newBody: string): string {
  const idx = content.indexOf(header)
  if (idx === -1) return content

  const lineEnd = content.indexOf('\n', idx)
  if (lineEnd === -1) return content

  // Find the next header (## or ---) or end of content
  const rest = content.slice(lineEnd + 1)
  const nextHeaderMatch = rest.match(/^(#{1,3} |\*{3}|---)/m)
  const nextHeaderIdx = nextHeaderMatch ? rest.indexOf(nextHeaderMatch[0]) : rest.length

  return content.slice(0, lineEnd + 1) + '\n' + newBody + '\n\n' + rest.slice(nextHeaderIdx)
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number)
  const d = new Date(year, month - 1, day)
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}
