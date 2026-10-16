#!/usr/bin/env python3
"""Generate the Kiro power from the Claude Code plugin.

The Claude Code plugin in plugins/kg is the source of truth. This script converts it into a Kiro
power (Agent Plugins format) at powers/knowledge-garden. Re-run it after changing the plugin:

    python3 scripts/build-kiro-power.py           # build
    python3 scripts/build-kiro-power.py --check   # build into a temp dir and fail if the
                                                  # committed power is out of date (for CI)

How each Claude Code component maps to Kiro:

    skills/<name>/      -> skills/kg-<name>/
    commands/<name>.md  -> skills/kg-<name>/SKILL.md   (Kiro has no commands; skills are slash-invocable)
    rules/<stack>.md    -> skills/kg-setup/references/steering/kg-<stack>.md
                           (/kg-setup copies these into the project's .kiro/steering/)
    agents/<name>.md    -> skills/kg-setup/references/agents/kg-<name>.md
                           (/kg-setup copies these into the project's .kiro/agents/)
    scripts/kiro-install.sh -> skills/kg-setup/scripts/install.sh
                           (/kg-setup runs it to copy skills, agents and steering into .kiro/)

A power can only ship skills and MCP config, and Kiro only makes slash commands from skills in a
workspace's .kiro/skills/. So /kg-setup installs everything into the project from the power.

Every targeted patch asserts that the text it replaces still exists. If the source plugin is
edited so a patch no longer matches, the build fails rather than shipping a half-converted file:
the same "fail loudly, never silently do less" rule scripts/validate.py follows.
"""

from __future__ import annotations

import base64
import filecmp
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "plugins" / "kg"
OUT_DEFAULT = ROOT / "powers" / "knowledge-garden"
PREFIX = "kg-"

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


# --------------------------------------------------------------------------- frontmatter


def split(text: str) -> tuple[str, str]:
    """Return (frontmatter, body). Frontmatter excludes the --- fences."""
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def fm_value(fm: str, key: str) -> str | None:
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


def yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)  # JSON strings are valid YAML scalars


# --------------------------------------------------------------------------- generic transforms


def names(src: Path) -> tuple[list[str], list[str]]:
    skills = sorted(d.name for d in (src / "skills").iterdir() if d.is_dir())
    commands = sorted(f.stem for f in (src / "commands").glob("*.md"))
    return skills, commands


def generic(text: str, component_names: list[str]) -> str:
    alt = "|".join(sorted(component_names, key=len, reverse=True))

    # /kg:plan -> /kg-plan ; kg:task-worker -> kg-task-worker
    text = re.sub(rf"/kg:({alt})\b", rf"/{PREFIX}\1", text)
    text = re.sub(rf"\bkg:({alt})\b", rf"{PREFIX}\1", text)

    # "the knowledge-docs skill" / "`learnings-researcher` agent" -> `kg-...`
    text = re.sub(
        rf"(?<![\w/-])`?(?<!{PREFIX})({alt})`?(?= (?:skill|agent|command)\b)",
        rf"`{PREFIX}\1`",
        text,
    )
    # Bare agent names anywhere else in prose.
    for agent in ("learnings-researcher", "task-worker"):
        text = re.sub(rf"(?<![\w-]){agent}\b", f"{PREFIX}{agent}", text)
    text = text.replace(f"`{PREFIX}{PREFIX}", f"`{PREFIX}").replace(f"{PREFIX}{PREFIX}", PREFIX)

    # $ARGUMENTS: Kiro only substitutes it in the CLI. In the IDE the text after the slash
    # command arrives as context, so describe it instead of relying on substitution.
    text = re.sub(
        r"## Arguments\n\n- `\$ARGUMENTS` \((required|optional)\):",
        r"## Input\n\nThe input is the text typed after the slash command, or the user's request "
        r"when Kiro loads this skill on its own.\n\n- **Input** (\1):",
        text,
    )
    text = text.replace("`$ARGUMENTS`", "the input")
    text = text.replace("$ARGUMENTS", "[input]")

    # Project instructions: Kiro reads AGENTS.md and .kiro/steering/, not CLAUDE.md.
    text = text.replace("`CLAUDE.md` / `AGENTS.md`", "`AGENTS.md` / its own `.kiro/steering/` files")
    text = text.replace(
        "the project's own `CLAUDE.md`",
        "the project's own steering (`AGENTS.md` or its own `.kiro/steering/` files)",
    )
    text = text.replace(
        "the project's `CLAUDE.md`",
        "the project's own steering (`AGENTS.md` or its own `.kiro/steering/` files)",
    )
    text = text.replace("`CLAUDE.md`", "`AGENTS.md`").replace("CLAUDE.md", "AGENTS.md")

    # Claude Code tool names -> plain instructions Kiro's agent can follow.
    text = text.replace("Use AskUserQuestion to get", "Ask the user for")
    text = text.replace(
        "Use AskUserQuestion if", "Ask the user (offer the choices as a short numbered list) if"
    )
    text = text.replace("Do not use AskUserQuestion.", "Do not stop to ask.")
    text = text.replace("Use WebSearch only", "Search the web only")
    text = text.replace("multiple Grep+Read tool calls", "many separate search and read steps")
    text = text.replace("multiple Grep+Read calls", "many separate search and read steps")
    text = text.replace(
        "Prefer `Edit` over `Write` for existing files.",
        "Edit existing files in place rather than rewriting them.",
    )

    # Claude Code Grep/Glob parameters -> plain hints Kiro's grep/glob tools can follow.
    text = re.sub(r"^([ \t]*(?:Grep|Glob): .*)$", lambda m: tool_params(m.group(1)), text, flags=re.M)
    return text


