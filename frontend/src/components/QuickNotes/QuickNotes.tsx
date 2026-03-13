import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { createPortal } from "react-dom";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  PenLine,
  Plus,
  Trash2,
  Filter,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/apiClient";
import { buildTree, flattenTree, type FileNode } from "@/components/FileTree";

const QUICK_NOTES_DIR = "Quick-Notes";

const EMOJI_GRID = [
  ["📝", "📋", "📎", "📌", "📚", "💡", "🎯", "💻", "🔧", "🛠️"],
  ["🍕", "🍔", "🍰", "🍪", "🥗", "🍳", "🍜", "🍣", "☕", "🍷"],
  ["🏠", "🌿", "🎵", "🎨", "✈️", "🏋️", "💊", "🧘", "🎮", "📷"],
  ["❤️", "⭐", "✨", "🔥", "⚡", "💎", "🎁", "🎉", "🚀", "✅"],
];

interface QuickNotesProps {
  onFileSelect: (path: string) => void;
  selectedFile?: string;
  refreshTrigger?: number;
}

function loadSectionExpanded(): boolean {
  try {
    const v = localStorage.getItem("quick-notes-section-expanded");
    return v !== null ? v === "true" : true;
  } catch {
    return true;
  }
}

function loadFolderExpanded(): Set<string> {
  try {
    const v = localStorage.getItem("quick-notes-folders-expanded");
    return v ? new Set(JSON.parse(v)) : new Set();
  } catch {
    return new Set();
  }
}

function loadIcons(): Record<string, string> {
  try {
    const v = localStorage.getItem("quick-notes-icons");
    return v ? JSON.parse(v) : {};
  } catch {
    return {};
  }
}

function saveIcons(icons: Record<string, string>) {
  localStorage.setItem("quick-notes-icons", JSON.stringify(icons));
}

function countNotes(node: FileNode): number {
  if (!node.isDirectory) return 1;
  return (node.children || []).reduce((sum, c) => sum + countNotes(c), 0);
}

