# Personal Plugins

A personal Claude Code plugin marketplace by [oaa-dev](https://github.com/oaa-dev).

## Available Plugins

| Plugin | Description | Install |
|--------|-------------|---------|
| <img src="plugins/kg/icon.png" alt="" width="20"> Knowledge Garden (`kg`) | Project knowledge management for Laravel, Next.js, and generic stacks. 2 agents, 7 commands, 10 skills, 2 coding rulesets. | `/plugin install kg` |

## Claude Code Install

```bash
/plugin marketplace add https://github.com/oaa-dev/claude-skill
/plugin install kg
```

Or, for local development against this working copy:

```bash
/plugin marketplace add /path/to/claude-skill
/plugin install kg
```

## Validation

```bash
python3 scripts/validate.py           # full report
python3 scripts/validate.py --quiet   # failures only, for CI
```

Exits non-zero on any error. Every check exists because that bug shipped at least once — these
plugins fail silently by nature, since an unexecutable instruction makes an agent quietly do less
rather than raise anything. Run it before committing.

Covers: frontmatter parses and names match filenames; `allowed-tools` entries are real, current
tool names; tools used in prose are declared; no command/skill name collisions; every
`/kg:<name>` and `subagent_type` resolves; internal links resolve; the knowledge-index template
contract holds; manifest versions agree; component counts match what is on disk.

## Token monitoring

```bash
python3 scripts/token-report.py                  # all projects -> token-usage.txt
python3 scripts/token-report.py --days 7         # last 7 days
python3 scripts/token-report.py --by session     # session totals only
python3 scripts/token-report.py --project pos    # one project
```

Reads the per-request token counts Claude Code already writes to
`~/.claude/projects/<slug>/*.jsonl`. Nothing needs enabling first and it works retroactively on
sessions already recorded. Reports per turn (one prompt plus every request it fans out into),
per session, and per project, with subagent usage counted separately — subagent transcripts live
in `<session-id>/subagents/` and are easy to miss.

Counts only, no cost: rates differ per model and change. Use `/cost` for the billed figure.

## Kiro Install

<img src="powers/knowledge-garden/icon.png" alt="Knowledge Garden" width="96">

`powers/knowledge-garden` is the same plugin packaged as a Kiro power, **Knowledge Garden**. In Kiro: **Powers** panel →
**Add Custom Power** → **Import power from GitHub** (`https://github.com/oaa-dev/kiro-skill`) or **Import power from a folder**
(`powers/knowledge-garden`). Then, in your project, ask Kiro chat to *"Set up Knowledge Garden for
this project"*. Setup copies the skills, sub-agents and steering into `.kiro/`, after which every
skill is a slash command named `/kg-<name>` (reload the window if they do not show up).

The power is generated from `plugins/kg` — edit the plugin, then rebuild:

```bash
python3 scripts/build-kiro-power.py           # regenerate powers/knowledge-garden
python3 scripts/build-kiro-power.py --check   # CI: fail if the power is out of date
```

The build fails if a conversion patch no longer matches the plugin source, or if any Claude
Code-only construct (`Agent(`, `AskUserQuestion`, `$ARGUMENTS`, `/kg:` ...) survives into the power.
See `powers/knowledge-garden/README.md` for the full mapping.

## Cursor Install

```text
/add-plugin kg
```