TOOL_PARAM_HINTS = {
    "-i=true": "case-insensitive",
    "output_mode=files_with_matches": "list matching files",
    "output_mode=content": "show matching lines",
    "head_limit=1": "first match only",
    "-i=false": None,  # case-sensitive is the default
    "-n=true": None,  # line numbers come with matching lines
}


def tool_params(line: str) -> str:
    hints = []
    for param, hint in TOOL_PARAM_HINTS.items():
        if f" {param}" in line:
            line = line.replace(f" {param}", "")
            if hint:
                hints.append(hint)
    return f"{line} ({', '.join(hints)})" if hints else line


def patch(text: str, old: str, new: str, where: str) -> str:
    if old not in text:
        fail(f"{where}: patch target not found (source changed?): {old[:70]!r}")
        return text
    return text.replace(old, new)


# --------------------------------------------------------------------------- shared snippets

RULES_STEERING = (
    "the kg coding rules installed by `/kg-setup` as steering: `.kiro/steering/kg-laravel.md`, "
    "`.kiro/steering/kg-nextjs.md`, or both, matching the stack in `kg.local.md` (or the legacy "
    "`knowledge-garden.local.md`). Skip for a `generic` stack. If the stack has rules but the "
    "steering file is missing, say so and suggest re-running `/kg-setup`."
)


def researcher_dispatch(prompt: str, indent: str = "") -> str:
    lines = [
        "Delegate to the `kg-learnings-researcher` sub-agent (installed by `/kg-setup`) with this "
        "prompt:",
        "",
        f"> {prompt}",
        "",
        "If that agent is not available, do the lookup yourself: read `docs/knowledge/index.md`, "
        "match the task's modules, components and keywords against its Critical Patterns, Modules, "
        "Solutions and Answers tables, read the matching module docs and at most 3 strongly "
        "matching solution files, and distill the learnings, gotchas and module file maps.",
    ]
    return "\n".join(indent + line if line else "" for line in lines)


AGENT_BLOCK = re.compile(
    r"^([ \t]*)```\n[ \t]*Agent\(\n\s*subagent_type: \"kg-learnings-researcher\",\n.*?"
    r"prompt: \"(.*?)\"\n\s*\)\n[ \t]*```",
    re.S | re.M,
)


def replace_researcher_blocks(text: str, where: str) -> str:
    new, n = AGENT_BLOCK.subn(lambda m: researcher_dispatch(m.group(2), m.group(1)), text)
    if n == 0:
        fail(f"{where}: expected a learnings-researcher dispatch block")
    return new


# --------------------------------------------------------------------------- per-file patches


