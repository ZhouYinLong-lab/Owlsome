# Version Control Strategy

This repository uses small stage-based commits so the team can review and recover each project increment independently.

## Branches

- `main`: stable demo branch. It should always run locally.
- Feature branches may be used later for risky work, for example `feature/pdf-live-ingestion`.

## Commit Stages

Each stage should be committed with a clear message:

1. `Add Obsidian compatibility core`
2. `Integrate Obsidian output into document pipeline`
3. `Document PDF and Markdown processing implementation`
4. `Verify Owlsome demo stability`

## Commit Message Format

Use imperative messages:

```text
Add Obsidian-compatible Markdown normalizer
Integrate Obsidian mode into text archiver
Document PDF to Markdown workflow
```

For larger commits, include a body:

```text
Add Obsidian-compatible Markdown normalizer

- Add YAML frontmatter generation
- Convert MinerU details blocks into Obsidian callouts
- Preserve math, wikilinks, task lists, and images
```

## Push Policy

After every stage:

```powershell
git status --short
git add <changed files>
git commit -m "<message>"
git push
```

If GitHub is unreachable, keep the local commit and retry:

```powershell
git push -u origin main
```

