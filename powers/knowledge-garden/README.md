<img src="icon.png" alt="Knowledge Garden" width="128">

# Knowledge Garden (Kiro power)

Project knowledge management for Laravel, Next.js, and generic stacks, packaged as a Kiro power.
Developed by [oaa-dev](https://github.com/oaa-dev).

> **Generated file.** This power is built from the Claude Code plugin in `plugins/kg` by
> `scripts/build-kiro-power.py`. Edit the plugin, then rebuild. Do not edit this folder by hand.

## Install

1. In Kiro, open the **Powers** panel and choose **Add Custom Power**.
2. Pick **Import power from GitHub** and enter `https://github.com/oaa-dev/kiro-skill` (`powers/knowledge-garden`
   is the power folder), or **Import power from a folder** and select a local checkout of
   `powers/knowledge-garden`.
3. Open your project and, in Kiro chat, type:

   ```text
   Set up Knowledge Garden for this project
   ```

   Before setup there is no `/kg-` slash command in the workspace, so you ask in plain words.
   Kiro activates the power and runs its `kg-setup` skill.
4. Reload the Kiro window or start a new chat. Type `/` and the `/kg-` commands are listed.

`kg-setup` does more here than in Claude Code. Kiro makes slash commands from the skills in a
workspace's `.kiro/skills/`, and a power can only ship skills and MCP config. So setup copies
everything into your project with `skills/kg-setup/scripts/install.sh`:

| Installed into the project | What it is |
|---|---|
| `.kiro/skills/kg-*/` | The 16 other skills, as `/kg-plan`, `/kg-work`, `/kg-review` ... |
| `.kiro/agents/kg-learnings-researcher.md` | Read-only knowledge lookup sub-agent |
| `.kiro/agents/kg-task-worker.md` | Parallel task executor used by `/kg-work` |
| `.kiro/steering/kg-laravel.md` | Laravel coding rules, `fileMatch` on `**/*.php` |
| `.kiro/steering/kg-nextjs.md` | Next.js coding rules, `fileMatch` on `**/*.ts`, `**/*.tsx` |
| `.kiro/kg-manifest.txt` | What setup installed, so a re-run can upgrade safely |

Commit `.kiro/` if your team should share the commands. Workspace agents load only in a trusted
workspace; without them the skills still work and do their lookups inline.

`kg-setup` itself stays in the power and is not copied, so it never goes stale in a project.

### Upgrading

Update the power, then ask Kiro to set up Knowledge Garden again. Files that still match what
setup installed are replaced; files you edited are kept and listed. To take the new version of an
edited file, delete it and run setup again.

### Optional: `/kg-setup` as a slash command everywhere

To type `/kg-setup` instead of asking in words, copy the power's skills into your user skills
folder once (re-run after updating the power):

```bash
mkdir -p ~/.kiro/skills && cp -r powers/knowledge-garden/skills/kg-* ~/.kiro/skills/
```

That also makes every `/kg-` command available in all projects. Running `/kg-setup` in a project
still installs the workspace copies, the agents and the steering. Workspace skills take priority
over user skills, so a project keeps the version its setup installed.

## Skills

Every Claude Code command and skill is a Kiro skill, invoked as `/kg-<name>`:

| Kiro | Claude Code | What it does |
|---|---|---|
| `/kg-setup` | `/kg:setup` | Detect stack, create schema and `docs/knowledge/`, install skills, agents and steering |
| `/kg-generate-module-docs` | `/kg:generate-module-docs` | Index project modules |
| `/kg-module-docs` | skill | Per-module docs by reference tracing |
| `/kg-brainstorm` | `/kg:brainstorm` | Knowledge-backed brainstorm |
| `/kg-plan` | `/kg:plan` | Knowledge-backed implementation plan |
| `/kg-work` | `/kg:work` | Execute a plan in waves, serial or parallel |
| `/kg-review` | `/kg:review` | Review changes against known issues and rules |
| `/kg-quickfix` | `/kg:quickfix` | Small fixes with a mandatory knowledge check |
| `/kg-ask` | `/kg:ask` | Answer questions, knowledge base first |
| `/kg-audit` | `/kg:audit` | Audit existing code for rules, best practices and security |
| `/kg-compound` | `/kg:compound` | Capture a solved problem |
| `/kg-knowledge-docs` | skill | The capture workflow behind `/kg-compound` |
| `/kg-reindex` | `/kg:reindex` | Rebuild `docs/knowledge/index.md` |
| `/kg-knowledge-index` | skill | Index format and generation |
| `/kg-knowledge-insights` | skill | Patterns and hotspots across the knowledge base |
| `/kg-knowledge-prune` | skill | Flag stale docs |
| `/kg-playwright-test` | skill | Write, run, and diagnose Playwright tests |

The `kg-` prefix keeps the names clear of Kiro's own slash commands and of other powers.

## What changed in conversion

| Claude Code | Kiro |
|---|---|
| `Agent(subagent_type: ...)` | Delegation to a named Kiro sub-agent, with an inline fallback |
| `run_in_background: true` | Parallel sub-agents (background with Kiro workflows enabled) |
| `AskUserQuestion` | Ask in chat |
| `TodoWrite` | Kiro's `todo` tool, or a checklist in chat |
| `$ARGUMENTS` | "the input": the text after the slash command |
| `${CLAUDE_PLUGIN_ROOT}/rules/` | `.kiro/steering/kg-*.md` |
| `CLAUDE.md` | `AGENTS.md` and your own `.kiro/steering/` files |
| `model: haiku` on learnings-researcher | Not set; add a `model:` line to `.kiro/agents/kg-learnings-researcher.md` to pin a cheaper model |

The `docs/knowledge/` layout is unchanged, so a project can use the Claude Code plugin and this
power side by side against the same knowledge base.