def patch_work(t: str) -> str:
    w = "commands/work.md"
    t = replace_researcher_blocks(t, w)
    t = patch(
        t,
        "5. **Create task list.** Use TodoWrite to track progress:",
        "5. **Create task list.** Track progress in a todo list (Kiro's `todo` tool where available, "
        "otherwise a checklist in chat):",
        w,
    )
    t = patch(
        t,
        "0. **Load the coding rules once**, before the first task: read `${CLAUDE_PLUGIN_ROOT}/rules/` for the\n"
        "   stack in `kg.local.md` — or `knowledge-garden.local.md` for projects set up before 0.4.0 —\n"
        "   loading `laravel.md`, `nextjs.md`, or both. Skip for a `generic` stack. They stay in context for\n"
        "   every task in the run.",
        f"0. **Load the coding rules once**, before the first task: read {RULES_STEERING} They stay in "
        "context for every task in the run.",
        w,
    )
    t = patch(
        t,
        "   Workers load the coding rules themselves from `${CLAUDE_PLUGIN_ROOT}/rules/` — do not paste the\n"
        "   ruleset into the prompt.",
        "   Workers load the coding rules themselves from `.kiro/steering/` — do not paste the\n"
        "   ruleset into the prompt.",
        w,
    )
    t = patch(
        t,
        "2. **Dispatch kg-task-worker agents.** Launch all tasks in the wave simultaneously using "
        "`Agent(run_in_background: true)` -- all in a single message for true parallelism:",
        "2. **Dispatch task-worker sub-agents.** Delegate every task in the wave to its own "
        "`kg-task-worker` sub-agent at the same time, so Kiro runs them in parallel:",
        w,
    )
    t, n = re.subn(
        r"   ```\n   For each task in the current wave, dispatch a `kg-task-worker` agent:\n\n"
        r"   Agent\(\n     subagent_type: \"kg-task-worker\",\n     description: \"Execute task: \[brief\]\",\n"
        r"     prompt: \"\"\"\n(.*?)     \"\"\",\n     run_in_background: true\n   \)\n   ```\n",
        lambda m: "   Give each worker this prompt, filled in for its task:\n\n   ```\n"
        + re.sub(r"^    ", "", m.group(1), flags=re.M)
        + "   ```\n",
        t,
        flags=re.S,
    )
    if n != 1 or "subagent_type: \"kg-task-worker\"" in t:
        fail(f"{w}: task-worker dispatch block not converted")
    t = patch(
        t,
        "   If a `kg-task-worker` agent is defined, use it. Otherwise fall back to `general-purpose`.",
        "   If the `kg-task-worker` agent is not installed, delegate to Kiro's default sub-agent instead.",
        w,
    )
    t = patch(
        t,
        "3. **Collect results.** Wait for all background agents to complete.",
        "3. **Collect results.** Wait for every sub-agent in the wave to finish.",
        w,
    )
    t = re.sub(
        r"If triggered, run in background so it doesn't block the user:\n```\nAgent\(\n.*?\n\)\n```",
        "If triggered, delegate this to a sub-agent so it doesn't block the user (with Kiro "
        "workflows enabled it runs in the background):\n\n"
        "> Follow `.kiro/skills/kg-module-docs/SKILL.md` for these modules only: [affected module "
        "names]. Then follow `.kiro/skills/kg-knowledge-index/SKILL.md` to rebuild the index.\n\n"
        "A sub-agent does not load skills on its own, so the prompt points it at the skill files "
        "`/kg-setup` installed. If sub-agents are unavailable, or those files are missing, run the "
        "`kg-module-docs` and `kg-knowledge-index` skills yourself after the Step 4 report.",
        t,
        flags=re.S,
    )
    if "Agent(" in t:
        fail(f"{w}: an Agent( block was not converted")
    return t


def patch_task_worker(t: str) -> str:
    w = "agents/task-worker.md"
    t = patch(
        t,
        "1. **Load the coding rules.** Read the ruleset for the project's stack before writing anything:\n"
        "   `${CLAUDE_PLUGIN_ROOT}/rules/laravel.md`, `${CLAUDE_PLUGIN_ROOT}/rules/nextjs.md`, or both for a\n"
        "   full-stack project. The stack is recorded in `kg.local.md` (or the legacy `knowledge-garden.local.md`). Skip only if the stack\n"
        "   is `generic`, which has no ruleset.",
        f"1. **Load the coding rules.** Before writing anything, read {RULES_STEERING}",
        w,
    )
    t = patch(t, "- **No TodoWrite.** The orchestrator", "- **No todo list.** The orchestrator", w)
    return t


