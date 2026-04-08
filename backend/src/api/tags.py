"""Tags and wiki-links API endpoints.

Provides endpoints for:
- Listing all tags with counts
- Finding notes by tag
- Finding backlinks to a note
"""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..middleware import limiter
from ..middleware.rate_limit import RATE_LIMIT_SEARCH
from ..middleware.validation import MAX_FILE_PATH_LENGTH
from ..parsing import extract_tags, extract_wiki_links, normalize_link_target
from ..storage import StorageBackend


router = APIRouter(prefix="/tags", tags=["tags"])


# =============================================================================
# Models
# =============================================================================


class TagCount(BaseModel):
    """A tag with its occurrence count."""

    tag: str
    count: int


class TagListResponse(BaseModel):
    """Response containing all tags with counts."""

    tags: list[TagCount]
    total: int


class NoteInfo(BaseModel):
    """Basic information about a note."""

    path: str
    title: str


class NotesByTagResponse(BaseModel):
    """Response containing notes that have a specific tag."""

    tag: str
    notes: list[NoteInfo]
    count: int


class WikiLink(BaseModel):
    """A wiki-link with source and target."""

    source_path: str
    source_title: str
    target: str


class BacklinksResponse(BaseModel):
    """Response containing backlinks to a note."""

    path: str
    backlinks: list[WikiLink]
    count: int


class OutgoingLinksResponse(BaseModel):
    """Response containing outgoing links from a note."""

    path: str
    links: list[str]
    count: int


# =============================================================================
# Helper Functions
# =============================================================================


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend from app state."""
    return request.app.state.storage


def extract_title(path: str, content: str) -> str:
    """Extract title from file path or content.

    Args:
        path: File path
        content: File content

    Returns:
        Title string
    """
    import re

    # Try to get title from first H1 heading
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    # Fallback to filename without extension
    filename = path.split("/")[-1]
    if filename.endswith(".md"):
        return filename[:-3]
    return filename


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=TagListResponse)
@limiter.limit(RATE_LIMIT_SEARCH)
async def list_tags(
    request: Request,
    storage: StorageBackend = Depends(get_storage),
) -> TagListResponse:
    """List all tags across the vault with occurrence counts.

    Scans all markdown files and extracts #tags, returning them
    sorted by count (descending) then alphabetically.

    Returns:
        List of tags with their counts
    """
    tag_counts: dict[str, int] = {}

    # Get all markdown files
    all_files = await storage.list("")
    md_files = [f for f in all_files if f.endswith(".md")]

    for file_path in md_files:
        try:
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")
            tags = extract_tags(content)

            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        except Exception:
            # Skip files that can't be read
            continue

    # Sort by count (descending), then alphabetically
    sorted_tags = sorted(
        tag_counts.items(),
        key=lambda x: (-x[1], x[0]),
    )

    tags = [TagCount(tag=tag, count=count) for tag, count in sorted_tags]

    return TagListResponse(
        tags=tags,
        total=len(tags),
    )


@router.get("/{tag}/notes", response_model=NotesByTagResponse)
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_notes_by_tag(
    tag: str,
    request: Request,
    storage: StorageBackend = Depends(get_storage),
) -> NotesByTagResponse:
    """Get all notes that contain a specific tag.

    Args:
        tag: The tag to search for (without # prefix)

    Returns:
        List of notes containing the tag
    """
    notes: list[NoteInfo] = []

    # Get all markdown files
    all_files = await storage.list("")
    md_files = [f for f in all_files if f.endswith(".md")]

    for file_path in md_files:
        try:
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")
            tags = extract_tags(content)

            if tag in tags:
                notes.append(
                    NoteInfo(
                        path=file_path,
                        title=extract_title(file_path, content),
                    )
                )
        except Exception:
            continue

    # Sort by title
    notes.sort(key=lambda n: n.title.lower())

    return NotesByTagResponse(
        tag=tag,
        notes=notes,
        count=len(notes),
    )


@router.get("/links/backlinks", response_model=BacklinksResponse)
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_backlinks(
    path: str = Query(
        ...,
        description="Path to the note to find backlinks for",
        max_length=MAX_FILE_PATH_LENGTH,
    ),
    request: Request = None,
    storage: StorageBackend = Depends(get_storage),
) -> BacklinksResponse:
    """Find all notes that link to a specific note via [[wiki-links]].

    Args:
        path: Path to the target note

    Returns:
        List of notes that link to the target
    """
    backlinks: list[WikiLink] = []

    # Normalize the target path for comparison
    target_filename = path.split("/")[-1]
    if target_filename.endswith(".md"):
        target_name = target_filename[:-3]
    else:
        target_name = target_filename

    # Get all markdown files
    all_files = await storage.list("")
    md_files = [f for f in all_files if f.endswith(".md")]

    for file_path in md_files:
        # Skip the target file itself
        if file_path == path:
            continue

        try:
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")
            wiki_links = extract_wiki_links(content)

            # Check if any link points to our target
            for link in wiki_links:
                normalized = normalize_link_target(link)
                # Check if the link matches the target
                # Support both full path match and filename-only match
                link_filename = normalized.split("/")[-1]
                if link_filename.endswith(".md"):
                    link_name = link_filename[:-3]
                else:
                    link_name = link_filename

                if normalized == path or link_name == target_name:
                    backlinks.append(
                        WikiLink(
                            source_path=file_path,
                            source_title=extract_title(file_path, content),
                            target=link,
                        )
                    )
                    break  # Only count each file once
        except Exception:
            continue

    # Sort by source title
    backlinks.sort(key=lambda b: b.source_title.lower())

    return BacklinksResponse(
        path=path,
        backlinks=backlinks,
        count=len(backlinks),
    )


@router.get("/links/outgoing", response_model=OutgoingLinksResponse)
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_outgoing_links(
    path: str = Query(
        ...,
        description="Path to the note to get outgoing links for",
        max_length=MAX_FILE_PATH_LENGTH,
    ),
    request: Request = None,
    storage: StorageBackend = Depends(get_storage),
) -> OutgoingLinksResponse:
    """Get all outgoing [[wiki-links]] from a specific note.

    Args:
        path: Path to the source note

    Returns:
        List of link targets from the note
    """
    try:
        content_bytes = await storage.read(path)
        content = content_bytes.decode("utf-8")
        wiki_links = extract_wiki_links(content)
    except FileNotFoundError:
        wiki_links = []
    except Exception:
        wiki_links = []

    return OutgoingLinksResponse(
        path=path,
        links=wiki_links,
        count=len(wiki_links),
    )
