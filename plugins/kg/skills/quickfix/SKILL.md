---
name: quickfix
description: Fix minor issues fast with a knowledge check. No planning, no brainstorming -- scan docs, fix, verify.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
---

# Quickfix

**Purpose:** Rapidly fix minor issues with minimal overhead. Scans knowledge docs first to avoid repeating past mistakes, then goes straight to the fix.

## When to Use

- Lint errors, type errors, small bugs
- Off-by-one, wrong variable, missing import
- Broken tests from a recent change
- Minor styling/layout issues
- Config tweaks
- Anything where the fix is likely < 3 files

## When NOT to Use

- Root cause is unclear and needs deep investigation (use /debug or /kg:plan instead)
- Fix spans many files or modules (use /kg:work instead)
- The issue reveals a design problem (use /kg:brainstorm instead)

---

## Process

<step number="1" required="true">
### Step 1: Understand the Issue

Read `$ARGUMENTS` for the issue description. If the user also provided a file path, error message, or stack trace, use that as the starting point.

If `$ARGUMENTS` is empty, check recent conversation context for the issue.

**Do NOT ask clarifying questions unless the issue is truly ambiguous.** Make reasonable assumptions and proceed.

**Scope check:** Before proceeding, assess whether this is actually a quickfix:

- **Escalate to `/kg:plan`** if: the fix likely touches 4+ files, requires database migrations, needs new interfaces/abstractions, or has unclear dependencies between components.
- **Escalate to `/kg:brainstorm`** if: the root cause is unclear, there are multiple valid approaches with real tradeoffs, or the issue reveals a design problem.

If either applies, tell the user:

```
This looks bigger than a quickfix -- it [reason].
Suggest: /kg:plan [topic] or /kg:brainstorm [topic]
```

Then STOP. Do not attempt the fix.
</step>

<step number="2" required="true" depends_on="1">
### Step 2: Knowledge Check

**Always run this step. Never skip it.**

Two lookups run in parallel:

**2a. Learnings researcher.** Dispatch the `learnings-researcher` agent with the issue description. This surfaces past solutions, critical patterns, and module context from the knowledge index.

```
Agent(
  subagent_type: "kg:learnings-researcher",
  description: "Research knowledge for quickfix",
  prompt: "[issue description from Step 1]"
)
```

**2b. Module docs.** Identify the module(s) the issue belongs to (from the error path, component name, or context). Read the matching module doc directly:

```
Read: docs/knowledge/modules/{module-name}.md
```

If the module name is unclear, scan the directory:

```
Glob: pattern="docs/knowledge/modules/*.md"
```

Then pick the most relevant file and read it. The module doc contains the file map, relationships, and connected components -- use this to understand what the fix might affect.

**Combine results:**

- If learnings or critical patterns match, apply them to the fix
- If module doc shows relationships (e.g., observer, event, policy tied to the model), check whether the fix needs to account for those
- If both return nothing relevant, proceed directly -- don't stall on empty results
</step>

<step number="3" required="true" depends_on="2">
### Step 3: Locate and Fix

Find the relevant code. Use the most direct path:

1. If a file/line is mentioned, go there directly
2. If an error message is given, grep for it
3. If a component/function name is given, glob for it
4. If learnings-researcher returned module docs, use those file maps instead of exploring the filesystem

Before writing, load the coding rules for the project's stack from `${CLAUDE_PLUGIN_ROOT}/rules/`
(`laravel.md`, `nextjs.md`, or both). The stack is recorded in `kg.local.md`, or in
`knowledge-garden.local.md` for projects set up before 0.4.0. Skip for a `generic` stack.

Apply the fix. Prefer `Edit` over `Write` for existing files. Keep changes minimal -- fix the issue, nothing more. The rules govern the lines you touch; do not reformat or restructure surrounding code to match them.
</step>

<step number="4" required="true" depends_on="3">
### Step 4: Verify

Run the most relevant verification:

- **Type error**: run the type checker (`bun tsc --noEmit`, `npx tsc --noEmit`, or `php artisan ide-helper:models` as appropriate)
- **Test failure**: re-run the failing test
- **Lint error**: re-run the linter
- **Runtime bug**: if a test exists, run it; otherwise note what the user should verify manually

If verification fails, iterate once. If it still fails, report what happened and let the user decide.
</step>

<step number="5" required="false" depends_on="4">
### Step 5: Report

Keep it brief:

```
Fixed: [one-line summary]
Changed: [file(s)]
Verified: [how]
Knowledge: [any learnings applied, or "none"]
```

If the fix revealed a deeper issue worth documenting, suggest: "Consider running /kg:compound to capture this."
</step>