def patch_quickfix(t: str) -> str:
    w = "skills/quickfix/SKILL.md"
    t = replace_researcher_blocks(t, w)
    t = patch(t, "(use /debug or /kg-plan instead)", "(use /kg-plan instead)", w)
    t = patch(
        t,
        "Before writing, load the coding rules for the project's stack from `${CLAUDE_PLUGIN_ROOT}/rules/`\n"
        "(`laravel.md`, `nextjs.md`, or both). The stack is recorded in `kg.local.md`, or in\n"
        "`knowledge-garden.local.md` for projects set up before 0.4.0. Skip for a `generic` stack.",
        f"Before writing, read {RULES_STEERING}",
        w,
    )
    return t


def patch_review(t: str) -> str:
    w = "commands/review.md"
    t = replace_researcher_blocks(t, w)
    t = patch(
        t,
        "6. **Load the coding rules.** Read `${CLAUDE_PLUGIN_ROOT}/rules/` for the stack in\n"
        "   `kg.local.md` — or `knowledge-garden.local.md` for projects set up before 0.4.0 — loading\n"
        "   `laravel.md`, `nextjs.md`, or both. Skip for a `generic` stack.",
        f"6. **Load the coding rules.** Read {RULES_STEERING}",
        w,
    )
    return t


def patch_setup(t: str) -> str:
    w = "skills/setup/SKILL.md"
    t = patch(
        t,
        "- **Rules**: [rules/laravel.md / rules/nextjs.md / both / none for generic]",
        "- **Rules**: [.kiro/steering/kg-laravel.md / .kiro/steering/kg-nextjs.md / both / none for generic]",
        w,
    )
    install_step = """<step number="6" required="true" depends_on="5">
### Step 6: Install Skills, Sub-agents and Steering into `.kiro/`

Kiro makes slash commands only from skills in the workspace's `.kiro/skills/` (or the user's
`~/.kiro/skills/`), and a power can only ship skills. So this step copies the rest of Knowledge
Garden into the project. From the project root, run this skill's install script with the stack
from Step 5, where `<kg-setup folder>` is the folder containing this SKILL.md:

```bash
sh <kg-setup folder>/scripts/install.sh <laravel|nextjs|fullstack|generic>
```

It installs:

| What | Where |
|------|-------|
| Every other `kg-*` skill | `.kiro/skills/kg-*/`, which become `/kg-plan`, `/kg-work`, `/kg-review` ... |
| Sub-agents | `.kiro/agents/kg-learnings-researcher.md`, `.kiro/agents/kg-task-worker.md` |
| Coding rules (not for `generic`) | `.kiro/steering/kg-laravel.md`, `.kiro/steering/kg-nextjs.md`, or both |

The steering files use `inclusion: fileMatch`, so Kiro applies them whenever it works on `.php`
or `.ts`/`.tsx` files.

The script records what it installed in `.kiro/kg-manifest.txt`. On a re-run it replaces only
files that still match what it installed last time; files the project edited are kept and
listed. Show the user the script's summary, including any kept files.

`kg-setup` itself is not copied: it stays in the power, so re-running setup after the power is
updated always installs the new version.

**If `sh` is not available** (native Windows without Git Bash or WSL), copy the same files with
your file tools instead, contents unchanged: every `kg-*` folder beside the `kg-setup` folder
except `kg-setup` → `.kiro/skills/`, `references/agents/*.md` → `.kiro/agents/`, and the
stack's `references/steering/kg-*.md` → `.kiro/steering/`. Do not overwrite a file that already
exists; tell the user which were skipped. Do not write a manifest.

Workspace agents load only when the workspace is trusted. If Kiro asks, the user needs to trust
the workspace for `/kg-work`, `/kg-plan`, `/kg-review`, `/kg-brainstorm` and `/kg-quickfix` to
delegate to these agents. Without them those skills still work, doing the lookups inline.
</step>

<step number="7" required="true" depends_on="6">
### Step 7: Confirm Setup"""
    t = patch(t, '<step number="6" required="true" depends_on="5">\n### Step 6: Confirm Setup', install_step, w)
    t = patch(
        t,
        "Coding rules in effect: [rules/laravel.md / rules/nextjs.md / both / none]\n"
        "  Agents load these when writing code. Your AGENTS.md always outranks them.",
        "Coding rules in effect: [.kiro/steering/kg-laravel.md / .kiro/steering/kg-nextjs.md / both / none]\n"
        "  Kiro applies these when editing matching files. Your AGENTS.md and your own steering always outrank them.\n"
        "Skills: .kiro/skills/kg-* (slash commands /kg-plan, /kg-work, /kg-review ...)\n"
        "Sub-agents: .kiro/agents/kg-learnings-researcher.md, .kiro/agents/kg-task-worker.md\n"
        "Commit .kiro/ so your team gets the same commands. If the /kg- commands do not show up yet,\n"
        "reload the Kiro window or start a new chat.",
        w,
    )
    return t


