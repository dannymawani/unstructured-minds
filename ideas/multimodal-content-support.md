# Multimodal Content Support

**Status:** Future idea
**Date:** 2026-03-13

## Problem

The app currently only handles markdown text. Users can't paste images (gym whiteboard photos, handwritten notes), attach PDFs (lab results, meal plans), or drop in other unstructured content — even though "unstructured" is in the name.

## What Already Works

- Chat panel supports pasting up to 5 images for Claude analysis via `/chat/note-assist`
- Claude vision API is available (Sonnet 4.5) — can already read images
- Local vault storage can technically write any file type
- Milkdown has image plugins (`image-block`, `image-inline`) but they're not enabled

## What's Needed

### Phase 1: Image paste in editor (Medium effort)
- Enable Milkdown image-block plugin
- Store images in vault under `attachments/` or similar
- Serve images back via a new backend endpoint (`/files/{path}`)
- Render inline in the editor via markdown `![](url)` syntax

### Phase 2: Extract data from images (Low-Medium effort)
- Add multimodal path to extraction pipeline (currently hardcoded to `content.decode("utf-8")`)
- Send images to Claude vision alongside text for extraction
- Use case: photo of gym whiteboard → structured workout data

### Phase 3: PDF support (Medium effort)
- Add PDF upload endpoint
- Extract text via library (e.g., `pdfplumber`, `PyPDF2`)
- Optionally send pages as images to Claude for richer extraction
- Use case: blood test PDF → structured health metrics

### Phase 4: Persistent binary storage for cloud mode (High effort)
- New `attachments` table in Postgres (metadata + reference)
- Object storage (S3/Azure Blob/Cloudflare R2) for actual bytes
- Link attachments to notes via foreign keys
- File serving endpoint with auth

## Architecture Considerations

- Local mode: store files in vault filesystem, straightforward
- Cloud mode: need object storage — Postgres isn't ideal for blobs
- Extraction pipeline needs a multimodal branch, not a replacement of the text path
- Image size limits and compression for editor paste
- Consider OCR fallback for non-Claude extraction (cost control)

## Quick Wins (could do anytime)
1. Document existing image-in-chat capability for users
2. Enable Milkdown image plugin with local file storage
3. Add a single `extract_from_image()` method to the Claude client
