# Owlsome Learning Implementation Overview

For a fuller handoff, read `docs/agent_handoff_guide.md`. For frontend theme and accessibility conventions, read `docs/design_system.md`.

Owlsome Learning currently contains three cooperating modules:

```text
mineru_tools
→ PDF / document parsing

text_archiver
→ Markdown cleanup and layout repair

learning_platform
→ Knowledge-base import, personal learning space, contribution review, progress, Q&A
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
→ optional contribution review
→ community content merged into public knowledge points
```

## Stage 3 Contribution APIs

Personal uploads stay private by default. A learner must explicitly create a contribution before content can enter the public knowledge base.

```text
POST /api/contributions/from-personal-point
GET  /api/contributions/pending
GET  /api/contributions/{id}
POST /api/contributions/{id}/approve
POST /api/contributions/{id}/reject
POST /api/contributions/{id}/request-revision
```

The first version supports `content_scope = whole_point`. Approved contributions are merged into public `content_units` with `source = community_contribution:{id}` so the frontend can label community content. Rejected and revision-requested contributions keep review records but do not modify the public knowledge base.

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