def patch_audit(t: str) -> str:
    w = "skills/audit/SKILL.md"
    precedence = "the *Precedence and conflicts* section at the end of each kg steering file"
    t = patch(t, "stack ruleset in `rules/`,", "stack ruleset installed in `.kiro/steering/`,", w)
    t = patch(
        t,
        "4. The stack's rulesets from `${CLAUDE_PLUGIN_ROOT}/rules/`: `laravel.md`, `nextjs.md`, or both.",
        f"4. The stack's rulesets: {RULES_STEERING}",
        w,
    )
    t = patch(t, "   Skip them for a `generic` stack.\n", "", w)  # RULES_STEERING already says so
    t = patch(
        t, "each numbered section of `laravel.md` / `nextjs.md`,",
        "each numbered section of `kg-laravel.md` / `kg-nextjs.md`,", w,
    )
    t = patch(t, "following\n`rules/README.md`, and", f"following\n{precedence}, and", w)
    t = patch(t, "`rules/laravel.md §7`", "`kg-laravel.md §7`", w)
    t = patch(t, "Precedence follows `rules/README.md`:", f"Precedence follows {precedence}:", w)
    return t


PATCHES = {
    "skills/audit/SKILL.md": patch_audit,
    "commands/work.md": patch_work,
    "skills/quickfix/SKILL.md": patch_quickfix,
    "commands/review.md": patch_review,
    "commands/plan.md": lambda t: replace_researcher_blocks(t, "commands/plan.md"),
    "commands/brainstorm.md": lambda t: replace_researcher_blocks(t, "commands/brainstorm.md"),
    "skills/setup/SKILL.md": patch_setup,
    "agents/task-worker.md": patch_task_worker,
}

EXTRA_DESCRIPTION = {
    # Claude Code's disable-model-invocation has no Kiro equivalent; say it in the description,
    # which is what Kiro matches against.
    "knowledge-docs": " Do not load this on your own; it runs only when /kg-compound invokes it.",
}

DESCRIPTION_PREFIX = {
    # Before setup runs, no /kg- slash command exists in the workspace: the user asks in plain
    # words and Kiro has to pick this skill from its description.
    "setup": "Run this first to set up Knowledge Garden: installs the /kg- skills, sub-agents and "
    "steering into .kiro/. Also re-run after updating the power. ",
}


# --------------------------------------------------------------------------- power metadata

DISPLAY_NAME = "Knowledge Garden"
AUTHOR = "oaa-dev"
POWER_REPO = "https://github.com/oaa-dev/kiro-skill"  # the power is published from this repo
DESCRIPTION = (
    "Project knowledge management for Laravel, Next.js, and generic stacks: module docs, "
    "captured solutions, knowledge-backed brainstorm/plan/work/review, quickfix, Q&A, "
    f"Playwright testing, and stack coding rules. Developed by {AUTHOR}."
)
KEYWORDS = [
    "kg", "knowledge garden", "kg setup", "set up knowledge garden",
    "knowledge base", "learnings", "institutional knowledge",
    "module docs", "compound", "quickfix", "brainstorm", "implementation plan",
    "code review", "playwright", "laravel", "nextjs",
]
ICON = ROOT / "scripts" / "kiro-power-icon.png"  # drawn by scripts/make-kiro-icon.py


