---
name: work
description: Execute work with knowledge guardrails and incremental commits
argument-hint: "[plan file, task description, or specification]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - Edit
  - TodoWrite
---

# Knowledge-Guarded Work Execution

Execute a plan or task systematically with knowledge guardrails that surface relevant learnings before touching each module.

<instructions>

## Phase 1: Knowledge Context

Surface relevant institutional knowledge -- but only if there's knowledge to surface.

1. **Read the work input.** If `$ARGUMENTS` points to a file (plan, spec, or todo), read it fully. Otherwise treat `$ARGUMENTS` as the task description.

2. **Quick-check the index.** Read the first 10 lines of `docs/knowledge/index.md`.
   - **If not found:** suggest running `/kg:setup`. STOP.
   - **If both `<!-- Solutions: 0 -->` and `<!-- Modules: 0 -->`:** skip to Phase 2. No knowledge to surface.
   - **Otherwise:** proceed to step 3.

3. **Spawn learnings-researcher.** Dispatch the agent with the work context:

   ```
   Agent(
     subagent_type: "kg:learnings-researcher",
     description: "Research knowledge for work execution",
     prompt: "Search for institutional learnings relevant to this work: [input from step 1]. Include module file maps for any modules being touched."
   )
   ```

4. **Use response.** Use the returned learnings, watch-outs, critical patterns, and module context for Phase 2.

## Phase 2: Task Breakdown & Dependency Analysis

1. **Parse tasks.** Break the work into discrete, ordered tasks. If the input is a plan file, extract steps directly from it.

2. **Annotate file scope.** For each task, identify which files it will create or modify:
   - Extract file references from the plan (paths, module names, component names)
   - If the plan doesn't specify files, infer from task descriptions using Glob/Grep to locate relevant code

3. **Build dependency graph.** Analyze tasks for dependencies:
   - **Explicit ordering**: task descriptions that say "after X", "requires Y", "once Z is done"
   - **Data dependencies**: task B uses a type/function/export that task A creates
   - **File overlap**: if two tasks modify the same file, they MUST be sequential (never parallel)

4. **Form parallel waves.** Group tasks into waves of independent work:
   - **Wave 1**: tasks with no dependencies (can all run in parallel)
   - **Wave 2**: tasks that depend only on Wave 1 tasks
   - **Wave N**: tasks that depend only on tasks in earlier waves
   - Tasks within a wave have zero dependencies on each other and zero file overlap

5. **Create task list.** Use TodoWrite to track progress:
   - Each task should be small enough for one commit
   - Include wave assignment and file scope per task
   - Flag tasks that touch modules with documented issues

6. **Present execution plan.** Show the user the wave structure:

   ```
   ## Execution Plan

   **Wave 1** (parallel - N tasks):
   - Task A: [description] → files: [list]
   - Task B: [description] → files: [list]

   **Wave 2** (parallel - N tasks, after Wave 1):
   - Task C: [description] → files: [list]

   **Wave 3** (serial - depends on Wave 2):
   - Task D: [description] → files: [list]
   ```

   Ask the user:
   - **Parallel mode** (recommended when 2+ tasks in any wave): dispatch independent tasks as parallel agents
   - **Serial mode**: execute all tasks one at a time (classic behavior)

   If all tasks are in a single wave chain (every task depends on the previous), skip the question and use serial mode automatically.

## Phase 3: Execute Tasks

**Before starting any task**, snapshot the current HEAD so Phase 4 can diff against it:
```bash
WORK_BASELINE=$(git rev-parse HEAD 2>/dev/null || echo "no-git")
```

### Serial Mode

Use when the user chooses serial, or when all tasks are dependent.

For each task in order:

0. **Load the coding rules once**, before the first task: read `${CLAUDE_PLUGIN_ROOT}/rules/` for the
   stack in `kg.local.md` — or `knowledge-garden.local.md` for projects set up before 0.4.0 —
   loading `laravel.md`, `nextjs.md`, or both. Skip for a `generic` stack. They stay in context for
   every task in the run.

1. **Apply knowledge context.** Cross-reference this task's module/component against the learnings and module context returned by the agent in Phase 1. Note any relevant gotchas before starting.

2. **Execute the task.** Implement the change following established patterns and knowledge guardrails.

3. **Verify.** Run relevant tests or checks after each task:
   ```bash
   # Run tests if available
   # Lint if configured
   # Type-check if applicable
   ```

4. **Commit incrementally.** After each completed task, suggest a commit with a descriptive message. Ask the user if they want to commit now or continue.

5. **Update progress.** Mark the task as complete in the todo list.

### Parallel Mode

Use when the user chooses parallel and at least one wave has 2+ independent tasks.

For each wave:

