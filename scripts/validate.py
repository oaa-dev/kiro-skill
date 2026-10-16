#!/usr/bin/env python3
"""Structural validation for the plugins in this marketplace.

Every check here exists because the corresponding bug shipped at least once. This plugin's
failure mode is silence -- an unexecutable instruction makes an agent quietly do less rather
than raise anything -- so the job of this script is to turn that silence into a non-zero exit.

Usage:
    python3 scripts/validate.py           # validate every plugin in the marketplace
    python3 scripts/validate.py --quiet   # only print failures

Exits 1 if any ERROR is found. WARNINGs do not fail the run.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Tool names a component may declare in `allowed-tools`. Extend deliberately: an unknown name
# is an error precisely so that a typo like "Globso i" cannot silently disable a tool.
VALID_TOOLS = {
    "Agent", "AskUserQuestion", "Bash", "Edit", "Glob", "Grep", "NotebookEdit",
    "Read", "Skill", "TodoWrite", "WebFetch", "WebSearch", "Write",
    "EnterPlanMode", "ExitPlanMode", "TaskCreate", "TaskGet", "TaskList",
    "TaskOutput", "TaskStop", "TaskUpdate", "Monitor", "SendMessage", "ListAgents",
}

# Names that were valid once and are not any more. Flagged with the fix, because renaming a
# tool out from under a plugin breaks it without any error at runtime.
RETIRED_TOOLS = {"Task": "Agent"}

# Tools whose use in prose implies a declaration. The negation filter below removes
# prohibitions ("Do not use AskUserQuestion").
TOOL_USE_PATTERNS = {
    "Write": r"\bWrite\b",
    "Edit": r"\bEdit\b",
    "Read": r"\bRead\b",
    "Glob": r"\bGlob\b",
    "Grep": r"\bGrep\b",
    "Bash": r"```bash|`mkdir |`mv |`rm ",
    "AskUserQuestion": r"AskUserQuestion",
    "Agent": r"Agent\(",
    "TodoWrite": r"TodoWrite",
    "WebSearch": r"WebSearch",
    "WebFetch": r"WebFetch",
}

# Tools whose names are still tool names in lowercase ("grep for it" means the Grep tool).
# Read/Write/Edit/Bash are excluded deliberately: they are ordinary English and matching them
# case-insensitively floods the run with false positives.
CASE_INSENSITIVE_TOOLS = {"Glob", "Grep", "AskUserQuestion", "TodoWrite", "WebSearch", "WebFetch"}

NEGATIONS = ("do not use", "never use", "no todowrite", "do not create or update todos")

# Link targets that are illustrative rather than real paths.
PLACEHOLDER_LINK = re.compile(r"\{|\bcategory/|\bfilename\b|<name>")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


# --------------------------------------------------------------------------- frontmatter


def split_frontmatter(text: str) -> str | None:
    """Return the raw frontmatter block, or None if the file does not open with one."""
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    return parts[1] if len(parts) >= 3 else None


def parse_frontmatter(raw: str) -> dict:
    """Parse flat frontmatter. Uses PyYAML when present, else a minimal fallback.

    The fallback handles exactly the shapes these files use: `key: value` and `key:` followed
    by a `  - item` list. Keeping it dependency-free means CI needs no install step.
    """
    try:
        import yaml  # type: ignore

        return yaml.safe_load(raw) or {}
    except ImportError:
        pass

    data: dict = {}
    key = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"\s+-\s+(.*)$", line)
        if item and key:
            data.setdefault(key, []).append(item.group(1).strip().strip("\"'"))
            continue
        kv = re.match(r"([A-Za-z0-9_-]+):\s*(.*)$", line)
        if kv:
            key, value = kv.group(1), kv.group(2).strip()
            data[key] = value.strip("\"'") if value else []
    return data


_parsed: dict[Path, dict | None] = {}


def component_data(path: Path) -> dict | None:
    """Parse a component's frontmatter once, reporting a failure exactly once.

    Returns None when the file has no frontmatter or it does not parse. Every check must go
    through here: a raw parse in one check crashes the whole run on a malformed file, which
    turns a reportable error into a traceback.
    """
    if path in _parsed:
        return _parsed[path]
    result: dict | None = None
    if not path.exists():
        err(f"{path.relative_to(ROOT)}: missing")
    else:
        raw = split_frontmatter(path.read_text())
        if raw is None:
            err(f"{path.relative_to(ROOT)}: no frontmatter block")
        else:
            try:
                result = parse_frontmatter(raw)
            except Exception as exc:  # noqa: BLE001 - surface any parser failure verbatim
                first = str(exc).splitlines()[0]
                err(f"{path.relative_to(ROOT)}: frontmatter does not parse -- {first}")
    _parsed[path] = result
    return result


def components(plugin: Path) -> list[tuple[str, str, Path]]:
    """Yield (kind, name, path) for every command, skill, and agent in a plugin."""
    out = []
    for f in sorted((plugin / "commands").glob("*.md")):
        out.append(("command", f.stem, f))
    for d in sorted(p for p in (plugin / "skills").glob("*") if p.is_dir()):
        out.append(("skill", d.name, d / "SKILL.md"))
    for f in sorted((plugin / "agents").glob("*.md")):
        out.append(("agent", f.stem, f))
    return out


# --------------------------------------------------------------------------- checks


def check_frontmatter(plugin: Path) -> None:
    """Frontmatter parses, declares a name, and that name matches the file it lives in."""
    for kind, name, path in components(plugin):
        if kind == "skill" and not path.exists():
            err(f"{path.relative_to(ROOT)}: skill directory has no SKILL.md")
        data = component_data(path)
        if data is None:
            continue
        declared = data.get("name")
        if not declared:
            err(f"{path.relative_to(ROOT)}: frontmatter has no `name:`")
        elif declared != name:
            err(f"{path.relative_to(ROOT)}: name is '{declared}' but the file says '{name}'")
        if ":" in str(declared or ""):
            err(
                f"{path.relative_to(ROOT)}: name '{declared}' is namespaced by hand -- "
                f"use the bare name; the plugin prefix is applied automatically"
            )


def check_tools(plugin: Path) -> None:
    """Declared tools exist, are not retired, and cover what the instructions actually use."""
    for kind, name, path in components(plugin):
        data = component_data(path)
        if data is None:
            continue
        text = path.read_text()
        declared = data.get("allowed-tools") or []
        if isinstance(declared, str):
            declared = [declared]
        rel = path.relative_to(ROOT)

        if not declared:
            warn(f"{rel}: declares no allowed-tools (inherits defaults)")

        for tool in declared:
            if tool in RETIRED_TOOLS:
                err(f"{rel}: '{tool}' is retired -- use '{RETIRED_TOOLS[tool]}'")
            elif tool not in VALID_TOOLS:
                err(f"{rel}: '{tool}' is not a known tool name (typo?)")

        if not declared:
            continue
        body = text.split("---\n", 2)[2]
        for tool, pattern in TOOL_USE_PATTERNS.items():
            if tool in declared:
                continue
            flags = re.IGNORECASE if tool in CASE_INSENSITIVE_TOOLS else 0
            for m in re.finditer(pattern, body, flags):
                line = body[body.rfind("\n", 0, m.start()) + 1 : body.find("\n", m.end())]
                if any(n in line.lower() for n in NEGATIONS):
                    continue
                err(f"{rel}: uses {tool} but does not declare it -- {line.strip()[:60]}")
                break


def check_collisions(plugin: Path) -> None:
    """A command and a skill sharing a name makes the skill unreachable."""
    cmds = {f.stem for f in (plugin / "commands").glob("*.md")}
    skills = {d.name for d in (plugin / "skills").glob("*") if d.is_dir()}
    for name in sorted(cmds & skills):
        err(
            f"{plugin.name}: '{name}' exists as both a command and a skill -- "
            f"the command shadows the skill and makes it unreachable"
        )


def check_references(plugin: Path, slug: str) -> None:
    """Every /slug:name invocation and every subagent_type points at something real."""
    valid = {n for _, n, _ in components(plugin)}
    for path in sorted(plugin.rglob("*.md")):
        if path.name == "CHANGELOG.md":
            continue  # historical entries legitimately name old commands
        rel = path.relative_to(ROOT)
        text = path.read_text()

        if f"/{slug}::" in text:
            err(f"{rel}: uses '::' -- plugin invocations take a single colon")

        for ref in set(re.findall(rf"/{slug}:([a-z][a-z0-9-]*)", text)):
            if ref not in valid:
                err(f"{rel}: /{slug}:{ref} does not exist")

        for ref in set(re.findall(r'subagent_type:\s*"([^"]+)"', text)):
            if ref == "general-purpose":
                continue
            if not ref.startswith(f"{slug}:"):
                err(f"{rel}: subagent_type '{ref}' is not namespaced as {slug}:<agent>")
            elif ref.split(":", 1)[1] not in valid:
                err(f"{rel}: subagent_type '{ref}' names no existing agent")


def check_links(plugin: Path) -> None:
    """Relative markdown links resolve, ignoring illustrative placeholder paths."""
    for path in sorted(plugin.rglob("*.md")):
        for target in re.findall(r"\]\((?!https?:)([^)]+)\)", path.read_text()):
            target = target.split("#")[0].strip()
            if not target or not target.endswith(".md") or PLACEHOLDER_LINK.search(target):
                continue
            if not (path.parent / target).exists():
                err(f"{path.relative_to(ROOT)}: broken link -> {target}")


def check_index_contract(plugin: Path) -> None:
    """Readers test for both index markers, so every emitted template must carry both.

    Omitting `<!-- Modules: 0 -->` makes the 'both markers' test unsatisfiable, and a fresh
    project then dispatches a research agent against an empty knowledge base on every run.

    Checked per fenced block, not per file: a file may hold several templates, and one of them
    being correct must not excuse another.
    """
    fence = re.compile(r"```[a-z]*\n(.*?)```", re.DOTALL)
    for path in sorted(plugin.rglob("*.md")):
        rel = path.relative_to(ROOT)
        for block in fence.findall(path.read_text()):
            if "# Knowledge Index" not in block:
                continue
            if "<!-- Solutions:" not in block:
                continue
            if "<!-- Modules:" not in block:
                err(
                    f"{rel}: emits an index template with no '<!-- Modules: N -->' marker -- "
                    f"readers test for both Solutions and Modules"
                )


def check_manifests(plugin: Path, market: dict) -> None:
    """Versions agree across all three manifests, and the source path resolves."""
    p = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text())
    entry = next((e for e in market["plugins"] if e["name"] == p["name"]), None)
    if entry is None:
        err(f"{plugin.name}: not listed in marketplace.json under name '{p['name']}'")
        return
    versions = {"plugin.json": p.get("version"), "marketplace.json": entry.get("version")}
    cursor = plugin / ".cursor-plugin" / "plugin.json"
    if cursor.exists():
        versions["cursor plugin.json"] = json.loads(cursor.read_text()).get("version")
    if len(set(versions.values())) > 1:
        err(f"{plugin.name}: versions disagree -- {versions}")
    if not (ROOT / entry["source"].lstrip("./")).is_dir():
        err(f"marketplace.json: source '{entry['source']}' does not resolve")


def check_counts(plugin: Path) -> None:
    """Component counts quoted in prose must match what is on disk.

    These counts live in five files. They have drifted apart before, in all five at once.
    """
    actual = {
        "agent": len(list((plugin / "agents").glob("*.md"))),
        "command": len(list((plugin / "commands").glob("*.md"))),
        "skill": len([d for d in (plugin / "skills").glob("*") if d.is_dir()]),
    }
    targets = list(plugin.rglob("*.md")) + list(plugin.rglob("*.json"))
    targets += [ROOT / "README.md", ROOT / ".claude-plugin" / "marketplace.json"]
    for path in targets:
        if not path.exists() or path.name == "CHANGELOG.md":
            continue
        text = path.read_text()
        for kind, n in actual.items():
            # Prose form ("7 commands") and table form ("| Commands | 7 |") are both used.
            quoted = re.findall(rf"(\d+)\s+{kind}s\b", text, re.IGNORECASE)
            quoted += re.findall(rf"^\|\s*{kind}s\s*\|\s*(\d+)\s*\|", text, re.I | re.M)
            for found in quoted:
                if int(found) != n:
                    err(f"{path.relative_to(ROOT)}: says {found} {kind}s, found {n} on disk")
                    break


# --------------------------------------------------------------------------- runner


def main() -> int:
    quiet = "--quiet" in sys.argv
    market_path = ROOT / ".claude-plugin" / "marketplace.json"
    if not market_path.exists():
        print(f"no marketplace at {market_path}", file=sys.stderr)
        return 1
    market = json.loads(market_path.read_text())

    plugins = [ROOT / e["source"].lstrip("./") for e in market["plugins"]]
    for plugin in plugins:
        if not plugin.is_dir():
            err(f"marketplace.json: source for '{plugin.name}' does not resolve")
            continue
        slug = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text())["name"]
        checks = [
            ("frontmatter", lambda: check_frontmatter(plugin)),
            ("tools", lambda: check_tools(plugin)),
            ("collisions", lambda: check_collisions(plugin)),
            ("references", lambda: check_references(plugin, slug)),
            ("links", lambda: check_links(plugin)),
            ("index contract", lambda: check_index_contract(plugin)),
            ("manifests", lambda: check_manifests(plugin, market)),
            ("counts", lambda: check_counts(plugin)),
        ]
        for label, fn in checks:
            # A check that crashes must not take the rest of the run with it -- a partial
            # report is useful, a traceback with no findings is not.
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                err(f"{plugin.name}: '{label}' check crashed -- {type(exc).__name__}: {exc}")

    for w in warnings:
        if not quiet:
            print(f"WARN   {w}")
    for e in errors:
        print(f"ERROR  {e}")

    n = sum(len(components(p)) for p in plugins if p.is_dir())
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s) across {n} components")
        return 1
    if not quiet:
        print(f"\nok  {n} components, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
