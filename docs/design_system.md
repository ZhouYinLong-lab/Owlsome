# Owlsome Learning Design System

This document records the current visual direction so agents and UI collaborators can extend the product consistently.

## 1. Brand Direction

Owlsome Learning uses Nanjing University purple as the main identity color. The interface should feel academic, trustworthy, and product-like rather than decorative.

Design goals:

- purple is the primary action and navigation color
- gold is a restrained secondary accent
- reading surfaces stay bright and low-noise
- math content remains the visual priority
- admin-only states are clear but not visually dominant in learner mode

## 2. Theme Tokens

The canonical tokens live in:

```text
D:\Projects\EL\learning_platform\frontend\src\styles.css
```

Current token set:

| Token | Purpose |
|---|---|
| `--color-nju-purple` | primary action, selected states, progress, major accents |
| `--color-nju-purple-hover` | primary hover and theorem accent |
| `--color-nju-purple-dark` | headings and selected navigation contrast |
| `--color-nju-purple-deep` | sidebar base |
| `--color-nju-purple-soft` | subtle panels, empty states, answer backgrounds |
| `--color-nju-purple-panel` | expanded tree hover and nested panel emphasis |
| `--color-nju-gold` | brand mark and secondary emphasis |
| `--color-nju-gold-soft` | notices and secondary ghost actions |
| `--color-nju-gold-text` | readable text on soft gold surfaces |
| `--color-text` | main body text |
| `--color-muted` | helper text, metadata, descriptions |
| `--color-bg` | app page background |
| `--color-surface` | cards and content panels |
| `--color-border` | default border |
| `--color-border-strong` | table/input/progress supporting borders |
| `--color-danger` | reject/error/destructive actions |
| `--color-info` | definition/source tags |
| `--color-success` | success/todo callouts |
| `--color-warning` | examples and exercise-adjacent accents |

## 3. Color Application Rules

### Navigation

- Sidebar background uses the deep purple gradient.
- Active sidebar item uses `--color-nju-purple`.
- Sidebar body text uses light-on-dark tokens.
- Role switch is visibly purple because it controls a product mode.

### Actions

- Primary buttons use purple with white text.
- Destructive buttons use `--color-danger`.
- Ghost/secondary buttons may use soft gold when they represent a lower-risk helper action.
- Disabled actions use soft purple or neutral muted states.

### Content

- Cards and reading panes stay white.
- Resource trees use soft purple backgrounds and purple selected indicators.
- Community contribution labels use gold to separate them from textbook-origin content.
- Definitions, theorems, examples, and exercises keep distinct left-border accents:
  - definition: info blue
  - theorem: purple
  - example: warning amber
  - exercise: danger red

### Markdown / Obsidian

- Callout note/tip/important uses purple.
- Warning/danger/error uses red.
- Example/question/FAQ uses gold.
- Success/todo uses green.
- Tables use neutral borders for readability.

## 4. Accessibility Requirements

- Primary purple buttons must use white text.
- Focus outlines must remain visible and should not be removed.
- Text should not rely on color alone; use labels such as `社区贡献`, `清洗版教材`, or status text.
- Math rendering must allow horizontal scrolling for large formulas.
- Do not use negative letter spacing.
- Keep cards at 8px radius or less unless the global design system changes.
- Maintain sufficient contrast for metadata. If a color is too faint on white, use `--color-muted` or darker.

## 5. Component Conventions

| Component | Visual rule |
|---|---|
| `AppShell` | persistent purple sidebar, role switch at bottom |
| `Dashboard` | fewer than four high-level metrics, task-oriented cards |
| `KnowledgeBase` | Obsidian-style resource tree on the left, detail on the right |
| `PersonalSpaces` | upload/tools above personal resource tree, detail on the right |
| `ReviewCenter` | admin-only list cards with explicit approve/reject/revision actions |
| `MarkdownRenderer` | preserve Obsidian syntax expectations and KaTeX display behavior |

## 6. Future UI Work

Before introducing new colors, first try existing tokens. Add a new token only when the color communicates a new semantic state that cannot be expressed by the current set.

Recommended next UI tasks:

1. Add resource tree search with purple selected-result highlighting.
2. Persist expanded tree nodes in localStorage.
3. Add a breadcrumb above public and personal detail panes.
4. Add consistent loading skeletons using soft purple panels.
5. Add dark-mode tokens only after the light theme is stable.
