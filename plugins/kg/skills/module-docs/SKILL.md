---
name: module-docs
description: Generate per-module documentation by tracing references from module anchors. Use when indexing project modules for fast AI lookup.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Module Docs Generator

**Purpose:** Auto-index project modules into markdown files in `docs/knowledge/modules/` for fast AI navigation. Uses a reference-tracing approach that works regardless of project directory conventions.

## Overview

Instead of enumerating file types, this skill starts from **module anchors** (models for Laravel, route segments for Next.js) and traces all references to build a complete picture of each module.

**Key principle:** Grep the project for the anchor's class/name, then categorize what you find. This naturally discovers any file type -- including custom ones the project may use.

---

## Process

### Step 1: Detect Stack

Read `kg.local.md` (or the legacy `knowledge-garden.local.md`) or `docs/knowledge/schema.yaml` to determine the stack. If neither exists, run the setup skill first.

### Step 2: Discover Module Anchors

**Laravel:** Scan `app/Models/` for model files. Each model = one module.

**Next.js:** Detect router type (`app/` or `pages/`). Each top-level route segment = one module.

If `$ARGUMENTS` specifies a module name, process only that module. Otherwise process all discovered modules.

### Step 3: Generate Module Docs

For each module anchor, follow the stack-specific scanning strategy:

- **Laravel**: Follow the strategy in [laravel-scan.md](./references/laravel-scan.md)
- **Next.js**: Follow the strategy in [nextjs-scan.md](./references/nextjs-scan.md)

### Step 4: Write Module Files

Write each module doc to `docs/knowledge/modules/{module-name}.md` (lowercase, hyphenated).

**Every module doc must open by declaring its path root**, on the third line, before any content:

```markdown
# Purchasing Module

Stack: Laravel 12 (`backend/`). All paths below are relative to `backend/`.
```

This is what makes the file map usable. In a monorepo the anchors live under a workspace directory
(`backend/`, `frontend/`), so a path written as `app/Models/User.php` resolves from nowhere and the
reader has to search the filesystem anyway — defeating the entire purpose of the doc. Declare the
root once at the top and keep every path in the file relative to it.

For a single-application repository, say so explicitly:

```markdown
Stack: Next.js 16. All paths below are relative to the repository root.
```

**A module doc without this header is a defect**, not a stylistic difference. Regenerate it.

### Step 5: Summary

After processing all modules, present a summary:

```
Module docs generated:

| Module | Files Found | Path |
|--------|-------------|------|
| User | 14 | docs/knowledge/modules/user.md |
| Order | 22 | docs/knowledge/modules/order.md |
| ... | ... | ... |

Total: [N] modules indexed, [N] connected files discovered.
```

---

## Incremental Updates

If module docs already exist in `docs/knowledge/modules/`, re-running this skill will overwrite them with fresh scans. The skill does not attempt to merge -- a full rescan is fast enough and avoids stale data.

---

## Error Handling

**No models/routes found:**
- Report: "No module anchors found. Ensure your project has models in app/Models/ (Laravel) or route segments in app/ or pages/ (Next.js)."

**Schema not found:**
- Suggest running setup first: "Run /kg:setup to initialize Knowledge Garden before generating module docs."
