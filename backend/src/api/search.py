"""Search API endpoints for full-text search across vault notes."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..cache import search_cache
from ..middleware import limiter
from ..middleware.rate_limit import RATE_LIMIT_SEARCH
from ..middleware.validation import validate_query_length, MAX_SEARCH_QUERY_LENGTH
from ..storage import StorageBackend


router = APIRouter()


class SearchRequest(BaseModel):
    """Request for full-text search."""

    query: str = Field(..., max_length=MAX_SEARCH_QUERY_LENGTH)
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    """A single search result."""

    path: str
    title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    """Response containing search results."""

    results: list[SearchResult]


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
    # Try to get title from first H1 heading
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    # Fallback to filename without extension
    filename = path.split("/")[-1]
    if filename.endswith(".md"):
        return filename[:-3]
    return filename


def create_snippet(content: str, query_terms: list[str], max_length: int = 150) -> str:
    """Create a snippet highlighting matching terms.

    Args:
        content: Full file content
        query_terms: List of search terms to highlight
        max_length: Maximum snippet length

    Returns:
        Snippet with highlighted matches
    """
    # Find the first occurrence of any search term
    content_lower = content.lower()
    best_pos = len(content)  # Default to end if no match found

    for term in query_terms:
        pos = content_lower.find(term.lower())
        if pos != -1 and pos < best_pos:
            best_pos = pos

    # Calculate snippet boundaries
    start = max(0, best_pos - 50)
    end = min(len(content), start + max_length)

    # Adjust start to word boundary
    if start > 0:
        space_pos = content.rfind(" ", 0, start + 20)
        if space_pos > start - 30:
            start = space_pos + 1

    # Adjust end to word boundary
    if end < len(content):
        space_pos = content.find(" ", end - 20, end + 20)
        if space_pos != -1:
            end = space_pos

    snippet = content[start:end].strip()

    # Add ellipsis if needed
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    # Bold matching terms
    for term in query_terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        snippet = pattern.sub(f"**{term}**", snippet)

    # Clean up whitespace
    snippet = re.sub(r"\s+", " ", snippet)

    return snippet


def calculate_score(content: str, query_terms: list[str]) -> float:
    """Calculate relevance score based on term frequency.

    Args:
        content: File content
        query_terms: List of search terms

    Returns:
        Relevance score between 0 and 1
    """
    content_lower = content.lower()
    total_matches = 0
    terms_found = 0

    for term in query_terms:
        term_lower = term.lower()
        count = content_lower.count(term_lower)
        if count > 0:
            terms_found += 1
            total_matches += count

    if not query_terms:
        return 0.0

    # Score based on:
    # - Percentage of terms found (weighted 0.6)
    # - Total match count (weighted 0.4, capped at 10 matches)
    term_coverage = terms_found / len(query_terms)
    match_density = min(total_matches, 10) / 10

    return round(0.6 * term_coverage + 0.4 * match_density, 2)


@router.post("/search", response_model=SearchResponse)
@limiter.limit(RATE_LIMIT_SEARCH)
async def search(
    request: Request,
    body: SearchRequest,
    storage: StorageBackend = Depends(get_storage),
) -> SearchResponse:
    """Search across all vault notes.

    Performs a simple full-text search across markdown files,
    returning results with snippets and relevance scores.

    Args:
        request: HTTP request (required by slowapi rate limiter)
        body: Search query and options
        storage: Storage backend for file access

    Returns:
        Search results with paths, titles, snippets, and scores
    """
    query = body.query.strip()
    if not query:
        return SearchResponse(results=[])

    cache_key = f"{query}:{body.limit}"
    cached = search_cache.get(cache_key)
    if cached is not None:
        return cached

    # Split query into terms
    query_terms = query.split()

    # Get all markdown files
    all_files = await storage.list("")
    md_files = [f for f in all_files if f.endswith(".md")]

    results: list[SearchResult] = []

    for file_path in md_files:
        try:
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")

            # Check if any term matches
            content_lower = content.lower()
            if not any(term.lower() in content_lower for term in query_terms):
                continue

            score = calculate_score(content, query_terms)
            if score > 0:
                results.append(
                    SearchResult(
                        path=file_path,
                        title=extract_title(file_path, content),
                        snippet=create_snippet(content, query_terms),
                        score=score,
                    )
                )
        except Exception:
            # Skip files that can't be read
            continue

    # Sort by score descending
    results.sort(key=lambda r: r.score, reverse=True)

    # Apply limit
    results = results[: body.limit]

    response = SearchResponse(results=results)
    search_cache.set(cache_key, response)
    return response
