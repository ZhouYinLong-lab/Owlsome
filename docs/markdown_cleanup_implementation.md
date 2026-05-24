# Markdown Cleanup and Typesetting Technical Implementation

This document describes the Markdown cleanup module used by Owlsome Learning.

## Goal

Clean Markdown generated from PDF parsing while preserving source content and making the result friendly to:

- Obsidian vault workflows.
- Owlsome public knowledge-base import.
- Owlsome personal learning spaces.

## Technology Stack

- Python 3.9+
- OpenAI-compatible SDK (`openai`)
- OpenRouter-compatible API endpoint
- `python-dotenv` for local environment variables
- `tqdm` for CLI progress
- `difflib` for unified diff output
- `owlsome_core.obsidian` for final Obsidian-compatible normalization

## Core Workflow

```text
Raw Markdown
→ paragraph-based chunking
→ LLM cleanup per chunk
→ checkpoint save after every chunk
→ chunk merge and de-duplication
→ Obsidian-compatible normalization
→ formatted Markdown output
→ optional diff output
```

## Core Algorithm

### 1. Paragraph chunking

`chunk_markdown` splits text by blank-line-separated paragraphs. It avoids cutting in the middle of formulas or paragraphs when possible.

The final paragraph of a chunk can be reused as an overlap anchor for the next chunk.

### 2. LLM cleanup

Each chunk is sent to an OpenAI-compatible chat completion endpoint with a strict system prompt:

- Fix Markdown syntax.
- Repair PDF-induced line breaks.
- Normalize Chinese/English spacing.
- Preserve every source sentence and symbol.
- Preserve Obsidian syntax such as frontmatter, wikilinks, callouts, highlights, tasks, formulas, and images.

The model is configured by:

```text
OPENROUTER_API_KEY
OPENROUTER_BASE_URL
MODEL_NAME
```

### 3. Checkpointing

After each chunk, the result is saved to:

```text
<input>.checkpoint.json
```

This allows interrupted jobs to resume without reprocessing completed chunks.

### 4. Merge

`merge_chunks` uses a short anchor from the next chunk to remove duplicated overlap content.

### 5. Obsidian normalization

By default, `text_archiver` now applies:

```python
normalize_obsidian_markdown(
    final_output,
    title=args.obsidian_title or title_from_path(input_file),
    source=input_file,
    tags=["owlsome", "archived-markdown"],
    doc_type="cleaned_markdown",
)
```

This can be disabled for one-off compatibility checks:

```powershell
python main.py input.md --no-obsidian
```

## Data Processing Flow

```text
input.md
→ chunks[]
→ OpenRouter / LLM
→ processed chunk checkpoint
→ merged Markdown
→ Obsidian frontmatter + callout normalization
→ output.md
→ optional output.md.diff
```

## LLM Usage

Yes. The cleanup module uses an LLM for semantic-preserving formatting repair.

The LLM is not used to summarize or rewrite content. It is instructed to:

- Preserve the source.
- Repair layout and Markdown syntax.
- Preserve Obsidian-compatible constructs.

If an API call fails after retries, the original chunk is used as fallback to avoid data loss.

## CLI Interface

```powershell
python text_archiver/main.py input.md -o output.md --diff
```

Important options:

- `--chunk-size`: approximate chunk size.
- `--no-resume`: ignore checkpoint.
- `--diff`: save unified diff.
- `--show-diff`: print diff in terminal.
- `--obsidian`: enable Obsidian normalization, default.
- `--no-obsidian`: disable Obsidian post-processing.
- `--obsidian-title`: override frontmatter title.

## Module Boundaries

- `text_archiver/main.py`: CLI, chunking, LLM calls, checkpoint, diff.
- `owlsome_core/obsidian.py`: frontmatter, callout conversion, image path normalization.
- `learning_platform`: consumes cleaned Markdown but does not perform cleanup itself.

## Stability Notes

- The cleanup prompt must keep the “do not delete or summarize source text” rule.
- Obsidian post-processing is deterministic and conservative.
- Checkpoints should remain untracked.
- `.env` files must remain untracked.

