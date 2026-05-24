# Owlsome Learning Implementation Overview

Owlsome Learning currently contains three cooperating modules:

```text
mineru_tools
→ PDF / document parsing

text_archiver
→ Markdown cleanup and layout repair

learning_platform
→ Knowledge-base import, personal learning space, note review, progress, Q&A
```

The shared Markdown contract is Obsidian-compatible Markdown. The helper package is:

```text
owlsome_core/obsidian.py
```

## End-to-End Pipeline

```text
PDF
→ mineru_tools
→ Obsidian-compatible Markdown
→ text_archiver optional cleanup
→ learning_platform import
→ structured knowledge points
→ public knowledge base / personal learning space
```

## Current LLM Boundaries

- PDF parsing: delegated to MinerU APIs.
- Markdown cleanup: LLM via OpenRouter-compatible chat completions.
- Learning Q&A: optional LLM; deterministic offline fallback is always available.
- Structure extraction in the demo: rule-based first, LLM-ready later.

## Obsidian Reuse Strategy

Documents should remain usable outside Owlsome:

- Users can export files to an Obsidian vault.
- Knowledge points can use `[[wikilinks]]`.
- Important notes can use `> [!tip]` or `> [!warning]`.
- Metadata is stored in YAML frontmatter.

