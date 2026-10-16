---
name: knowledge-docs
description: Capture solved problems as categorized documentation with YAML frontmatter. Use after solving non-trivial problems to build searchable institutional knowledge.
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
preconditions:
  - Problem has been solved (not in-progress)
  - Solution has been verified working
---

# Knowledge Docs Skill

**Purpose:** Document solved problems to build searchable institutional knowledge with category-based organization and enum-validated YAML frontmatter.

## Overview

This skill captures problem solutions immediately after confirmation, creating structured documentation in `docs/knowledge/solutions/`. Files use YAML frontmatter validated against `docs/knowledge/schema.yaml` for consistent categorization and fast lookup.

**Organization:** Each problem is documented as one markdown file in its category directory (e.g., `docs/knowledge/solutions/performance-issues/n-plus-one-user-queries-20260225.md`).

---

<critical_sequence name="documentation-capture" enforce_order="strict">

## 7-Step Process

<step number="1" required="true">
### Step 1: Detect Confirmation

**Auto-invoke after phrases:**
- "that worked"
- "it's fixed"
- "working now"
- "problem solved"
- "that did it"

**OR manual:** `/kg:compound` command

**Non-trivial problems only:**
- Multiple investigation attempts needed
- Tricky debugging that took time
- Non-obvious solution
- Future sessions would benefit

**Skip documentation for:**
- Simple typos
- Obvious syntax errors
- Trivial fixes immediately corrected
</step>

<step number="2" required="true" depends_on="1">
### Step 2: Gather Context

Extract from conversation history:

**Required information:**
- **Module name**: which module or component had the problem
- **Symptom**: observable error/behavior (exact error messages)
- **Investigation attempts**: what didn't work and why
- **Root cause**: technical explanation of actual problem
- **Solution**: what fixed it (code/config changes)
- **Prevention**: how to avoid in future

**Environment details:**
- Framework version (e.g., Laravel 11.x, Next.js 15.x)
- File/line references
- OS version (if relevant)

**BLOCKING REQUIREMENT:** If critical context is missing (module name, exact error, or resolution steps), ask user and WAIT for response before proceeding to Step 3:

```
I need a few details to document this properly:

1. Which module had this issue? [ModuleName]
2. What was the exact error message or symptom?
3. What framework version are you using?

[Continue after user provides details]
```
</step>

<step number="3" required="false" depends_on="2">
### Step 3: Check Existing Docs

Search `docs/knowledge/solutions/` for similar issues:

```
Grep: pattern="[error phrase keyword]" path=docs/knowledge/solutions/ -i=true output_mode=files_with_matches
```

**IF similar issue found:**

Present decision options:

```
Found similar issue: docs/knowledge/solutions/[path]

What's next?
1. Create new doc with cross-reference (recommended)
2. Update existing doc (only if same root cause)
3. Other
```

Wait for user response, then execute chosen action.

**ELSE** (no similar issue found):

Proceed directly to Step 4 (no user interaction needed).
</step>

<step number="4" required="true" depends_on="2">
### Step 4: Generate Filename

Format: `[sanitized-symptom]-[module]-[YYYYMMDD].md`

**Sanitization rules:**
- Lowercase
- Replace spaces with hyphens
- Remove special characters except hyphens
- Truncate to reasonable length (< 80 chars)

**Examples:**
- `missing-eager-load-user-20260225.md`
- `hydration-mismatch-dashboard-20260225.md`
- `queue-timeout-order-processing-20260225.md`
</step>

<step number="5" required="true" depends_on="4" blocking="true">
### Step 5: Validate YAML Schema

**CRITICAL:** All docs require validated YAML frontmatter with enum validation.

<validation_gate name="yaml-schema" blocking="true">

**Load the schema:**
```
Read: docs/knowledge/schema.yaml
```

Classify the problem against the enum values defined in the schema. Ensure all required fields are present and match allowed values exactly.

**Required frontmatter fields:**
- `module`: string (module name or "System" for system-wide)
- `date`: YYYY-MM-DD
- `problem_type`: must match schema enum
- `component`: must match schema enum
- `symptoms`: array with 1-5 items
- `root_cause`: must match schema enum
- `framework_version`: string (e.g., "Laravel 11.x", "Next.js 15.1")
- `resolution_type`: must match schema enum
- `severity`: must be one of [critical, high, medium, low]
- `tags`: array of keywords

**BLOCK if validation fails:**

```
YAML validation failed

Errors:
- problem_type: must be one of schema enums, got "[invalid value]"
- component: must be one of schema enums, got "[invalid value]"

Please provide corrected values.
```

**GATE ENFORCEMENT:** Do NOT proceed to Step 6 until YAML frontmatter passes all validation rules.

