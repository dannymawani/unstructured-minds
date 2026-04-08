import { useState, useCallback, useEffect, useRef, forwardRef } from 'react'
import { cn } from '@/lib/utils'
import { X, ChevronLeft, ArrowRight, Loader2, CheckSquare, Square, AlertTriangle, Clock, ArrowRightCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DailyNoteWizardProps {
  isOpen: boolean
  onClose: () => void
  onComplete: (content: string, selectedTaskIds?: string[]) => void
  noteContent: string
  date: string
  apiBaseUrl?: string
}

interface ActivityOption {
  id: string
  label: string
  emoji: string
}

const ACTIVITY_OPTIONS: ActivityOption[] = [
  { id: 'strength', label: 'Strength', emoji: '🏋️' },
  { id: 'running', label: 'Running', emoji: '🏃' },
  { id: 'cycling', label: 'Cycling', emoji: '🚴' },
  { id: 'swimming', label: 'Swimming', emoji: '🏊' },
  { id: 'hiit', label: 'HIIT', emoji: '⚡' },
  { id: 'yoga', label: 'Yoga', emoji: '🧘' },
  { id: 'sports', label: 'Sports', emoji: '🎾' },
  { id: 'martial_arts', label: 'Martial Arts', emoji: '🥋' },
  { id: 'walking', label: 'Walking', emoji: '🚶' },
  { id: 'other', label: 'Other', emoji: '💪' },
]

interface WorkoutSuggestion {
  date: string | null
  exercises: {
    exercise_name: string
    display_name: string
    sets: number
    reps: number | null
    weight_kg: number | null
    suggested_weight_kg: number | null
  }[]
  focus: string | null
}

interface RolloverTask {
  id: string
  date: string
  description: string
  status: string
  category: string | null
  priority: number | null
  deadline: string | null
  deadline_status: string | null
  auto_select: boolean
}

interface WizardAnswers {
  activities: Set<string>
  activityDetails: string
  isRestDay: boolean
  sleep: number | null
  energy: number | null
  mood: number | null
  workPriorities: string
  personal: string
  adhoc: string
  workoutSuggestion: WorkoutSuggestion | null
  rolloverTasks: RolloverTask[]
  selectedRolloverIds: Set<string>
}

const TOTAL_STEPS = 6

function makeInitialAnswers(): WizardAnswers {
  return {
    activities: new Set(),
    activityDetails: '',
    isRestDay: false,
    sleep: null,
    energy: null,
    mood: null,
    workPriorities: '',
    personal: '',
    adhoc: '',
    workoutSuggestion: null,
    rolloverTasks: [],
    selectedRolloverIds: new Set(),
  }
}

export function DailyNoteWizard({ isOpen, onClose, onComplete, noteContent, date, apiBaseUrl }: DailyNoteWizardProps) {
  const [step, setStep] = useState(1)
  const [answers, setAnswers] = useState<WizardAnswers>(makeInitialAnswers)
  const [isPopulating, setIsPopulating] = useState(false)
  const [rolloverLoading, setRolloverLoading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Fetch rollover tasks when wizard opens
  useEffect(() => {
    if (!isOpen || !apiBaseUrl) return

    setRolloverLoading(true)
    fetch(`${apiBaseUrl}/tasks/rollover?target_date=${date}`)
      .then(res => res.ok ? res.json() : null)
      .then((data: { tasks: RolloverTask[]; total: number } | null) => {
        if (data && data.tasks.length > 0) {
          const autoSelected = new Set(
            data.tasks.filter(t => t.auto_select).map(t => t.id)
          )
          setAnswers(a => ({
            ...a,
            rolloverTasks: data.tasks,
            selectedRolloverIds: autoSelected,
          }))
        } else {
          setAnswers(a => ({ ...a, rolloverTasks: [], selectedRolloverIds: new Set() }))
          setStep(2)
        }
      })
      .catch(() => {
        setAnswers(a => ({ ...a, rolloverTasks: [], selectedRolloverIds: new Set() }))
        setStep(2)
      })
      .finally(() => setRolloverLoading(false))
  }, [isOpen, apiBaseUrl, date])

  // Reset when opening
  useEffect(() => {
    if (isOpen) {
      setStep(1)
      setAnswers(makeInitialAnswers())
    }
  }, [isOpen])

  // Fetch last strength workout when Strength is selected
  const fetchWorkoutSuggestion = useCallback(async () => {
    if (!apiBaseUrl) return
    try {
      const res = await fetch(`${apiBaseUrl}/dashboard/last-strength-workout`)
      if (res.ok) {
        const data: WorkoutSuggestion = await res.json()
        if (data.exercises.length > 0) {
          setAnswers(a => ({ ...a, workoutSuggestion: data }))
        }
      }
    } catch {
      // Silently fail - suggestion is optional
    }
  }, [apiBaseUrl])

  // Focus textarea when reaching text steps
  useEffect(() => {
    if (isOpen && step >= 4) {
      setTimeout(() => textareaRef.current?.focus(), 50)
    }
  }, [isOpen, step])

  const goNext = useCallback(async () => {
    if (step < TOTAL_STEPS) {
      setStep(s => s + 1)
    } else {
      // Final step — populate via API, fall back to client-side
      setIsPopulating(true)

      const selectedRolloverTasks = answers.rolloverTasks
        .filter(t => answers.selectedRolloverIds.has(t.id))
        .map(t => ({
          description: t.description,
          deadline: t.deadline,
          deadline_status: t.deadline_status,
        }))

      // Build workout string for backend
      let workoutStr: string | null = null
      if (answers.isRestDay) {
        workoutStr = 'Rest'
      } else if (answers.activities.size > 0) {
        workoutStr = [...answers.activities]
          .map(id => ACTIVITY_OPTIONS.find(a => a.id === id)?.label ?? id)
          .join(', ')
      }

      try {
        if (apiBaseUrl) {
          const res = await fetch(`${apiBaseUrl}/calendar/daily-note/populate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              date,
              template: noteContent,
              workout: workoutStr,
              activity_details: answers.activityDetails || null,
              sleep: answers.sleep,
              energy: answers.energy,
              mood: answers.mood,
              work_priorities: answers.workPriorities,
              personal: answers.personal,
              adhoc: answers.adhoc,
              workout_suggestion: answers.workoutSuggestion,
              rollover_tasks: selectedRolloverTasks.length > 0 ? selectedRolloverTasks : null,
            }),
          })
          if (res.ok) {
            const data = await res.json()
            const selectedIds = [...answers.selectedRolloverIds]
            onComplete(data.content, selectedIds.length > 0 ? selectedIds : undefined)
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
      const selectedIds = [...answers.selectedRolloverIds]
      onComplete(populated, selectedIds.length > 0 ? selectedIds : undefined)
    }
  }, [step, noteContent, answers, onComplete, apiBaseUrl, date])

  const goBack = useCallback(() => {
    if (step > 1) {
      // Skip rollover step when going back if there are no tasks
      if (step === 2 && answers.rolloverTasks.length === 0) return
      setStep(s => s - 1)
    }
  }, [step, answers.rolloverTasks.length])

  // Handle Enter key in textareas to advance
  const handleTextareaKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      goNext()
    }
  }, [goNext])

  if (!isOpen) return null

  const formattedDate = formatDate(date)
  const displayStep = answers.rolloverTasks.length === 0 ? step - 1 : step
  const displayTotal = answers.rolloverTasks.length === 0 ? TOTAL_STEPS - 1 : TOTAL_STEPS

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
            {Array.from({ length: displayTotal }, (_, i) => (
              <div
                key={i}
                className={cn(
                  'h-1 flex-1 rounded-full transition-colors',
                  i < displayStep ? 'bg-primary' : 'bg-muted'
                )}
              />
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-1.5">Step {displayStep} of {displayTotal}</p>
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
            <StepRollover
              tasks={answers.rolloverTasks}
              selectedIds={answers.selectedRolloverIds}
              loading={rolloverLoading}
              onChange={(ids) => setAnswers(a => ({ ...a, selectedRolloverIds: ids }))}
            />
          )}
          {step === 2 && (
            <StepCheckin
              sleep={answers.sleep}
              energy={answers.energy}
              mood={answers.mood}
              onChange={({ sleep, energy, mood }) => setAnswers(a => ({ ...a, sleep, energy, mood }))}
            />
          )}
          {step === 3 && (
            <StepActivity
              activities={answers.activities}
              isRestDay={answers.isRestDay}
              activityDetails={answers.activityDetails}
              onChange={(updates) => setAnswers(a => ({ ...a, ...updates }))}
              onFetchSuggestion={fetchWorkoutSuggestion}
              onKeyDown={handleTextareaKeyDown}
            />
          )}
          {step === 4 && (
            <StepText
              question="What are your work priorities today?"
              placeholder="e.g. Finish API integration, review PR #42, standup at 10am..."
              value={answers.workPriorities}
              onChange={(v) => setAnswers(a => ({ ...a, workPriorities: v }))}
              onKeyDown={handleTextareaKeyDown}
              ref={textareaRef}
            />
          )}
          {step === 5 && (
            <StepText
              question="Any personal items for today?"
              placeholder="e.g. Grocery shopping, call dentist, pick up package..."
              value={answers.personal}
              onChange={(v) => setAnswers(a => ({ ...a, personal: v }))}
              onKeyDown={handleTextareaKeyDown}
              ref={textareaRef}
            />
          )}
          {step === 6 && (
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
            disabled={step === 1 || (step === 2 && answers.rolloverTasks.length === 0)}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>

          <div className="flex gap-2">
            {step === 1 && answers.rolloverTasks.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => {
                setAnswers(a => ({ ...a, selectedRolloverIds: new Set() }))
                setStep(2)
              }}>
                Skip
              </Button>
            )}
            {step === TOTAL_STEPS && (
              <Button variant="ghost" size="sm" onClick={goNext}>
                Skip
              </Button>
            )}
            <Button size="sm" onClick={goNext} className="gap-1">
              {step === TOTAL_STEPS ? 'Finish' : 'Next'}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Sub-components ---

function StepRollover({
  tasks,
  selectedIds,
  loading,
  onChange,
}: {
  tasks: RolloverTask[]
  selectedIds: Set<string>
  loading: boolean
  onChange: (ids: Set<string>) => void
}) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Checking for pending tasks...</p>
      </div>
    )
  }

  if (tasks.length === 0) return null

  const allSelected = tasks.every(t => selectedIds.has(t.id))

  const toggleAll = () => {
    if (allSelected) {
      onChange(new Set())
    } else {
      onChange(new Set(tasks.map(t => t.id)))
    }
  }

  const toggleTask = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    onChange(next)
  }

  return (
    <div className="flex flex-col gap-3 py-2 flex-1">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-medium">Carry forward tasks?</h3>
        <button
          onClick={toggleAll}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {allSelected ? 'Deselect all' : 'Select all'}
        </button>
      </div>
      <p className="text-sm text-muted-foreground">
        {tasks.length} pending task{tasks.length !== 1 ? 's' : ''} from previous days
      </p>

      <div className="flex flex-col gap-1 max-h-[250px] overflow-y-auto pr-1">
        {tasks.map((task) => {
          const isSelected = selectedIds.has(task.id)
          return (
            <button
              key={task.id}
              onClick={() => toggleTask(task.id)}
              className={cn(
                'flex items-start gap-2.5 px-3 py-2 rounded-lg text-left transition-all text-sm',
                'hover:bg-accent/50',
                isSelected ? 'bg-primary/5 border border-primary/20' : 'bg-card border border-transparent'
              )}
            >
              {isSelected
                ? <CheckSquare className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                : <Square className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              }
              <div className="flex-1 min-w-0">
                <span className="block truncate">{task.description}</span>
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  {task.deadline_status === 'overdue' && (
                    <span className="inline-flex items-center gap-1 text-xs text-rose-500 font-medium">
                      <AlertTriangle className="h-3 w-3" />
                      Overdue
                    </span>
                  )}
                  {task.deadline_status === 'due_today' && (
                    <span className="inline-flex items-center gap-1 text-xs text-amber-500 font-medium">
                      <Clock className="h-3 w-3" />
                      Due today
                    </span>
                  )}
                  {task.deadline_status === 'upcoming' && task.deadline && (
                    <span className="text-xs text-muted-foreground">
                      Due {formatShortDate(task.deadline)}
                    </span>
                  )}
                  {task.status === 'in_progress' && (
                    <span className="inline-flex items-center gap-1 text-xs text-blue-500 font-medium">
                      <ArrowRightCircle className="h-3 w-3" />
                      In progress
                    </span>
                  )}
                  {task.category && (
                    <span className="text-xs text-muted-foreground">{task.category}</span>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {selectedIds.size === 0 && (
        <p className="text-xs text-muted-foreground mt-1">No tasks selected — skip or select some to carry forward</p>
      )}
    </div>
  )
}

function StepCheckin({
  sleep,
  energy,
  mood,
  onChange,
}: {
  sleep: number | null
  energy: number | null
  mood: number | null
  onChange: (values: { sleep: number | null; energy: number | null; mood: number | null }) => void
}) {
  return (
    <div className="flex flex-col gap-5 py-2">
      <div>
        <h3 className="text-xl font-medium">Quick check-in</h3>
        <p className="text-sm text-muted-foreground mt-1">Tap to rate, tap again to clear</p>
      </div>
      <RatingRow
        label="Sleep"
        value={sleep}
        onChange={(v) => onChange({ sleep: v, energy, mood })}
      />
      <RatingRow
        label="Energy"
        value={energy}
        onChange={(v) => onChange({ sleep, energy: v, mood })}
      />
      <RatingRow
        label="Mood"
        value={mood}
        onChange={(v) => onChange({ sleep, energy, mood: v })}
      />
    </div>
  )
}

function RatingRow({
  label,
  value,
  onChange,
}: {
  label: string
  value: number | null
  onChange: (v: number | null) => void
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
        {value !== null && (
          <span className="text-xs text-muted-foreground">{value}/10</span>
        )}
      </div>
      <div className="flex gap-1">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
          <button
            key={n}
            onClick={() => onChange(value === n ? null : n)}
            className={cn(
              'flex-1 h-8 rounded text-xs font-medium transition-all',
              value === n
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground'
            )}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  )
}

function StepActivity({
  activities,
  isRestDay,
  activityDetails,
  onChange,
  onFetchSuggestion,
  onKeyDown,
}: {
  activities: Set<string>
  isRestDay: boolean
  activityDetails: string
  onChange: (updates: Partial<Pick<WizardAnswers, 'activities' | 'isRestDay' | 'activityDetails'>>) => void
  onFetchSuggestion: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
}) {
  const toggleActivity = (id: string) => {
    const next = new Set(activities)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
      if (id === 'strength') {
        onFetchSuggestion()
      }
    }
    onChange({ activities: next, isRestDay: false })
  }

  const toggleRestDay = () => {
    if (isRestDay) {
      onChange({ isRestDay: false })
    } else {
      onChange({ activities: new Set(), isRestDay: true, activityDetails: '' })
    }
  }

  return (
    <div className="flex flex-col gap-4 py-2 flex-1">
      <h3 className="text-xl font-medium">Any training or activity?</h3>

      <div className="grid grid-cols-5 gap-2">
        {ACTIVITY_OPTIONS.map(({ id, label, emoji }) => (
          <button
            key={id}
            onClick={() => toggleActivity(id)}
            className={cn(
              'flex flex-col items-center gap-1 px-1 py-2.5 rounded-lg border transition-all text-xs',
              'hover:border-primary/50 hover:bg-primary/5',
              activities.has(id)
                ? 'border-primary bg-primary/10 text-primary font-medium'
                : 'border-border bg-card'
            )}
          >
            <span className="text-lg">{emoji}</span>
            <span className="truncate w-full text-center leading-tight">{label}</span>
          </button>
        ))}
      </div>

      <button
        onClick={toggleRestDay}
        className={cn(
          'flex items-center justify-center gap-2 px-3 py-2 rounded-lg border transition-all text-sm',
          isRestDay
            ? 'border-primary bg-primary/10 text-primary font-medium'
            : 'border-border bg-card hover:border-primary/50 hover:bg-primary/5'
        )}
      >
        <span>😴</span>
        <span>Rest Day</span>
      </button>

      {activities.size > 0 && !isRestDay && (
        <textarea
          value={activityDetails}
          onChange={(e) => onChange({ activityDetails: e.target.value })}
          onKeyDown={onKeyDown}
          placeholder="Add details about your session (optional)"
          className="min-h-[60px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        />
      )}

      {!isRestDay && activities.size === 0 && (
        <p className="text-xs text-muted-foreground">Select activities or skip to continue</p>
      )}
    </div>
  )
}

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

  // Carried Forward tasks — insert before Today's Focus
  const selectedTasks = answers.rolloverTasks.filter(t => answers.selectedRolloverIds.has(t.id))
  if (selectedTasks.length > 0) {
    const lines = ['## Carried Forward\n']
    for (const task of selectedTasks) {
      let desc = task.description
      if (task.deadline_status === 'overdue' && task.deadline) {
        desc += ` (Overdue: ${formatShortDate(task.deadline)})`
      } else if (task.deadline_status === 'due_today') {
        desc += ' (Due today)'
      } else if (task.deadline_status === 'upcoming' && task.deadline) {
        desc += ` (${formatShortDate(task.deadline)})`
      }
      lines.push(`- [ ] ${desc}`)
    }
    const carriedBlock = lines.join('\n') + '\n\n'

    const focusIdx = result.indexOf("## 🎯 Today's Focus")
    if (focusIdx !== -1) {
      result = result.slice(0, focusIdx) + carriedBlock + result.slice(focusIdx)
    } else {
      const firstSection = result.search(/^## /m)
      if (firstSection !== -1) {
        result = result.slice(0, firstSection) + carriedBlock + result.slice(firstSection)
      } else {
        result = result + '\n' + carriedBlock
      }
    }
  }

  // Activity
  if (answers.isRestDay) {
    result = result.replace(
      /[*-] \*\*Type\*\*:.*\n[*-] \*\*Focus\*\*:.*/,
      '- Rest day'
    )
  } else if (answers.activities.size > 0) {
    const typeStr = [...answers.activities]
      .map(id => ACTIVITY_OPTIONS.find(a => a.id === id)?.label ?? id)
      .join(', ')

    result = replaceLine(result, '- **Type**:', `- **Type**: ${typeStr}`)
    result = replaceLine(result, '* **Type**:', `* **Type**: ${typeStr}`)

    if (answers.activityDetails.trim()) {
      result = replaceLine(result, '- **Focus**:', `- **Focus**: ${answers.activityDetails.trim()}`)
      result = replaceLine(result, '* **Focus**:', `* **Focus**: ${answers.activityDetails.trim()}`)
    }

    // Add workout suggestion table for strength training
    if (answers.activities.has('strength') && answers.workoutSuggestion?.exercises.length) {
      const suggestion = answers.workoutSuggestion
      const dateStr = suggestion.date ? ` ${suggestion.date}` : ''
      const tableLines = [
        '',
        `> **Suggested Workout (from${dateStr})** — edit below to log, or delete if skipping`,
        '> ',
        '> | Exercise | Last | Suggested | Reps | Sets |',
        '> |----------|------|-----------|------|------|',
      ]
      for (const ex of suggestion.exercises) {
        const name = ex.display_name || ex.exercise_name
        const lastW = ex.weight_kg && ex.weight_kg > 0 ? `${ex.weight_kg}kg` : 'BW'
        const suggW = ex.suggested_weight_kg ? `${ex.suggested_weight_kg}kg` : lastW
        const reps = ex.reps ? String(ex.reps) : '-'
        const sets = ex.sets ? String(ex.sets) : '-'
        tableLines.push(`> | ${name} | ${lastW} | ${suggW} | ${reps} | ${sets} |`)
      }
      tableLines.push('')
      const suggestionBlock = tableLines.join('\n')

      const focusIdx = result.indexOf('- **Focus**:')
      const focusIdxAlt = result.indexOf('* **Focus**:')
      const insertIdx = focusIdx !== -1 ? focusIdx : focusIdxAlt
      if (insertIdx !== -1) {
        const lineEnd = result.indexOf('\n', insertIdx)
        if (lineEnd !== -1) {
          result = result.slice(0, lineEnd + 1) + suggestionBlock + result.slice(lineEnd + 1)
        }
      }
    }
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

    const items = answers.workPriorities
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean)
    if (items.length > 0) {
      const checkboxes = items.map(item => `- [ ] ${item}`).join('\n')
      result = replaceSection(result, "## 🎯 Today's Focus", checkboxes)
    }
  }

  // Personal items
  if (answers.personal.trim()) {
    result = insertAfterHeader(result, '## 🤷🏽 Personal', answers.personal.trim())
  }

  // Adhoc notes
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

function formatShortDate(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number)
  const d = new Date(year, month - 1, day)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