function sortTree(nodes: FileNode[]): FileNode[] {
  const sorted = [...nodes].sort((a, b) => {
    if (a.isDirectory !== b.isDirectory) return a.isDirectory ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  for (const node of sorted) {
    if (node.children) node.children = sortTree(node.children);
  }
  return sorted;
}

function filterTree(nodes: FileNode[], query: string): FileNode[] {
  const q = query.toLowerCase();
  return nodes.reduce<FileNode[]>((acc, node) => {
    if (node.isDirectory) {
      const filtered = filterTree(node.children || [], query);
      if (filtered.length > 0) acc.push({ ...node, children: filtered });
    } else {
      if (node.name.toLowerCase().includes(q)) acc.push(node);
    }
    return acc;
  }, []);
}

export function QuickNotes({
  onFileSelect,
  selectedFile,
  refreshTrigger,
}: QuickNotesProps) {
  const [sectionExpanded, setSectionExpanded] = useState(loadSectionExpanded);
  const [expanded, setExpanded] = useState(loadFolderExpanded);
  const [isFilterVisible, setIsFilterVisible] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [tree, setTree] = useState<FileNode[]>([]);

  // Drag and drop state
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  // Icon state
  const [icons, setIcons] = useState<Record<string, string>>(loadIcons);
  const [iconPickerTarget, setIconPickerTarget] = useState<string | null>(null);
  const [iconPickerPos, setIconPickerPos] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const iconPickerRef = useRef<HTMLDivElement>(null);

  const filterRef = useRef<HTMLInputElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);

  // Persist section state
  useEffect(() => {
    localStorage.setItem(
      "quick-notes-section-expanded",
      String(sectionExpanded),
    );
  }, [sectionExpanded]);

  useEffect(() => {
    localStorage.setItem(
      "quick-notes-folders-expanded",
      JSON.stringify([...expanded]),
    );
  }, [expanded]);

  useEffect(() => {
    if (isFilterVisible) setTimeout(() => filterRef.current?.focus(), 10);
  }, [isFilterVisible]);

  useEffect(() => {
    if (isCreating) setTimeout(() => nameInputRef.current?.focus(), 10);
  }, [isCreating]);

  // Close icon picker on click outside
  useEffect(() => {
    if (!iconPickerTarget) return;
    const handle = (e: MouseEvent) => {
      if (
        iconPickerRef.current &&
        !iconPickerRef.current.contains(e.target as Node)
      ) {
        setIconPickerTarget(null);
        setIconPickerPos(null);
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [iconPickerTarget]);

  const fetchNotes = useCallback(async () => {
    try {
      const data = await api.get<{
        files: Array<{ path: string; name: string; is_directory: boolean }>;
      }>("/vault/files");
      const quickFiles = data.files.filter(
        (f) =>
          (f.path === QUICK_NOTES_DIR ||
            f.path.startsWith(QUICK_NOTES_DIR + "/")) &&
          f.name !== ".gitkeep",
      );
      const fullTree = buildTree(quickFiles);
      const root = fullTree.find((n) => n.path === QUICK_NOTES_DIR);
      setTree(sortTree(root?.children || []));
    } catch {
      /* silently fail */
    }
  }, []);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes, refreshTrigger]);

  const displayTree = useMemo(() => {
    if (!filterText.trim()) return tree;
    return filterTree(tree, filterText.trim());
  }, [tree, filterText]);

  const effectiveExpanded = useMemo(() => {
    if (filterText.trim()) {
      const all = new Set<string>();
      const addAll = (nodes: FileNode[]) => {
        for (const n of nodes) {
          if (n.isDirectory) {
            all.add(n.path);
            if (n.children) addAll(n.children);
          }
        }
      };
      addAll(displayTree);
      return all;
    }
    return expanded;
  }, [filterText, expanded, displayTree]);

  const flattened = useMemo(
    () => flattenTree(displayTree, effectiveExpanded),
    [displayTree, effectiveExpanded],
  );

  const toggleSection = useCallback(
    () => setSectionExpanded((prev) => !prev),
    [],
  );

  const toggleFolder = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const toggleFilter = useCallback(() => {
    setIsFilterVisible((prev) => {
      if (prev) setFilterText("");
      return !prev;
    });
  }, []);

  const cancelCreate = useCallback(() => {
    setIsCreating(false);
    setNewName("");
  }, []);

  const startCreate = useCallback(() => {
    setIsCreating(true);
    setNewName("");
  }, []);

  // Supports "name" or "folder/name" syntax
  const handleCreate = useCallback(async () => {
    const raw = newName.trim();
    if (!raw) {
      cancelCreate();
      return;
    }

    let folder = QUICK_NOTES_DIR;
    let title = raw;

    // If input contains a slash, treat prefix as folder
    const slashIdx = raw.lastIndexOf("/");
    if (slashIdx > 0) {
      folder = `${QUICK_NOTES_DIR}/${raw.slice(0, slashIdx)}`;
      title = raw.slice(slashIdx + 1);
    }
    if (!title) {
      cancelCreate();
      return;
    }

    const path = `${folder}/${title}.md`;
    try {
      await api.post("/vault/file", { path, content: `# ${title}\n\n` });
      cancelCreate();
      await fetchNotes();
      onFileSelect(path);
      if (folder !== QUICK_NOTES_DIR) {
        setExpanded((prev) => new Set(prev).add(folder));
      }
    } catch {
      /* silently fail */
    }
  }, [newName, cancelCreate, fetchNotes, onFileSelect]);

  const handleDelete = useCallback(
    async (path: string, e: React.MouseEvent) => {
      e.stopPropagation();
      if (deleteTarget !== path) {
        setDeleteTarget(path);
        return;
      }
      try {
        await api.delete(`/vault/file?path=${encodeURIComponent(path)}`);
        setDeleteTarget(null);
        // Clean up icon
        setIcons((prev) => {
          const next = { ...prev };
          delete next[path];
          saveIcons(next);
          return next;
        });
        await fetchNotes();
      } catch {
        /* silently fail */
      }
    },
    [deleteTarget, fetchNotes],
  );

  // Drag and drop handlers
  const handleDragStart = useCallback((e: React.DragEvent, path: string) => {
    e.dataTransfer.setData("text/plain", path);
    e.dataTransfer.effectAllowed = "move";
    setDraggedItem(path);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDraggedItem(null);
    setDropTarget(null);
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent, folderPath: string) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setDropTarget(folderPath);
    },
    [],
  );

  const handleDragLeave = useCallback(() => {
    setDropTarget(null);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent, targetFolderPath: string) => {
      e.preventDefault();
      setDropTarget(null);
      setDraggedItem(null);

      const sourcePath = e.dataTransfer.getData("text/plain");
      if (!sourcePath) return;

      const fileName = sourcePath.split("/").pop();
      if (!fileName) return;

      const newPath = `${targetFolderPath}/${fileName}`;
      if (newPath === sourcePath) return;

      try {
        await api.patch("/vault/file", {
          old_path: sourcePath,
          new_path: newPath,
        });
        // Update icon mapping
        if (icons[sourcePath]) {
          setIcons((prev) => {
            const next = { ...prev };
            next[newPath] = next[sourcePath];
            delete next[sourcePath];
            saveIcons(next);
            return next;
          });
        }
        await fetchNotes();
        setExpanded((prev) => new Set(prev).add(targetFolderPath));
      } catch {
        /* silently fail */
      }
    },
    [fetchNotes, icons],
  );

  // Drop on root (Quick-Notes/ level)
  const handleRootDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDropTarget(QUICK_NOTES_DIR);
  }, []);

  const handleRootDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setDropTarget(null);
      setDraggedItem(null);

      const sourcePath = e.dataTransfer.getData("text/plain");
      if (!sourcePath) return;

      const fileName = sourcePath.split("/").pop();
      if (!fileName) return;

      const newPath = `${QUICK_NOTES_DIR}/${fileName}`;
      if (newPath === sourcePath) return;

      try {
        await api.patch("/vault/file", {
          old_path: sourcePath,
          new_path: newPath,
        });
        if (icons[sourcePath]) {
          setIcons((prev) => {
            const next = { ...prev };
            next[newPath] = next[sourcePath];
            delete next[sourcePath];
            saveIcons(next);
            return next;
          });
        }
        await fetchNotes();
      } catch {
        /* silently fail */
      }
    },
    [fetchNotes, icons],
  );

  // Icon picker
  const openIconPicker = useCallback((e: React.MouseEvent, path: string) => {
    e.stopPropagation();
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setIconPickerTarget(path);
    setIconPickerPos({ x: rect.right + 4, y: rect.top });
  }, []);

  const selectIcon = useCallback(
    (emoji: string) => {
      if (!iconPickerTarget) return;
      setIcons((prev) => {
        const next = { ...prev, [iconPickerTarget]: emoji };
        saveIcons(next);
        return next;
      });
      setIconPickerTarget(null);
      setIconPickerPos(null);
    },
    [iconPickerTarget],
  );

  const clearIcon = useCallback(() => {
    if (!iconPickerTarget) return;
    setIcons((prev) => {
      const next = { ...prev };
      delete next[iconPickerTarget];
      saveIcons(next);
      return next;
    });
    setIconPickerTarget(null);
    setIconPickerPos(null);
  }, [iconPickerTarget]);

  const handleNameKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleCreate();
      } else if (e.key === "Escape") cancelCreate();
    },
    [handleCreate, cancelCreate],
  );

  return (
    <div className="flex flex-col min-h-0" role="tree" aria-label="Quick notes">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 pt-3 pb-1 shrink-0">
        <button
          onClick={toggleSection}
          className="flex items-center gap-1 text-muted-foreground/50 hover:text-muted-foreground transition-colors"
        >
          {sectionExpanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          <span className="text-[10px] font-medium uppercase tracking-widest select-none">
            Quick Notes
          </span>
        </button>
        <div className="flex-1 h-px bg-border/30" />
        {sectionExpanded && (
          <>
            <button
              onClick={toggleFilter}
              className={cn(
                "flex items-center justify-center h-5 w-5 rounded-sm transition-colors",
                isFilterVisible
                  ? "text-foreground bg-accent/60"
                  : "text-muted-foreground/40 hover:text-foreground hover:bg-accent/60",
              )}
              title="Filter notes"
            >
              <Filter className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={startCreate}
              className="flex items-center justify-center h-5 w-5 rounded-sm text-muted-foreground/40 hover:text-foreground hover:bg-accent/60 transition-colors"
              title="New quick note"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </>
        )}
      </div>

      {sectionExpanded && (
        <div
          className="overflow-auto min-h-0 pb-2"
          onDragOver={handleRootDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleRootDrop}
        >
          {/* Filter */}
          {isFilterVisible && (
            <div className="px-3 pb-1">
              <input
                ref={filterRef}
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") {
                    setIsFilterVisible(false);
                    setFilterText("");
                  }
                }}
                placeholder="Filter notes…"
                className="w-full text-xs bg-accent/40 rounded-sm px-2 py-1 outline-none placeholder:text-muted-foreground/40 border border-transparent focus:border-border/50"
              />
            </div>
          )}

          {/* Create form — just type a name, or folder/name to create in a folder */}
          {isCreating && (
            <div className="px-3 pb-1">
              <input
                ref={nameInputRef}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={handleNameKeyDown}
                onBlur={() => {
                  if (!newName.trim()) cancelCreate();
                }}
                placeholder="eg. content_ideas/my_idea"
                className="w-full text-xs bg-accent/40 rounded-sm px-2 py-1 outline-none placeholder:text-muted-foreground/40 border border-transparent focus:border-border/50"
              />
            </div>
          )}

          {/* Tree items */}
          {flattened.map(({ node, depth }) => {
            if (node.isDirectory) {
              const count = countNotes(node);
              const isExp = effectiveExpanded.has(node.path);
              const isDropHover =
                dropTarget === node.path && draggedItem !== null;
              return (
                <div
                  key={node.path}
                  role="treeitem"
                  aria-expanded={isExp}
                  className={cn(
                    "flex items-center gap-1 px-2 cursor-pointer text-sm",
                    "min-h-[28px] mx-1 rounded-sm",
                    "hover:bg-accent transition-colors",
                    isDropHover && "bg-teal-500/20 ring-1 ring-teal-500/40",
                  )}
                  style={{ paddingLeft: `${depth * 16 + 8}px` }}
                  onClick={() => toggleFolder(node.path)}
                  onDragOver={(e) => handleDragOver(e, node.path)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => {
                    e.stopPropagation();
                    handleDrop(e, node.path);
                  }}
                >
                  {isExp ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); openIconPicker(e, node.path) }}
                    className="flex items-center justify-center h-5 w-5 shrink-0 rounded-sm transition-colors hover:bg-accent/80"
                    title="Set icon"
                  >
                    {icons[node.path] ? (
                      <span className="text-sm leading-none">{icons[node.path]}</span>
                    ) : (
                      <Folder className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                  <span className="truncate flex-1">{node.name}</span>
                  <span className="text-[10px] text-muted-foreground/50 tabular-nums shrink-0">
                    {count}
                  </span>
                </div>
              );
            }

            const noteIcon = icons[node.path];
            const isDragging = draggedItem === node.path;

            return (
              <div
                key={node.path}
                role="treeitem"
                aria-selected={selectedFile === node.path}
                draggable
                onDragStart={(e) => handleDragStart(e, node.path)}
                onDragEnd={handleDragEnd}
                className={cn(
                  "group flex items-center gap-1 px-2 cursor-pointer text-sm",
                  "min-h-[28px] mx-1 rounded-sm",
                  "hover:bg-accent transition-colors",
                  selectedFile === node.path &&
                    "bg-accent text-accent-foreground",
                  isDragging && "opacity-40",
                )}
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
                onClick={() => onFileSelect(node.path)}
              >
                {/* Icon area - click to pick */}
                <button
                  onClick={(e) => openIconPicker(e, node.path)}
                  className={cn(
                    "flex items-center justify-center h-5 w-5 shrink-0 rounded-sm transition-colors",
                    "hover:bg-accent/80",
                  )}
                  title="Set icon"
                >
                  {noteIcon ? (
                    <span className="text-sm leading-none">{noteIcon}</span>
                  ) : (
                    <PenLine
                      className={cn(
                        "h-4 w-4",
                        selectedFile === node.path
                          ? "text-teal-400"
                          : "text-muted-foreground",
                      )}
                    />
                  )}
                </button>
                <span className="truncate flex-1">
                  {node.name.replace(/\.md$/, "")}
                </span>
                <button
                  onClick={(e) => handleDelete(node.path, e)}
                  className={cn(
                    "flex items-center justify-center h-5 w-5 rounded-sm shrink-0 transition-all",
                    deleteTarget === node.path
                      ? "opacity-100 text-rose-400 hover:bg-rose-500/15"
                      : "opacity-0 group-hover:opacity-60 text-muted-foreground hover:text-foreground hover:bg-accent",
                  )}
                  title={
                    deleteTarget === node.path
                      ? "Click again to delete"
                      : "Delete note"
                  }
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            );
          })}

          {/* Root drop zone indicator */}
          {draggedItem &&
            dropTarget === QUICK_NOTES_DIR &&
            flattened.length > 0 && (
              <div className="mx-2 my-1 h-0.5 rounded-full bg-teal-500/40" />
            )}

          {/* Empty state */}
          {tree.length === 0 && !isCreating && (
            <button
              onClick={startCreate}
              className={cn(
                "flex items-center gap-1 px-2 w-full text-left text-sm",
                "min-h-[28px] mx-1 rounded-sm",
                "text-muted-foreground/30 hover:text-muted-foreground/60 hover:bg-accent/30 transition-colors",
              )}
              style={{ paddingLeft: "8px" }}
            >
              <span className="h-4 w-4" />
              <PenLine className="h-4 w-4 shrink-0" />
              <span>New note…</span>
            </button>
          )}
        </div>
      )}

      {/* Icon picker portal */}
      {iconPickerTarget &&
        iconPickerPos &&
        createPortal(
          <div
            ref={iconPickerRef}
            className="fixed z-[9999] rounded-lg border bg-popover shadow-lg p-2"
            style={{ top: iconPickerPos.y, left: iconPickerPos.x }}
          >
            <div className="space-y-1">
              {EMOJI_GRID.map((row, i) => (
                <div key={i} className="flex gap-0.5">
                  {row.map((emoji) => (
                    <button
                      key={emoji}
                      onClick={() => selectIcon(emoji)}
                      className="h-7 w-7 flex items-center justify-center rounded hover:bg-accent transition-colors text-base"
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              ))}
            </div>
            {icons[iconPickerTarget] && (
              <button
                onClick={clearIcon}
                className="w-full mt-1 px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors"
              >
                Remove icon
              </button>
            )}
          </div>,
          document.body,
        )}
    </div>
  );
}