1. **Prepare knowledge context.** Use the learnings, module context, and patterns returned by the agent in Phase 1. Filter to the modules/components relevant to this wave's tasks and compile a knowledge briefing to pass to each worker.

   Workers load the coding rules themselves from `${CLAUDE_PLUGIN_ROOT}/rules/` — do not paste the
   ruleset into the prompt. Include only project-specific overrides: anything in the project's
   `CLAUDE.md` or `critical-patterns.md` that contradicts or extends the ruleset for these files.

2. **Dispatch task-worker agents.** Launch all tasks in the wave simultaneously using `Agent(run_in_background: true)` -- all in a single message for true parallelism:

   ```
   For each task in the current wave, dispatch a task-worker agent:

   Agent(
     subagent_type: "kg:task-worker",
     description: "Execute task: [brief]",
     prompt: """
       ## Task
       [task description]

       ## File Scope
       [files this task should create/modify]

       ## Knowledge Context
       [relevant learnings, patterns, gotchas compiled in step 1]

       ## Plan Context
       [enough plan context to understand the broader goal]
     """,
     run_in_background: true
   )
   ```

   If a `kg:task-worker` agent is defined, use it. Otherwise fall back to `general-purpose`. Include task-worker constraints in the prompt (no commits, no user questions, stay in file scope).

3. **Collect results.** Wait for all background agents to complete. Review each agent's structured result (status, files changed, tests, warnings).

4. **Run full test suite.** After all workers in the wave complete, run the project's full test suite to catch cross-task conflicts:
   ```bash
   # Run full test suite (project-specific command)
   ```
   If tests fail, diagnose whether the conflict is between parallel tasks or an individual task issue. Fix before proceeding.

5. **Present wave results.** Show the user a summary:

   ```
   ## Wave N Results

   **Task A**: completed -- changed file1.ext, file2.ext
   **Task B**: completed -- changed file3.ext
   **Task C**: partial -- [issue description]

   **Tests**: all passing | N failures
   **Warnings**: [any cross-task issues]
   ```

   Ask the user:
   - Commit all wave changes together (recommended)
   - Commit per task
   - Fix issues first

6. **Proceed to next wave.** After the user approves the commit, move to the next wave. Tasks in the next wave can now reference outputs from this wave.

## Phase 4: Auto-Maintain Knowledge Base

After all tasks are complete, the AI assesses the work and auto-maintains the knowledge base. Uses `$WORK_BASELINE` captured at the start of Phase 3.

### Step 1: Summarize Work

Summarize the work completed: tasks done, files changed, any knowledge-backed decisions made during execution.

### Step 2: Detect Structural Changes (auto, silent)

Compare against the pre-work baseline to find structural changes:

```bash
git diff --name-status $WORK_BASELINE HEAD
```

If not in a git repo or no commits were made, skip to Step 3.

**Trigger module docs regeneration if ANY of these are true:**
- New files added (`A`) in module directories (models, controllers, services, repositories, pages, components)
- Files renamed (`R`) or deleted (`D`) in module directories
- New migration files added
- New route files added

If triggered, run in background so it doesn't block the user:
```
Agent(
  subagent_type: "general-purpose",
  description: "Regenerate module docs for affected modules",
  prompt: "Run the kg:module-docs skill for these modules only: [affected module names]. Then run the kg:knowledge-index skill to rebuild the index.",
  run_in_background: true
)
```

If not triggered: skip silently.

### Step 3: Recommend Knowledge Capture (if warranted)

Review the work execution (the full Phase 3) for signals of non-trivial problem-solving.

**Recommend running `/kg:compound` if 2+ of these signals are present:**
- Errors were encountered and resolved during execution (failed tests, runtime errors, unexpected behavior)
- Multiple attempts were needed to get something working (debugging loops, reverts, retries)
- The root cause was different from the initially suspected cause
- The fix required reading framework source code or documentation to understand internal behavior
- A non-obvious workaround was needed (not just following established patterns)

**Skip entirely if ALL of these are true:**
- All tasks completed on first attempt without errors
- Changes were straightforward (adding new files, simple CRUD, following documented patterns)
- No debugging or investigation was needed

If signals detected, **recommend** (don't auto-run) with a one-line summary of what would be documented:

```
Tip: This session hit [brief description of the non-trivial problem].
Run /kg:compound to capture it while the context is fresh.
```

This keeps the user in control -- they decide whether to spend the time documenting. The AI just makes sure they don't forget.

### Step 4: Report

```
## Work Complete

**Tasks:** N completed
**Files changed:** [list]
**Knowledge maintenance:**
- Module docs: [updating in background for X, Y | no structural changes]
- Knowledge capture: [recommended -- see above | not needed]
```

## Arguments

- `$ARGUMENTS` (required): path to a plan file, task description, or inline specification.

</instructions>