def write_power_md(out: Path) -> None:
    """POWER.md beside plugin.json, for Kiro's Powers panel only.

    Kiro loads the power from plugin.json, whose schema allows neither a display name nor an
    icon, and whose name must be lowercase kebab-case. The Powers panel's detail view reads
    displayName, description, author and iconUrl from POWER.md frontmatter instead, and only
    accepts data: URIs for images, so the icon is embedded. icon.png is shipped as well for
    clients that look for a bundled file.
    """
    if not ICON.exists():
        fail("scripts/kiro-power-icon.png missing; run scripts/make-kiro-icon.py")
        return
    shutil.copy(ICON, out / "icon.png")
    icon_uri = "data:image/png;base64," + base64.b64encode(ICON.read_bytes()).decode()
    fm = "\n".join([
        "---",
        f"name: {yaml_str('knowledge-garden')}",
        f"displayName: {yaml_str(DISPLAY_NAME)}",
        f"description: {yaml_str(DESCRIPTION)}",
        f"keywords: {json.dumps(KEYWORDS)}",
        f"author: {yaml_str(AUTHOR)}",
        f"iconUrl: {yaml_str(icon_uri)}",
        "---",
    ])
    body = f"""
# {DISPLAY_NAME}

Project knowledge management for Laravel, Next.js, and generic stacks. Developed by {AUTHOR}.

## Getting started

In a new project, start with the `kg-setup` skill (the user may ask to "set up Knowledge
Garden"). It detects the stack, creates `docs/knowledge/`, and installs the other skills,
sub-agents and coding rules into `.kiro/`, after which every skill is a slash command:
`/kg-plan`, `/kg-work`, `/kg-review`, `/kg-quickfix`, `/kg-ask`, `/kg-compound` and more.
"""
    (out / "POWER.md").write_text(fm + "\n" + body)


def skill_file(name: str, description: str, body: str) -> str:
    # A skill that refers to "the input" without a section defining it gets a one-line definition
    # under its title, so the agent knows where the input comes from in the IDE.
    if re.search(r"\bthe input\b|\[input\]", body) and "## Input" not in body:
        body, n = re.subn(
            r"^(# .+\n)",
            rf"\1\n> **Input:** the text typed after `/{name}`, or the user's request when Kiro "
            r"loads this skill on its own.\n",
            body,
            count=1,
            flags=re.M,
        )
        if n != 1:
            fail(f"{name}: uses 'the input' but has no title to attach its definition to")
    return f"---\nname: {name}\ndescription: {yaml_str(description)}\nlicense: MIT\n---\n{body}"


