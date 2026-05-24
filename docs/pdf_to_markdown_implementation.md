# PDF to Markdown Technical Implementation

This document describes the PDF parsing module used by Owlsome Learning.

## Goal

Convert PDFs and document URLs into Markdown that can be consumed by:

- Owlsome public knowledge-base import.
- Personal learning spaces.
- Obsidian-compatible vault workflows.

The output is now normalized toward Obsidian-compatible Markdown.

## Technology Stack

- Python 3.9+
- FastAPI / Uvicorn for the MinerU WebUI.
- SQLite via `aiosqlite` for parse task history.
- MinerU API for PDF parsing.
- `requests` for HTTP calls.
- `pypdf` for large PDF splitting.
- `owlsome_core.obsidian` for Obsidian Markdown normalization.

## Core Workflow

```text
PDF / URL / Uploaded local file
→ MinerU task creation
→ optional large-PDF split
→ MinerU API parse
→ result ZIP download / Markdown extraction
→ chunk merge for large PDFs
→ Obsidian-compatible Markdown normalization
→ WebUI task DB + SSE result event
```

## Core Algorithm

### 1. Task creation

The WebUI accepts:

- Public PDF URL.
- Local uploaded PDF.
- Parse mode: precision / agent.
- Options: OCR, formula recognition, table recognition, language, page ranges.

The task is stored in SQLite with status `pending`.

### 2. Background execution

`mineru_tools/webui/task_manager.py` runs each parse job in a background executor and emits SSE events:

- `status`
- `progress`
- `chunk`
- `result`
- `error`

### 3. Large PDF handling

For precision local-file mode, large PDFs are handled by `MinerUClient.parse_large_pdf`:

```text
large.pdf
→ split into <= 200 page chunks
→ submit chunks to MinerU
→ poll chunk progress
→ download each result
→ merge Markdown into merged_full.md
```

### 4. Obsidian normalization

After MinerU returns Markdown, the WebUI calls:

```python
normalize_obsidian_markdown(
    markdown,
    title=Path(file_name).stem,
    source=source_path_or_url,
    tags=["owlsome", "mineru", "pdf"],
    doc_type="parsed_pdf",
)
```

This step:

- Adds YAML frontmatter when missing.
- Preserves formulas, images, task lists, and wikilinks.
- Converts MinerU `<details><summary>...</summary>...</details>` blocks to Obsidian callouts.
- Normalizes image path separators.

## Data Flow

```text
User upload
→ uploads/
→ tasks table
→ MinerUClient / AgentClient
→ output/
→ markdown_content field
→ learning_platform importer or personal-space upload
```

Runtime output directories are excluded from git. A curated sample Markdown file is committed under:

```text
learning_platform/sample_data/calculus_ii_chapter5_mineru.md
```

## LLM Usage

This module does not use an LLM directly inside Owlsome. It delegates document parsing to MinerU, which may use OCR / VLM capabilities depending on selected MinerU model options.

LLM-based cleanup is handled by `text_archiver`, not by the MinerU WebUI.

## Interfaces

Important WebUI routes:

- `POST /api/tasks`: create parse task.
- `GET /api/tasks/{db_id}`: get task status.
- `GET /api/tasks/{db_id}/sse`: stream task progress.
- `GET /api/tasks/{db_id}/markdown`: get Markdown result.
- `GET /output/{path}`: serve output files.

Important Python entrypoints:

- `mineru_tools/run.py`
- `mineru_tools/webui/app.py`
- `mineru_tools/webui/task_manager.py`
- `mineru_tools/mineru_client/client.py`

## Stability Notes

- Obsidian normalization is post-processing only; it does not change MinerU parsing behavior.
- If normalization fails in future changes, it should fall back to raw Markdown rather than fail the parse task.
- Secrets such as MinerU tokens must stay in local config or environment files and must not be committed.

