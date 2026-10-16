---
name: kg-brainstorm
description: "Explore requirements and approaches with knowledge-backed context"
license: MIT
---

# Knowledge-Backed Brainstorm

Explore requirements and approaches for a topic, informed by institutional knowledge from the knowledge garden.

<instructions>

## Phase 1: Knowledge Context

Surface relevant institutional knowledge -- but only if there's knowledge to surface.

1. **Quick-check the index.** Read the first 10 lines of `docs/knowledge/index.md`.
   - **If not found:** suggest running `/kg-setup`. STOP.
   - **If both `<!-- Solutions: 0 -->` and `<!-- Modules: 0 -->`:** skip to Phase 2. No knowledge to surface.
   - **Otherwise:** proceed to step 2.

2. **Spawn kg-learnings-researcher.** Dispatch the agent with the brainstorm topic:

   Delegate to the `kg-learnings-researcher` sub-agent (installed by `/kg-setup`) with this prompt:

   > Search for institutional learnings relevant to: [input]

   If that agent is not available, do the lookup yourself: read `docs/knowledge/index.md`, match the task's modules, components and keywords against its Critical Patterns, Modules, Solutions and Answers tables, read the matching module docs and at most 3 strongly matching solution files, and distill the learnings, gotchas and module file maps.

3. **Use response.** Use the returned learnings, patterns, and module context as the knowledge foundation for Phase 2.

## Scope Check

After Phase 1, assess whether brainstorming is the right workflow:

- **De-escalate to `/kg-quickfix`** if: the topic is a specific bug or issue with an obvious fix that touches < 3 files and has no real design tradeoffs.
- **Escalate to `/kg-plan`** if: the approach is already clear, there's no ambiguity in requirements, and the user just needs an implementation plan.

If either applies, suggest the alternative:

```
This looks like a [quickfix / ready-to-plan task] -- [reason].
Suggest: /kg-quickfix [topic] or /kg-plan [topic]
```

Wait for user response before proceeding or switching.

## Phase 2: Collaborative Brainstorm

With knowledge context established, guide exploration of the topic from the input.

1. **Frame the topic.** Summarize what is being brainstormed and any constraints from the knowledge context.

2. **Explore dimensions.** Walk through these areas with the user:
   - **Problem/Goal**: What exactly needs to be solved or built?
   - **Users/Stakeholders**: Who is affected?
   - **Approaches**: What are the possible ways to tackle this? (Present 2-4 options)
   - **Tradeoffs**: What are the pros/cons of each approach?
   - **Known risks**: What does the knowledge base tell us about pitfalls in this area?
   - **Open questions**: What do we still need to figure out?

3. **Iterate with user.** Ask the user for the user's preferences on approaches and tradeoffs. Continue refining until the brainstorm feels complete.

## Phase 3: Save Brainstorm

1. **Create brainstorm directory** if it doesn't exist:
   ```bash
   mkdir -p docs/brainstorms
   ```

2. **Generate filename**: `YYYY-MM-DD-<sanitized-topic>.md` where the topic is derived from the input.

3. **Write brainstorm file** with this structure:

   ```markdown
   # Brainstorm: [Topic]

   **Date:** YYYY-MM-DD
   **Status:** Draft

   ## Knowledge Context

   [Summary of relevant learnings surfaced in Phase 1]

   ## Problem / Goal

   [What we're trying to solve]

   ## Approaches Considered

   ### Approach A: [Name]
   - **Description:** ...
   - **Pros:** ...
   - **Cons:** ...

   ### Approach B: [Name]
   - **Description:** ...
   - **Pros:** ...
   - **Cons:** ...

   ## Decision

   [Preferred approach and rationale, or "TBD" if not yet decided]

   ## Open Questions

   - [Unresolved questions]

   ## Next Steps

   - [ ] [Action items]
   ```

4. **Confirm output.** Tell the user where the brainstorm was saved and suggest next steps:
   - `/kg-plan` to create an implementation plan from this brainstorm
   - Continue refining the brainstorm

## Input

The input is the text typed after the slash command, or the user's request when Kiro loads this skill on its own.

- **Input** (required): topic or feature description to brainstorm about.

</instructions>