</validation_gate>
</step>

<step number="6" required="true" depends_on="5">
### Step 6: Create Documentation

**Determine category from problem_type:** Use the `category_map` in `docs/knowledge/schema.yaml` to map `problem_type` to the directory name.

**Create documentation file:**

```bash
mkdir -p "docs/knowledge/solutions/${CATEGORY}"
```

Populate using the template from [resolution-template.md](./assets/resolution-template.md) with context gathered in Step 2 and validated YAML frontmatter from Step 5.

**Module linking:** If a module doc exists in `docs/knowledge/modules/` for the affected module, add a note at the bottom:

```markdown
## Module Reference
See [module docs](../../modules/{module-name}.md) for full module documentation.
```

**Index regeneration:** After writing the solution file, regenerate the knowledge index so it stays current:

1. Read all solution files: `Glob: pattern="docs/knowledge/solutions/**/*.md"`
2. Read `docs/knowledge/patterns/critical-patterns.md`
3. Extract frontmatter from each solution (first 20 lines, parallel batches of 10)
4. Rewrite `docs/knowledge/index.md` with updated Solutions table and Critical Patterns digest

This ensures the next workflow command that reads the index will see this new solution.
</step>

<step number="7" required="false" depends_on="6">
### Step 7: Cross-Reference and Critical Pattern Detection

If similar issues found in Step 3:

**Update existing doc** with a "Related Issues" link:
```markdown
- See also: [{filename}](../{category}/{filename})
```

**Update new doc** with cross-reference (already included from Step 6).

**Update patterns if applicable:**

If this represents a common pattern (3+ similar issues):
```bash
# Add to docs/knowledge/patterns/common-solutions.md
```

**Critical Pattern Detection:**

If this issue has automatic indicators suggesting it might be critical:
- Severity: `critical` in YAML
- Affects multiple modules
- Non-obvious solution

Then in the decision menu, add a note:
```
This might be worth adding to Required Reading (Option 2)
```

But **NEVER auto-promote**. User decides via decision menu.
</step>

</critical_sequence>

---

<decision_gate name="post-documentation" wait_for_user="true">

## Decision Menu After Capture

After successful documentation, present options and WAIT for user response:

```
Solution documented

File created:
- docs/knowledge/solutions/[category]/[filename].md

What's next?
1. Continue workflow (recommended)
2. Add to Required Reading - Promote to critical patterns
3. Link related issues - Connect to similar problems
4. View documentation - See what was captured
5. Other
```

**Handle responses:**

**Option 1: Continue workflow**
- Return to calling skill/workflow
- Documentation is complete

**Option 2: Add to Required Reading**

Action:
1. Extract pattern from the documentation
2. Format as WRONG vs CORRECT with code examples using [critical-pattern-template.md](./assets/critical-pattern-template.md)
3. Add to `docs/knowledge/patterns/critical-patterns.md`
4. Add cross-reference back to this doc
5. Confirm: "Added to Required Reading. The learnings-researcher agent will surface this pattern."

**Option 3: Link related issues**
- Prompt: "Which doc to link? (provide filename or describe)"
- Search `docs/knowledge/solutions/` for the doc
- Add cross-reference to both docs
- Confirm: "Cross-reference added"

**Option 4: View documentation**
- Display the created documentation
- Present decision menu again

**Option 5: Other**
- Ask what they'd like to do

</decision_gate>

---

## Success Criteria

Documentation is successful when ALL of the following are true:

- YAML frontmatter validated (all required fields, correct formats)
- File created in `docs/knowledge/solutions/[category]/[filename].md`
- Enum values match `docs/knowledge/schema.yaml` exactly
- Code examples included in solution section
- Cross-references added if related issues found
- User presented with decision menu and action confirmed

---

## Error Handling

**Missing context:**
- Ask user for missing details
- Don't proceed until critical info provided

**YAML validation failure:**
- Show specific errors
- Present retry with corrected values
- BLOCK until valid

**Schema not found:**
- Suggest running setup: "Run /kg:setup to initialize Knowledge Garden first."

**Similar issue ambiguity:**
- Present multiple matches
- Let user choose: new doc, update existing, or link as duplicate

---

## Quality Guidelines

**Good documentation has:**
- Exact error messages (copy-paste from output)
- Specific file:line references
- Observable symptoms (what you saw, not interpretations)
- Failed attempts documented (helps avoid wrong paths)
- Technical explanation (not just "what" but "why")
- Code examples (before/after if applicable)
- Prevention guidance (how to catch early)
- Cross-references (related issues)

**Avoid:**
- Vague descriptions ("something was wrong")
- Missing technical details ("fixed the code")
- No context (which version? which file?)
- Just code dumps (explain why it works)
- No prevention guidance
