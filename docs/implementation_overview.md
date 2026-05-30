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

## Completed Productized Capabilities

- Public knowledge base demo import: imports the stable Calculus II Chapter 5 `5.1-5.2` sample from cleaned MinerU Markdown when available.
- Full Calculus II import: administrators can use `POST /api/import/calculus-full` or the System Overview UI to dry-run or import the cleaned full textbook into the public resource library.
- Content QA and demo convergence: the full textbook import has a reproducible audit script that flags long, marker-poor, short, or formula-suspicious knowledge points and writes a Markdown report.
- Public resource hierarchy: the frontend resource tree now supports the full Chapter 5-10 structure, search filtering, breadcrumb context, and chapter/point ordering.
- Private learning spaces: Markdown/TXT uploads and sample spaces are split into personal knowledge points with progress state and personal Q&A.
- Contribution review loop: private knowledge points can be submitted as pending contributions, reviewed by an administrator, and merged into public `content_units` with a community label.
- Optional retrieval adapter: BGE-style embedding/reranker HTTP integration is available behind `RETRIEVAL_PROVIDER`, with keyword matching as the hard fallback.
- NJU purple theme: the frontend uses a tokenized Nanjing University purple design system documented in `docs/design_system.md`.

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

## Full Calculus II Import

The full-textbook path has been productized beyond the original CLI probe:

```text
POST /api/import/calculus-full
```

Typical administrator import body:

```json
{"dry_run": false, "reset_course": true, "write_report": true}
```

The API and CLI share `learning_platform/backend/app/pipelines/calculus_full_importer.py`, so chapter splitting, statistics, report generation, duplicate-course behavior, and fallback source selection stay consistent. After conservative second-pass splitting, the latest dry-run identifies 6 chapters, 76 knowledge points, and 638 content units from `merged_full_formatted.md`.

For content QA, run:

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\content_quality_audit.py --report D:\Projects\EL\docs\test_records\calculus_content_quality_audit.md
```

This report is intentionally structural: it helps the team find long sections, weak marker recognition, and formula-boundary risks before a demo, but it is not a complete mathematical proofread.

## Demo Readiness

The competition demo is documented in:

```text
D:\Projects\EL\docs\demo\demo_paths.md
D:\Projects\EL\docs\demo\competition_demo_script_5min.md
```

The three fixed paths are full textbook/public browsing, private learning space/Q&A, and private contribution/admin review/public merge.

## Current LLM Boundaries

- PDF parsing: delegated to MinerU APIs.
- Markdown cleanup: LLM via DeepSeek or another OpenAI-compatible chat completion provider.
- Learning Q&A: optional LLM; deterministic offline fallback is always available.
- Structure extraction in the demo: rule-based first, LLM-ready later.

## Obsidian Reuse Strategy

Documents should remain usable outside Owlsome:

- Users can export files to an Obsidian vault.
- Knowledge points can use `[[wikilinks]]`.
- Important notes can use `> [!tip]` or `> [!warning]`.
- Metadata is stored in YAML frontmatter.
