---
name: plan
description: Create implementation plans informed by past learnings and known gotchas
argument-hint: "[feature description, brainstorm file, or specification]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - Edit
  - EnterPlanMode
  - TodoWrite
---

# Knowledge-Backed Implementation Plan

Create an implementation plan that leverages institutional knowledge to avoid known pitfalls and apply proven patterns.

<instructions>

## Phase 1: Knowledge Context

Surface relevant institutional knowledge -- but only if there's knowledge to surface.

1. **Determine input.** If `$ARGUMENTS` points to a file (brainstorm, spec, or doc), read it fully. Otherwise treat `$ARGUMENTS` as the feature description.

2. **Quick-check the index.** Read the first 10 lines of `docs/knowledge/index.md`.
   - **If not found:** suggest running `/kg:setup`. STOP.
   - **If both `<!-- Solutions: 0 -->` and `<!-- Modules: 0 -->`:** skip to Phase 2. No knowledge to surface.
   - **Otherwise:** proceed to step 3.

3. **Spawn learnings-researcher.** Dispatch the agent with the plan topic:

   ```
   Agent(
     subagent_type: "kg:learnings-researcher",
     description: "Research knowledge for planning",
     prompt: "Search for institutional learnings relevant to this feature: [input from step 1]"
   )
   ```

4. **Use response.** Use the returned learnings, gotchas, critical patterns, and module context for Phase 2.

## Scope Check

After Phase 1, assess whether a full plan is the right workflow:

- **De-escalate to `/kg:quickfix`** if: the task is a specific bug or minor issue with an obvious fix that touches < 3 files, needs no architectural decisions, and has no real risk.
- **Escalate to `/kg:brainstorm`** if: requirements are vague or ambiguous, there are multiple fundamentally different approaches with unclear tradeoffs, or the user hasn't decided what to build yet.

If either applies, suggest the alternative:

```
This looks like a [quickfix / brainstorm-first task] -- [reason].
Suggest: /kg:quickfix [topic] or /kg:brainstorm [topic]
```

Wait for user response before proceeding or switching.

## Phase 2: Create Plan

With knowledge context established, create a structured implementation plan.

1. **Analyze scope.** Break down the feature/task into concrete implementation steps. Consider:
   - Which files need to change?
   - What order should changes happen in?
   - What are the dependencies between steps?

2. **Apply knowledge guardrails.** For each step, cross-reference against learnings:
   - If a step touches a module with documented issues, add a warning note
   - If a step involves a pattern that has a documented gotcha, reference it
   - If critical patterns apply, ensure the plan follows them

3. **Flag risks.** Based on knowledge base findings, explicitly call out:
   - Steps that touch areas with past critical/high-severity issues
   - Patterns that previously caused problems
   - Areas with no documented knowledge (blind spots)

4. **Get user input.** Use AskUserQuestion if there are ambiguous requirements or multiple valid approaches.

## Phase 3: Save Plan

1. **Create plans directory** if it doesn't exist:
   ```bash
   mkdir -p docs/plans
   ```

2. **Generate filename**: `YYYY-MM-DD-<type>-<sanitized-name>-plan.md` where type is one of: feature, bugfix, refactor, migration, optimization.

3. **Write plan file** with this structure:

   ```markdown
   # Plan: [Feature/Task Name]

   **Date:** YYYY-MM-DD
   **Type:** [feature|bugfix|refactor|migration|optimization]
   **Status:** Draft

   ## Knowledge Context

   ### Relevant Learnings
   - [Learning title](../knowledge/solutions/category/filename.md): [key insight]

   ### Known Gotchas
   - [Gotcha description and how the plan avoids it]

   ### Critical Patterns Applied
   - [Pattern and where it's applied in this plan]

   ## Overview

   [Brief description of what this plan accomplishes]

   ## Implementation Steps

   ### Step 1: [Description]
   - **Files:** `path/to/file.ext`
   - **Details:** What to do
   - **Knowledge note:** [If applicable, reference to relevant learning]

   ### Step 2: [Description]
   ...

   ## Risks and Mitigations

   | Risk | Likelihood | Mitigation |
   |------|-----------|------------|
   | [risk] | [high/medium/low] | [mitigation strategy] |

   ## Testing Strategy

   - [ ] [Test case 1]
   - [ ] [Test case 2]

   ## Open Questions

   - [Any unresolved questions]
   ```

4. **Confirm output.** Tell the user where the plan was saved and suggest:
   - `/kg:work <plan-file>` to start executing the plan
   - Review and refine the plan first

## Arguments

- `$ARGUMENTS` (required): feature description, path to a brainstorm/spec file, or inline specification.

</instructions>
