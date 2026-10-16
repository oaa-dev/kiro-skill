---
name: compound
description: Document a recently solved problem to compound your knowledge
argument-hint: "[optional: brief description of what was solved]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - Edit
---

# Compound Knowledge

Capture a recently solved problem as institutional knowledge using the knowledge-docs skill.

<instructions>

## Execution

This command is a streamlined entry point for the knowledge-docs skill. Use it after solving a non-trivial problem to document the solution.

1. **Verify knowledge base exists.** Check that `docs/knowledge/solutions/` exists. If not: "Run /kg:setup to initialize Knowledge Garden first." STOP.

2. **Detect context.** Determine what was solved:
   - If `$ARGUMENTS` is provided, use it as the problem description
   - If no arguments, scan the recent conversation for indicators of a solved problem:
     - Phrases like "that worked", "it's fixed", "working now", "problem solved"
     - Recent code changes that resolved an issue
   - If no solved problem is detected, ask: "What problem did you just solve?"

3. **Execute the knowledge-docs skill workflow.** Follow the full 7-step process defined in the knowledge-docs skill:

   **Step 1: Detect Confirmation** -- already done above.

   **Step 2: Gather Context** -- extract from conversation:
   - Module name
   - Symptom (exact error messages)
   - Investigation attempts (what didn't work)
   - Root cause (technical explanation)
   - Solution (what fixed it)
   - Prevention (how to avoid in future)

   If critical context is missing, ask the user and wait for response.

   **Step 3: Check Existing Docs** -- search for similar issues:
   ```
   Grep: pattern="[error phrase or keyword]" path=docs/knowledge/solutions/ -i=true output_mode=files_with_matches
   ```
   If similar found, present options (new doc, update existing, or skip).

   **Step 4: Generate Filename** -- format: `[sanitized-symptom]-[module]-[YYYYMMDD].md`

   **Step 5: Validate YAML Schema** -- read `docs/knowledge/schema.yaml` and validate all frontmatter fields against the enum values.

   **Step 6: Create Documentation** -- use the category from `category_map`, create the file in `docs/knowledge/solutions/[category]/`, populate using the resolution template.

   **Step 7: Cross-Reference** -- link related issues if found. Detect critical pattern candidates.

4. **Present decision menu:**

   ```
   Solution documented.

   File created:
   - docs/knowledge/solutions/[category]/[filename].md

   What's next?
   1. Continue workflow (recommended)
   2. Add to Required Reading - Promote to critical patterns
   3. Link related issues - Connect to similar problems
   4. View documentation - See what was captured
   ```

## Arguments

- `$ARGUMENTS` (optional): brief description of what was solved. If omitted, infers from conversation context.

</instructions>
