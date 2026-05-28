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
- DeepSeek 或其他 OpenAI-compatible API endpoint
- `python-dotenv` for local environment variables
- `tqdm` for CLI progress
- `difflib` for unified diff output
- `owlsome_core.obsidian` for final Obsidian-compatible normalization

## Core Workflow

```text
Raw Markdown
→ paragraph-based chunking
→ optional sample-based book profile generation
→ LLM cleanup per chunk, serial or parallel
→ checkpoint save after every finished chunk
→ chunk merge and de-duplication
→ Obsidian-compatible normalization
→ formatted Markdown output
→ optional diff and report output
```

## Core Algorithm

### 1. Paragraph chunking

`chunk_markdown` splits text by blank-line-separated paragraphs. It avoids cutting in the middle of formulas or paragraphs when possible.

The final paragraph of a chunk can be reused as an overlap anchor for the next chunk.

### 2. Optional book profile

For long textbooks, `text_archiver` can sample representative chunks and ask the model to produce a book-specific cleanup profile.

The profile covers heading hierarchy, example/exercise formatting, formula preservation, image handling, Obsidian syntax rules, and manual review risks.

Generate a profile automatically:

```powershell
python D:\Projects\EL\text_archiver\main.py input.md --auto-profile --profile-samples 5 --parallel 4 --report
```

Reuse an existing profile:

```powershell
python D:\Projects\EL\text_archiver\main.py input.md --book-profile input_profile.md --parallel 4 --report
```

### 3. LLM cleanup

Each chunk is sent to an OpenAI-compatible chat completion endpoint with a strict system prompt:

- Fix Markdown syntax.
- Repair PDF-induced line breaks.
- Normalize Chinese/English spacing.
- Preserve every source sentence and symbol.
- Preserve Obsidian syntax such as frontmatter, wikilinks, callouts, highlights, tasks, formulas, and images.

The model is configured by:

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

Current default recommendation:

```text
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

Legacy `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, and `MODEL_NAME` are still supported for existing environments.

### 4. Parallel cleanup

`--parallel N` enables thread-based parallel processing.

- `--parallel 1` keeps the original serial behavior.
- `--parallel N`, where `N > 1`, creates independent workers.
- Each worker creates its own OpenAI-compatible client.
- The main thread saves checkpoint and report metadata when chunks finish.
- Final merge always sorts by chunk index, not completion order.

If the API rate limits requests, reduce `--parallel` or increase `--rate-limit-delay`.

### 5. Checkpointing

After each chunk, the result is saved to:

```text
<input>.checkpoint.json
```

This allows interrupted jobs to resume without reprocessing completed chunks.

The checkpoint remains compatible with the old shape and may include per-chunk metadata:

```json
{
  "processed": {"0": "..."},
  "meta": {
    "0": {
      "status": "done",
      "duration_seconds": 3.2,
      "attempts": 1,
      "fallback_to_original": false
    }
  }
}
```

### 6. Merge

`merge_chunks` uses a short anchor from the next chunk to remove duplicated overlap content.

### 7. Obsidian normalization

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
→ optional book profile
→ DeepSeek / OpenAI-compatible LLM, serial or parallel
→ processed chunk checkpoint
→ merged Markdown
→ Obsidian frontmatter + callout normalization
→ output.md
→ optional output.md.diff / output.md.report.json
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
- `--parallel`: parallel worker count, default 1.
- `--auto-profile`: sample chunks and generate a book-specific profile.
- `--profile-samples`: number of sampled chunks.
- `--book-profile`: reuse an existing profile.
- `--profile-output`: path for generated profile.
- `--report`: save processing report JSON.
- `--rate-limit-delay`: base retry delay.
- `--dry-run`: show chunks and sample plan without API calls.

## Report Output

When `--report` is set, the tool writes:

```text
<output>.report.json
```

The report includes input/output paths, model, parallelism, chunk count, profile mode, runtime, failed/fallback chunks, and per-chunk metadata.

## Module Boundaries

- `text_archiver/main.py`: CLI, chunking, LLM calls, checkpoint, diff.
- `owlsome_core/obsidian.py`: frontmatter, callout conversion, image path normalization.
- `learning_platform`: consumes cleaned Markdown but does not perform cleanup itself.

## Stability Notes

- The cleanup prompt must keep the “do not delete or summarize source text” rule.
- Obsidian post-processing is deterministic and conservative.
- Checkpoints should remain untracked.
- `.env` files must remain untracked.
