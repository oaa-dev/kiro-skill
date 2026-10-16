# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.6.0] - 2026-10-15

### Added

- **`audit` skill (`/kg:audit`)**: audits the existing codebase (whole project, one module, or one
  path) against three dimensions: the project's own rules (`CLAUDE.md`, `critical-patterns.md`,
  stack ruleset), best practices, and security (OWASP-mapped checks plus `composer audit` /
  `npm audit`). Grep-driven candidates are verified in context before they're reported, and every
  finding carries `path:line` evidence, a severity, and a stable rule id.
- Checklists in `skills/audit/references/` (`security-checklist.md`, `best-practices.md`).
- Dated audit reports in `docs/knowledge/audits/`.

### Changed

- **`rules/laravel.md` §12 Exceptions**: all API exceptions are rendered by the global handler in
  `bootstrap/app.php` using the `ApiResponse` envelope, with a status map and the
  converted-exception gotcha (`ModelNotFoundException` → `NotFoundHttpException`).
- **`rules/laravel.md` §10 Tests**: one feature test file per controller, mirroring its path,
  with a required happy-path test for every action; 422, 401, 403, 404, and filter cases are
  recommended.

## [0.5.0] - 2026-10-02

### Added

- **`ask` skill (`/kg:ask`)** — answers questions about project structure, flow, architecture,
  layers, and past issues (knowledge base first, then targeted code search with `path:line`
  sources), or general questions directly with no knowledge lookup.
- Saved answers in `docs/knowledge/answers/`, indexed in a new Answers table in
  `docs/knowledge/index.md`, created by `setup`, and surfaced by `learnings-researcher`.

## [0.4.0] - 2026-08-10

### Added

- **`scripts/validate.py`** — structural validation for the marketplace. Every check corresponds
  to a bug that shipped at least once: `allowed-tools` typos and retired tool names, tools used in
  prose but never declared, command/skill name collisions, dangling `/kg:<name>` and
  `subagent_type` references, broken links, the empty-index template contract, manifest version
  drift, and component counts that disagree with the filesystem. Verified against 18 reintroduced
  defects; exits non-zero on any of them, and the clean tree is silent.

### Changed

- **Renamed the plugin from `knowledge-garden` to `kg`.** Invocations shorten from
  `/knowledge-garden:compound` to `/kg:compound` — 13 characters per command. The human-readable
  title stays **Knowledge Garden** in the README and the Cursor `displayName`, so the short name is
  only what you type.
- The per-project config file is now `kg.local.md`. Every reader falls back to
  `knowledge-garden.local.md`, so projects set up before 0.4.0 keep working untouched; `setup`
  renames it in place when it finds one.

### Migration

This changes the plugin's identity, so the old install must be removed:

```
/plugin uninstall knowledge-garden
/plugin install kg
```

`~/.claude/settings.json` needs its `enabledPlugins` key changed from
`knowledge-garden@personal-plugins` to `kg@personal-plugins`.

## [0.3.0] - 2026-08-10

### Added

- **Coding rules — a third knowledge tier.** `rules/laravel.md` and `rules/nextjs.md` ship with the
  plugin and describe how code is written: naming case per artefact, the
  `routes → Requests → Controllers → Data → Services → Repositories → Models` flow and its three
  boundary rules, Resource + `ApiResponse` envelope requirements, Spatie QueryBuilder in the
  repository, DTO/`Optional` semantics, and the Next.js `services → hooks → page` flow.
  Derived from conventions common to pos, pilaPH, and laravel-react-template — not invented.
- `rules/README.md` documenting precedence and how to report a conflict.
- Agents now load the ruleset for the detected stack before writing code: `task-worker` (step 1),
  `/work` (both serial and parallel modes), `quickfix`, and `/review`.
- `task-worker` reports any rule it departed from in its result Warnings, so a deliberate departure
  is visible rather than silent.
- `setup` records the applicable ruleset in `knowledge-garden.local.md` and surfaces it in the
  completion summary.

### Changed

- `task-worker`'s only style instruction was "match naming conventions and code style already
  present in the codebase" — i.e. read some files and guess. It now loads an explicit ruleset,
  with the surrounding code and the project's `CLAUDE.md` as the higher authorities.
- `/work` passes only project-specific *overrides* to workers, not the ruleset itself — workers
  read it from `${CLAUDE_PLUGIN_ROOT}` so there is one copy, not one per dispatch prompt.

## [0.2.0] - 2026-08-10

### Fixed

- **Agent dispatch was silently broken.** `allowed-tools` declared the obsolete `Task` tool in
  `/brainstorm`, `/plan`, `/review`, and `/work`, so none of them could actually dispatch
  `learnings-researcher`. Renamed to `Agent` in both the allowlists and the call bodies. This was
  the load-bearing bug: with retrieval dead, capture had no payoff and the knowledge loop stalled.
- **Command references used invalid `::` syntax.** 23 references to `/knowledge-garden::<name>`
  corrected to a single colon. This included the recovery instruction shown whenever the knowledge
  index is missing, which made the documented first-run path a dead end.
- Namespaced all bare command references (`/setup`, `/work`, `/plan`, …) to
  `/knowledge-garden:<name>` so they resolve.
- Removed a dangling reference to a `/debug` command that does not exist in this plugin.
- Normalized command `name:` frontmatter to bare names; the plugin namespace is applied
  automatically.
- Corrected `quickfix`'s `learnings-researcher` dispatch, which used a prose format instead of a
  real agent call and omitted the plugin namespace.
- Component counts now agree across `plugin.json`, the Cursor manifest, `marketplace.json`, and
  both READMEs. They previously disagreed in all five places.
- `homepage`/`repository` now point at `oaa-dev/claude-skill` instead of an unrelated repo.

### Removed

- `frontend-design` command and skill — duplicated the official `frontend-design` plugin, which is
  a better-maintained implementation of the same idea.
- Thin wrapper commands `quickfix`, `knowledge-insights`, `knowledge-prune`, and `playwright-test`.
  Each shadowed a same-named skill, making the skill unreachable while contributing nothing beyond
  a "run the X skill" instruction. Skills are directly invocable as `/knowledge-garden:<name>`.
  Argument handling the wrappers documented has been folded into the skills.
- `Task` from `task-worker`'s `allowed-tools` rather than renaming it to `Agent`. The entry was
  already inert, and granting a leaf executor the ability to spawn sub-agents would allow unbounded
  recursion inside parallel waves.

### Added

- Generic stack-agnostic schema in `setup` for projects that are neither Laravel nor Next.js.
  Previously the "Unknown" branch forced a choice between the two.
- Guidance in `setup` on extending schema enums instead of forcing a wrong match — a mislabeled
  solution is invisible to `knowledge-insights` aggregation.
- Explicit `Arguments` section in `knowledge-prune` documenting the staleness threshold.
- "The Loop" section in the plugin README, including the health check for whether capture is
  actually happening.

## [0.1.0] - 2026-02-25

### Added

- Initial release
- Setup skill with stack detection (Laravel, Next.js, full-stack) and dynamic schema generation
- Module docs skill with reference-tracing scanning strategies for Laravel and Next.js
- Knowledge docs skill for capturing solved problems with YAML frontmatter
- Knowledge insights skill for analyzing knowledge base patterns
- Knowledge prune skill for flagging and archiving stale learnings
- Learnings researcher agent for surfacing institutional knowledge
- Commands: generate-module-docs, knowledge-insights, knowledge-prune
