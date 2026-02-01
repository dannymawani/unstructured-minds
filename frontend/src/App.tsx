import { Button } from "@/components/ui/button"

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b px-4 py-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Unstructured Minds</h1>
        <Button variant="outline" size="sm">
          Settings
        </Button>
      </header>

      {/* Main content */}
      <main className="flex-1 flex">
        {/* Sidebar placeholder */}
        <aside className="w-64 border-r p-4">
          <p className="text-sm text-muted-foreground">File browser</p>
        </aside>

        {/* Editor placeholder */}
        <section className="flex-1 p-4">
          <p className="text-sm text-muted-foreground">Editor</p>
        </section>

        {/* Chat panel placeholder */}
        <aside className="w-80 border-l p-4">
          <p className="text-sm text-muted-foreground">Chat</p>
        </aside>
      </main>
    </div>
  )
}

export default App
