<img src="icon.png" alt="Knowledge Garden" width="128">

# Knowledge Garden

Project knowledge management for Laravel, Next.js, and generic stacks. Module indexing, dynamic schemas, knowledge capture, insights, and pruning.
Developed by [oaa-dev](https://github.com/oaa-dev).

## Components

| Type | Count | Names |
|------|-------|-------|
| Agents | 2 | learnings-researcher, task-worker |
| Commands | 7 | brainstorm, compound, generate-module-docs, plan, reindex, review, work |
| Skills | 10 | setup, module-docs, knowledge-docs, knowledge-index, knowledge-insights, knowledge-prune, playwright-test, quickfix, ask, audit |
| Rulesets | 2 | laravel, nextjs |

Commands and skills never share a name. A skill is invoked the same way a command is —
`/kg:<name>` — so `/kg:setup` and `/kg:quickfix` work
even though they are skills, not commands.

## Quick Start

1. Install the plugin
2. Run `/kg:setup` to detect your stack and generate a schema
3. Run `/kg:generate-module-docs` to index your project modules
4. Use `/kg:compound` after solving problems to capture learnings
5. Run `/kg:knowledge-insights` to see patterns across your knowledge base
6. Run `/kg:knowledge-prune` periodically to clean up stale docs

## The Loop

The plugin only pays for itself if capture and retrieval both work:

```
/brainstorm ─┐
/plan ───────┼─→ learnings-researcher reads past solutions ──→ better work
/work ───────┤
/review ─────┘                                                     │
                                                                   ▼
              docs/knowledge/solutions/  ←────────────  /compound captures it
```

If `/compound` stops getting run, retrieval has nothing to surface and the loop stalls. The
health check is simple: is the solution count in `docs/knowledge/index.md` still going up?

## Coding Rules

`rules/laravel.md` and `rules/nextjs.md` ship with the plugin and describe **how code is written** —
naming, layering, which class may touch what. Agents load the ruleset matching the project's stack
before writing anything.

This is a third tier, separate from the two knowledge stores:

| Source | Holds | Written by |
|---|---|---|
| `rules/*.md` | how to write code | shipped with the plugin |
| `critical-patterns.md` | rules earned from a failure in this repo | `/compound` |
| `solutions/**` | what broke and why | `/compound` |

**Precedence** — the more specific source wins: the project's `CLAUDE.md`, then
`critical-patterns.md`, then consistent existing practice, then the ruleset. Rules govern code
being *added or changed*; they are never a licence to rewrite working code. An agent that departs
from a rule reports it rather than deciding silently.

See [rules/README.md](./rules/README.md).

## Skills

### setup

Interactive setup that detects your stack (Laravel, Next.js, both, or generic), generates a `docs/knowledge/schema.yaml` with stack-appropriate enums, and creates the knowledge directory structure. Projects on an unrecognized stack get a stack-agnostic schema rather than a forced-fit Laravel or Next.js one.

### module-docs

Generates per-module markdown files in `docs/knowledge/modules/`. Uses a reference-tracing approach: starts from module anchors (models for Laravel, route segments for Next.js) and greps the entire project to find everything connected.

### knowledge-docs

Captures solved problems as categorized documentation with YAML frontmatter. Not model-invocable on its own — reached through `/kg:compound`.

### knowledge-index

Pre-computes a single `docs/knowledge/index.md` from every solution's frontmatter, so lookups are one file read instead of many Grep+Read calls. Regenerate with `/kg:reindex`.

### knowledge-insights

Analyzes the knowledge base to surface patterns: top problem types, most affected modules, common root causes, severity distribution, monthly trends, and hotspot modules.

### knowledge-prune

Scores documented solutions on staleness (age, severity, framework version, pattern links, module existence) and presents candidates for archiving, deletion, or retention. Accepts an optional threshold argument (default 50).

### playwright-test

Writes, runs, and analyzes Playwright E2E tests. Detects test scope from arguments or git changes, discovers project conventions from existing tests, presents a test plan for approval, runs tests, diagnoses failures, and optionally captures non-trivial testing insights into the knowledge base.

### quickfix

Fixes minor issues fast with a mandatory knowledge check but no planning phase. Escalates to `/kg:plan` or `/kg:brainstorm` when the issue turns out to be bigger than a quickfix.

### ask

Answers any question -- project structure, flow, architecture, layers, past issues, or general topics. Project questions are answered knowledge-base-first (index, architecture doc, module docs, solutions), then with targeted code search, citing `path:line` sources. General questions are answered directly with no knowledge lookup. Answers that required code digging can be saved to `docs/knowledge/answers/` and are indexed, so the next lookup is a single read.

### audit

Audits the codebase as it stands, not a diff, across three dimensions: **rules** (the project's own `CLAUDE.md` / `AGENTS.md`, `critical-patterns.md`, and the stack ruleset, with convention detection so a consistent project-wide departure from the stack ruleset becomes a single note, not 50 findings), **practices** (N+1 queries, unbounded queries, missing indexes, swallowed exceptions, missing transactions, type safety, test gaps, complexity hotspots), and **security** (secrets, injection, XSS, authorization, tenant scoping, mass assignment, CSRF/CORS, uploads, crypto, config, mapped to the OWASP Top 10, plus `composer audit` / `npm audit`). Every finding is verified in context and cited with `path:line`. Reports are saved to `docs/knowledge/audits/`. Read-only, and it touches no other skill's files: fixes are handed off to `/kg:quickfix` or `/kg:plan`.

```
/kg:audit                       # all three, whole project
/kg:audit security              # one dimension
/kg:audit rules Order           # one dimension, one module
/kg:audit rules,security app/Http
```

## Agents

### learnings-researcher

Searches `docs/knowledge/solutions/` for relevant past solutions by frontmatter metadata. Uses grep-first filtering for efficiency and runs on Haiku to keep lookups cheap. Dispatched automatically by `/brainstorm`, `/plan`, `/work`, `/review`, and `/quickfix`.

### task-worker

Executes a single scoped task dispatched by `/kg:work` in parallel mode. Implements, verifies, and reports — it does not commit, ask questions, or spawn further agents.

## Commands

| Command | Description |
|---------|-------------|
| `/kg:brainstorm` | Explore requirements and approaches with knowledge-backed context |
| `/kg:compound` | Document a recently solved problem to compound your knowledge |
| `/kg:generate-module-docs` | Scan project and generate module documentation |
| `/kg:plan` | Create implementation plans informed by past learnings |
| `/kg:reindex` | Regenerate the knowledge index from all solution files |
| `/kg:review` | Review code against documented patterns and known issues |
| `/kg:work` | Execute work with knowledge guardrails and incremental commits |

## Directory Structure (Generated)

After setup, your project will have:

```
docs/knowledge/
├── schema.yaml          # Stack-specific schema (generated by setup)
├── index.md             # Pre-computed lookup index (generated by knowledge-index)
├── modules/             # Module docs (generated by module-docs)
│   ├── user.md
│   ├── order.md
│   └── ...
├── solutions/           # Problem docs (created by knowledge-docs)
│   ├── performance-issues/
│   ├── runtime-errors/
│   └── ...
├── answers/             # Saved /kg:ask answers (optional)
├── audits/              # Dated /kg:audit reports (optional)
├── patterns/
│   └── critical-patterns.md
└── archive/             # Archived stale docs (by knowledge-prune)
```

## License

MIT