def build(out: Path) -> None:
    skills, commands = names(SRC)
    clash = set(skills) & set(commands)
    if clash:
        fail(f"command and skill share a name: {sorted(clash)}")
    all_names = skills + commands + ["learnings-researcher", "task-worker"]

    if out.exists():
        shutil.rmtree(out)
    (out / "skills").mkdir(parents=True)

    def convert(rel: str, text: str) -> str:
        if rel in PATCHES:
            # Patches are written against prefixed names, so apply the generic pass first.
            return PATCHES[rel](generic(text, all_names))
        return generic(text, all_names)

    # Skills: copy the whole folder (references, assets, scripts), convert every .md inside.
    for s in skills:
        src_dir, dst_dir = SRC / "skills" / s, out / "skills" / f"{PREFIX}{s}"
        shutil.copytree(src_dir, dst_dir)
        for md in dst_dir.rglob("*.md"):
            rel = md.relative_to(out / "skills" / f"{PREFIX}{s}")
            text = convert(f"skills/{s}/{rel}", md.read_text())
            if rel.name == "SKILL.md":
                fm, body = split(text)
                desc = (
                    DESCRIPTION_PREFIX.get(s, "")
                    + (fm_value(fm, "description") or "")
                    + EXTRA_DESCRIPTION.get(s, "")
                )
                text = skill_file(f"{PREFIX}{s}", desc, body)
            md.write_text(text)

    # Commands become skills.
    for c in commands:
        fm, body = split((SRC / "commands" / f"{c}.md").read_text())
        desc = fm_value(fm, "description") or c
        body = convert(f"commands/{c}.md", body)
        dst = out / "skills" / f"{PREFIX}{c}"
        dst.mkdir()
        (dst / "SKILL.md").write_text(skill_file(f"{PREFIX}{c}", desc, body))

    # Rules become fileMatch steering, shipped inside the setup skill.
    readme = generic((SRC / "rules" / "README.md").read_text(), all_names)
    tail = re.search(r"(## Precedence.*)", readme, re.S)
    if not tail:
        fail("rules/README.md: '## Precedence' section not found")
    precedence = tail.group(1).replace("## ", "### ") if tail else ""
    patterns = {"laravel": '["**/*.php"]', "nextjs": '["**/*.ts", "**/*.tsx"]'}
    steer_dir = out / "skills" / f"{PREFIX}setup" / "references" / "steering"
    steer_dir.mkdir(parents=True)
    for rule in sorted(p.stem for p in (SRC / "rules").glob("*.md") if p.stem != "README"):
        if rule not in patterns:
            fail(f"rules/{rule}.md: no fileMatchPattern defined for this stack")
            continue
        body = generic((SRC / "rules" / f"{rule}.md").read_text(), all_names)
        body, n = re.subn(
            r"See\s+\[README\.md\]\(\./README\.md\) for precedence\s+—",
            "See *Precedence* at the end of this file —",
            body,
        )
        if n != 1:
            fail(f"rules/{rule}.md: precedence link not found")
        steering = (
            f"---\ninclusion: fileMatch\nfileMatchPattern: {patterns[rule]}\n---\n"
            f"{body.rstrip()}\n\n## Precedence and conflicts (Knowledge Garden)\n\n{precedence.strip()}\n"
        )
        (steer_dir / f"{PREFIX}{rule}.md").write_text(steering)

    # Agents become Kiro custom agents, shipped inside the setup skill.
    agent_tools = {
        "learnings-researcher": ["read", "glob", "grep"],
        "task-worker": ["read", "write", "shell", "glob", "grep"],
    }
    agent_dir = out / "skills" / f"{PREFIX}setup" / "references" / "agents"
    agent_dir.mkdir(parents=True)
    for f in sorted((SRC / "agents").glob("*.md")):
        fm, body = split(f.read_text())
        body = re.sub(r"<examples>.*?</examples>\s*", "", body, flags=re.S)
        body = convert(f"agents/{f.name}", body)
        name = f"{PREFIX}{f.stem}"
        desc = generic(fm_value(fm, "description") or "", all_names)
        lines = [
            "---",
            f"name: {name}",
            f"description: {yaml_str(desc)}",
            f"tools: {json.dumps(agent_tools.get(f.stem, ['read', 'glob', 'grep']))}",
        ]
        if f.stem == "task-worker":
            lines.append('resources: ["file://.kiro/steering/**/*.md", "file://AGENTS.md"]')
        lines.append("---")
        (agent_dir / f"{name}.md").write_text("\n".join(lines) + "\n" + body.lstrip("\n"))

    # The install script /kg-setup runs to copy skills, agents and steering into .kiro/.
    install_src = ROOT / "scripts" / "kiro-install.sh"
    script_dir = out / "skills" / f"{PREFIX}setup" / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    script = install_src.read_text()
    if "@VERSION@" not in script:
        fail("scripts/kiro-install.sh: @VERSION@ placeholder not found")
    version = json.loads((SRC / ".claude-plugin" / "plugin.json").read_text())["version"]
    (script_dir / "install.sh").write_text(script.replace("@VERSION@", version))

    # Manifest.
    src_manifest = json.loads((SRC / ".claude-plugin" / "plugin.json").read_text())
    manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "knowledge-garden",
        "version": src_manifest["version"],
        "description": DESCRIPTION,
        "author": {"name": AUTHOR, "url": f"https://github.com/{AUTHOR}"},
        "keywords": KEYWORDS,
        "homepage": POWER_REPO,
        "repository": POWER_REPO,
        "license": src_manifest.get("license", "MIT"),
    }
    (out / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_power_md(out)
    shutil.copy(SRC / "LICENSE", out / "LICENSE")
    readme_src = ROOT / "scripts" / "kiro-power-README.md"
    if readme_src.exists():
        shutil.copy(readme_src, out / "README.md")
    else:
        fail("scripts/kiro-power-README.md missing")

    verify(out)


# --------------------------------------------------------------------------- verification

LEFTOVERS = {
    "Agent(": "Claude Code Agent() call",
    "subagent_type": "Claude Code subagent_type",
    "AskUserQuestion": "Claude Code AskUserQuestion tool",
    "TodoWrite": "Claude Code TodoWrite tool",
    "EnterPlanMode": "Claude Code plan mode",
    "CLAUDE_PLUGIN_ROOT": "Claude Code plugin root variable",
    "$ARGUMENTS": "argument placeholder",
    "/kg:": "Claude Code command namespace",
    "CLAUDE.md": "Claude Code project file",
    "allowed-tools": "Claude Code frontmatter",
    "run_in_background": "Claude Code background agent flag",
    "output_mode=": "Claude Code Grep parameter",
    "head_limit=": "Claude Code Grep/Glob parameter",
    "Grep+Read": "Claude Code tool names",
}


def verify(out: Path) -> None:
    skill_names = set()
    for d in sorted((out / "skills").iterdir()):
        sk = d / "SKILL.md"
        if not sk.exists():
            fail(f"{d.name}: missing SKILL.md")
            continue
        fm, _ = split(sk.read_text())
        name, desc = fm_value(fm, "name"), fm_value(fm, "description") or ""
        if name != d.name:
            fail(f"{d.name}: frontmatter name {name!r} must match folder name")
        if not re.fullmatch(r"[a-z0-9-]{1,64}", d.name):
            fail(f"{d.name}: Kiro skill names are lowercase letters, numbers and hyphens, max 64")
        if not desc or len(desc) > 1024:
            fail(f"{d.name}: description must be 1-1024 characters")
        skill_names.add(d.name)

    script = out / "skills" / f"{PREFIX}setup" / "scripts" / "install.sh"
    if not script.exists():
        fail("kg-setup: scripts/install.sh missing")
    elif "@VERSION@" in script.read_text():
        fail("kg-setup: scripts/install.sh still has the @VERSION@ placeholder")

    for path in sorted(out.rglob("*.md")):
        rel = path.relative_to(out)
        if rel.name == "README.md" and rel.parent == Path("."):
            continue  # the power README explains the mapping and names Claude Code terms on purpose
        text = path.read_text()
        for token, what in LEFTOVERS.items():
            if token in text:
                fail(f"{rel}: leftover {what} ({token!r})")
        for m in re.finditer(r"(?<![\w/.-])/kg-([a-z-]+)", text):
            if f"kg-{m.group(1)}" not in skill_names:
                fail(f"{rel}: /kg-{m.group(1)} does not resolve to a skill")
        for m in re.finditer(r"\]\((?!https?://|#)([^)\s]+)\)", text):
            target = m.group(1).split("#")[0]
            if re.search(r"\{|\bcategory/|\bfilename\b|<name>", target):
                continue
            if target and not (path.parent / target).exists():
                fail(f"{rel}: broken link -> {target}")


# --------------------------------------------------------------------------- main


def main() -> int:
    check = "--check" in sys.argv
    if check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "knowledge-garden"
            build(fresh)
            if not errors:
                cmp = filecmp.dircmp(fresh, OUT_DEFAULT)
                stale = cmp.left_only or cmp.right_only or cmp.diff_files or _deep_diff(cmp)
                if stale:
                    fail("powers/knowledge-garden is out of date; run scripts/build-kiro-power.py")
    else:
        build(OUT_DEFAULT)

    for e in errors:
        print(f"ERROR  {e}")
    if errors:
        return 1
    if not check:
        n = len(list((OUT_DEFAULT / "skills").iterdir()))
        print(f"Built {OUT_DEFAULT.relative_to(ROOT)} ({n} skills)")
    else:
        print("Kiro power is up to date")
    return 0


def _deep_diff(cmp: filecmp.dircmp) -> bool:
    return any(
        sub.left_only or sub.right_only or sub.diff_files or _deep_diff(sub)
        for sub in cmp.subdirs.values()
    )


if __name__ == "__main__":
    sys.exit(main())
