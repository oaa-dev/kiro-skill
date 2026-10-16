---
name: review
description: Review code against documented patterns and known issues
argument-hint: "[file path, branch name, or PR number]"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
---

# Knowledge-Backed Code Review

Review code changes against institutional knowledge, documented patterns, and known issues.

<instructions>

## Phase 1: Knowledge Auto-Read

Before reviewing, load relevant institutional knowledge -- but only if there's knowledge to surface.

1. **Determine review scope.** Based on `$ARGUMENTS`:
   - If a file path: review that file's recent changes
   - If a branch name: review all changes on that branch vs the default branch
   - If a PR number: use `gh pr diff $ARGUMENTS` to get the diff
   - If empty: review staged/unstaged changes (`git diff` and `git diff --cached`)

2. **Identify affected modules.** From the diff, extract:
   - Module names (from file paths and namespaces)
   - Component types (models, controllers, services, pages, hooks, etc.)
   - Technical patterns in use (queries, caching, auth, validation, etc.)

3. **Quick-check the index.** Read the first 10 lines of `docs/knowledge/index.md`.
   - **If not found:** proceed to Phase 2 without knowledge context.
   - **If both `<!-- Solutions: 0 -->` and `<!-- Modules: 0 -->`:** proceed to Phase 2 without knowledge context.
   - **Otherwise:** proceed to step 4.

4. **Spawn learnings-researcher.** Dispatch the agent with the identified modules and components:

   ```
   Agent(
     subagent_type: "kg:learnings-researcher",
     description: "Research knowledge for code review",
     prompt: "Search for institutional learnings relevant to these modules and components: [modules and components from step 2]. Include module file maps."
   )
   ```

5. **Use response.** Use the returned learnings and module context for Phase 2 cross-referencing.

6. **Load the coding rules.** Read `${CLAUDE_PLUGIN_ROOT}/rules/` for the stack in
   `kg.local.md` — or `knowledge-garden.local.md` for projects set up before 0.4.0 — loading
   `laravel.md`, `nextjs.md`, or both. Skip for a `generic` stack.
   Review the diff against these as well as against the knowledge base.

   Report a rule violation only when it is in code the diff **adds or changes**. Pre-existing code
   that departs from the ruleset is not a review finding — and if the project departs from it
   consistently, the ruleset is what's wrong. Say so instead.

## Phase 2: Knowledge-Informed Review

With institutional knowledge loaded, perform the review.

1. **Cross-reference changes against known issues.** For each changed file/module:
   - Check if any documented root causes apply to the changes
   - Check if documented symptoms could be introduced by the changes
   - Check if critical patterns are being followed or violated

2. **Review categories.** Evaluate the changes across these dimensions:

   **Knowledge-backed findings** (from the knowledge base):
   - Does this change repeat a documented mistake?
   - Does it touch an area with known critical patterns?
   - Does it handle edge cases that past solutions identified?

   **General code quality:**
   - Correctness: Does the code do what it intends?
   - Patterns: Does it follow the project's established patterns?
   - Edge cases: Are boundary conditions handled?
   - Performance: Any obvious performance concerns?

3. **Severity classification.** Rate each finding:
   - **Critical**: Repeats a documented root cause or violates a critical pattern
   - **Warning**: Touches an area with past issues but doesn't clearly repeat them
   - **Suggestion**: General improvement not tied to documented knowledge

## Phase 3: Report

Present the review in this structure:

```
## Knowledge-Backed Code Review

### Review Scope
- **Files reviewed:** X files
- **Modules affected:** [list]
- **Knowledge matches:** Y relevant learnings consulted

### Critical Findings
[Findings backed by documented issues -- highest priority]

#### 1. [Finding title]
- **File:** `path/to/file.ext:line`
- **Knowledge ref:** [docs/knowledge/solutions/category/filename.md]
- **Issue:** [What the documented learning says about this pattern]
- **Recommendation:** [What should change]

### Warnings
[Findings in areas with past issues]

### Suggestions
[General improvements]

### Knowledge Gaps
[Areas touched by changes that have no documented knowledge -- potential blind spots]

### Summary
- Critical: X findings
- Warnings: Y findings
- Suggestions: Z findings
- Verdict: [Approve / Request changes / Needs discussion]
```

## Arguments

- `$ARGUMENTS` (optional): file path, branch name, or PR number to review. If omitted, reviews current staged/unstaged changes.

</instructions>
