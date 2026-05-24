# Obsidian Compatibility Design

Owlsome Learning uses an Obsidian-compatible Markdown subset as the common document format between PDF parsing, Markdown cleanup, public knowledge-base import, and personal learning spaces.

## Supported Syntax

- YAML frontmatter with `type`, `title`, `source`, `tags`, `aliases`, `created_at`.
- Standard Markdown headings, lists, tables, code blocks, images, and links.
- LaTeX inline/block math: `$...$` and `$$...$$`.
- Obsidian wikilinks: `[[Knowledge Point]]` and `[[Target|Label]]`.
- Obsidian callouts: `> [!note]`, `> [!tip]`, `> [!warning]`.
- Highlights: `==important text==`.
- Task lists: `- [ ]` and `- [x]`.

## Shared Normalizer

The shared utility is `owlsome_core.obsidian.normalize_obsidian_markdown`.

It is intentionally conservative:

- Adds frontmatter only if the document does not already have it.
- Converts MinerU HTML `<details><summary>...</summary>...</details>` blocks into Obsidian callouts.
- Normalizes image path separators while preserving standard Markdown image syntax.
- Does not rewrite formulas or remove source text.

This shared utility is used by:

- `mineru_tools`: normalize Markdown emitted by PDF parsing tasks.
- `text_archiver`: optionally ask the LLM to preserve Obsidian syntax and normalize the final output.
- `learning_platform`: import and render the same Obsidian-compatible Markdown.

