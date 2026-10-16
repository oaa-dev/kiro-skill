---
name: knowledge-prune
description: Flag stale or outdated learnings for cleanup. Use periodically to keep the knowledge base relevant and maintainable.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Knowledge Prune

**Purpose:** Score documented solutions on staleness and present candidates for archiving, deletion, or retention. Keeps the knowledge base relevant by removing outdated learnings.

## Overview

This skill scans all files in `docs/knowledge/solutions/`, scores each on a staleness scale (0-100), and presents ranked candidates for cleanup. Archiving moves files to `docs/knowledge/archive/` (recoverable).

## Arguments

- `$ARGUMENTS` (optional): staleness score threshold, 0-100. Default: 50. Lower values flag more
  documents. Example: `/kg:knowledge-prune 30`.

---

## Process

### Step 1: Gather All Solution Files

```
Glob: pattern="docs/knowledge/solutions/**/*.md"
```

If no files found, report: "No solutions to prune. Knowledge base is empty."

### Step 2: Read Critical Patterns

```
Read: docs/knowledge/patterns/critical-patterns.md
```

Extract all filenames referenced in critical patterns (these get a staleness reduction).

### Step 3: Score Each Document

For each solution file, read the first 20 lines to extract YAML frontmatter, then compute a staleness score (0-100):

**Scoring factors:**

| Factor | Points | Calculation |
|--------|--------|-------------|
| Age | 0-30 | +1 per month since `date` field (max 30) |
| Severity | 0-20 | low=+20, medium=+10, high=+5, critical=0 |
| Framework version mismatch | 0-20 | If `framework_version` doesn't match current project version, +20 |
| Referenced by critical patterns | -20 | If filename appears in critical-patterns.md, -20 |
| Module still exists | -10 | If module has a doc in `docs/knowledge/modules/`, -10 |

**Minimum score:** 0 (floor)
**Maximum score:** 100

**To detect current framework version:**
- Laravel: read `composer.json` for `laravel/framework` version
- Next.js: read `package.json` for `next` version
- If version detection fails, skip this factor (0 points)

### Step 4: Filter and Rank

Default threshold: score > 50 (can be overridden via `$ARGUMENTS`).

Sort candidates by score descending.

### Step 5: Present Candidates

```markdown
## Stale Knowledge Candidates

**Threshold:** [score] (solutions scoring above this are flagged)
**Total solutions:** [N]
**Candidates found:** [M]

| # | Score | File | Module | Age | Severity | Reason |
|---|-------|------|--------|-----|----------|--------|
| 1 | 78 | solutions/runtime-errors/old-bug-20250101.md | Payments | 14mo | low | Old, low severity, module removed |
| 2 | 65 | solutions/config-errors/env-issue-20250601.md | System | 8mo | medium | Framework version mismatch |
| ... | ... | ... | ... | ... | ... | ... |

**Actions:**
- Enter numbers to select (e.g., "1, 3, 5")
- "all" to select all candidates
- "none" to skip pruning
```

### Step 6: User Decision

Wait for user to select candidates, then ask for each selected batch:

```
Selected [N] candidates. What action?

1. Archive (move to docs/knowledge/archive/ -- recoverable)
2. Delete permanently
3. Keep (remove from candidates list)
```

### Step 7: Execute Action

**Archive:**
```bash
mkdir -p docs/knowledge/archive/{category}
mv docs/knowledge/solutions/{category}/{filename} docs/knowledge/archive/{category}/{filename}
```

**Delete:**
```bash
rm docs/knowledge/solutions/{category}/{filename}
```

**Keep:**
- No action taken
- Optionally add a `# Reviewed: YYYY-MM-DD` comment to frontmatter to prevent re-flagging

### Step 8: Regenerate Index

After archiving or deleting files, regenerate `docs/knowledge/index.md` to reflect the current state:

1. Read all remaining solution files: `Glob: pattern="docs/knowledge/solutions/**/*.md"`
2. Read `docs/knowledge/patterns/critical-patterns.md`
3. Extract frontmatter from each solution (first 20 lines, parallel batches of 10)
4. Rewrite `docs/knowledge/index.md` with updated Solutions table and Critical Patterns digest

Skip this step if no files were archived or deleted (all kept).

### Step 9: Summary

```
Pruning complete:
- Archived: [N] files
- Deleted: [N] files
- Kept: [N] files
- Remaining solutions: [N] files
- Index: [regenerated / unchanged]
```

---

## Error Handling

**No solutions directory:**
- Suggest running setup: "Run /kg:setup to initialize Knowledge Garden first."

**No candidates above threshold:**
- Report: "No stale candidates found above threshold [score]. Your knowledge base is fresh."
- Suggest lowering threshold if desired.

**Archive directory missing:**
- Create it automatically with `mkdir -p`

**Malformed frontmatter:**
- Skip files with invalid/missing frontmatter
- Report count of skipped files
