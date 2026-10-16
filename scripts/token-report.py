#!/usr/bin/env python3
"""Write a token-usage report from Claude Code session transcripts.

Claude Code already records per-request token counts in its session transcripts under
~/.claude/projects/<project-slug>/*.jsonl. This reads them and writes a plain-text report --
nothing needs to be enabled beforehand, and it works retroactively on sessions already recorded.

Usage:
    python3 scripts/token-report.py                       # all projects -> token-usage.txt
    python3 scripts/token-report.py --project pos         # only projects matching "pos"
    python3 scripts/token-report.py --days 7              # last 7 days
    python3 scripts/token-report.py --out ~/usage.txt
    python3 scripts/token-report.py --by session          # session totals only

A "turn" is one user message plus every assistant request made before the next user message --
so a single request of yours that fans out into twenty tool calls is reported as one turn.

Token columns:
    input     fresh input tokens
    cache-w   written to the prompt cache (costs more than input)
    cache-r   read from the prompt cache (costs much less than input)
    output    generated tokens
    sub       tokens used by subagents dispatched during that turn

Counts only. Rates differ per model and change over time, so no cost is computed here --
use /cost in Claude Code for the billed figure.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"

FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


class Bucket:
    """Accumulated token counts for a turn or a session."""

    __slots__ = ("input", "cache_w", "cache_r", "output", "sub", "requests", "sub_requests")

    def __init__(self) -> None:
        self.input = self.cache_w = self.cache_r = self.output = 0
        self.sub = 0
        self.requests = self.sub_requests = 0

    def add(self, usage: dict, *, sidechain: bool) -> None:
        i, cw, cr, o = (int(usage.get(f) or 0) for f in FIELDS)
        if sidechain:
            # Subagent context is isolated from yours; report it separately so a cheap Haiku
            # researcher is not confused with main-context growth.
            self.sub += i + cw + cr + o
            self.sub_requests += 1
            return
        self.input += i
        self.cache_w += cw
        self.cache_r += cr
        self.output += o
        self.requests += 1

    @property
    def total(self) -> int:
        return self.input + self.cache_w + self.cache_r + self.output + self.sub


def human(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def text_of(message: dict) -> str:
    """First line of a user message, for labelling a turn."""
    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    else:
        text = ""
    for line in text.strip().splitlines():
        line = line.strip()
        # Skip harness-injected blocks so the label reflects what was actually typed.
        if line and not line.startswith(("<", "Caveat:", "[Request interrupted")):
            return line
    return ""


def stamp_of(rec: dict) -> datetime | None:
    if not rec.get("timestamp"):
        return None
    try:
        return datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        return None


def subagent_usage(session: Path):
    """Yield (timestamp, usage) for every subagent request spawned by a session.

    Subagent transcripts are written to <session-id>/subagents/agent-*.jsonl -- a directory
    beside the session file, not inside it. Reading only <project>/*.jsonl misses them
    entirely and silently reports zero subagent usage.
    """
    subdir = session.with_suffix("") / "subagents"
    if not subdir.is_dir():
        return
    for path in sorted(subdir.glob("*.jsonl")):
        for raw in path.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "assistant":
                continue
            usage = (rec.get("message") or {}).get("usage")
            if usage:
                yield stamp_of(rec), usage


def parse(path: Path, cutoff: datetime | None):
    """Yield (turn_index, label, started_at, Bucket) for one transcript."""
    turns: list[tuple[str, datetime | None, Bucket]] = []
    current: Bucket | None = None

    for raw in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue

        stamp = None
        if rec.get("timestamp"):
            try:
                stamp = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                stamp = None

        kind = rec.get("type")
        if kind == "user" and not rec.get("isSidechain"):
            label = text_of(rec.get("message") or {})
            if label:  # tool results arrive as user records too; they are not new turns
                current = Bucket()
                turns.append((label, stamp, current))
            continue

        if kind != "assistant":
            continue
        usage = (rec.get("message") or {}).get("usage")
        if not usage:
            continue
        if current is None:  # usage before any labelled prompt (session restore, etc.)
            current = Bucket()
            turns.append(("(session start)", stamp, current))
        current.add(usage, sidechain=bool(rec.get("isSidechain")))

    # Attribute each subagent request to the turn that was running when it fired.
    dated = [(s, b) for _, s, b in turns if s]
    for when, usage in subagent_usage(path):
        target = None
        if when and dated:
            for start, bucket in dated:
                if start <= when:
                    target = bucket
                else:
                    break
        if target is None and turns:
            target = turns[-1][2]
        if target is not None:
            target.add(usage, sidechain=True)

    for i, (label, stamp, bucket) in enumerate(turns, 1):
        if cutoff and stamp and stamp < cutoff:
            continue
        if bucket.requests or bucket.sub_requests:
            yield i, label, stamp, bucket


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="token-usage.txt", help="output file (default: token-usage.txt)")
    ap.add_argument("--project", default="", help="only projects whose slug contains this")
    ap.add_argument("--days", type=int, default=0, help="only turns from the last N days")
    ap.add_argument("--by", choices=("turn", "session"), default="turn", help="report granularity")
    args = ap.parse_args()

    if not PROJECTS.is_dir():
        print(f"no transcripts at {PROJECTS}")
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days) if args.days else None
    out: list[str] = []
    grand = Bucket()
    per_project: dict[str, Bucket] = defaultdict(Bucket)

    header = f"{'when':<17} {'turn':>5} {'input':>8} {'cache-w':>8} {'cache-r':>9} {'output':>8} {'sub':>8}  prompt"

    projects = sorted(p for p in PROJECTS.iterdir() if p.is_dir() and args.project in p.name)
    for project in projects:
        sessions = sorted(project.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
        rows: list[str] = []
        proj = per_project[project.name]

        for session in sessions:
            sb = Bucket()
            for idx, label, stamp, b in parse(session, cutoff):
                when = stamp.astimezone().strftime("%Y-%m-%d %H:%M") if stamp else "-"
                if args.by == "turn":
                    rows.append(
                        f"{when:<17} {idx:>5} {human(b.input):>8} {human(b.cache_w):>8} "
                        f"{human(b.cache_r):>9} {human(b.output):>8} {human(b.sub):>8}  {label[:60]}"
                    )
                for attr in ("input", "cache_w", "cache_r", "output", "sub", "requests", "sub_requests"):
                    setattr(sb, attr, getattr(sb, attr) + getattr(b, attr))
                    setattr(proj, attr, getattr(proj, attr) + getattr(b, attr))
                    setattr(grand, attr, getattr(grand, attr) + getattr(b, attr))
            if sb.requests or sb.sub_requests:
                rows.append(
                    f"{'  session total':<17} {sb.requests:>5} {human(sb.input):>8} "
                    f"{human(sb.cache_w):>8} {human(sb.cache_r):>9} {human(sb.output):>8} "
                    f"{human(sb.sub):>8}  {session.stem[:8]}  ({human(sb.total)} all-in)"
                )
                rows.append("")

        if rows:
            out.append(f"\n{'=' * 118}\n{project.name}\n{'=' * 118}")
            out.append(header)
            out.append("-" * 118)
            out.extend(rows)

    lines = [
        "Claude Code token usage",
        f"generated {datetime.now().astimezone():%Y-%m-%d %H:%M}"
        + (f"   (last {args.days} days)" if args.days else "")
        + f"   granularity: {args.by}",
        f"source: {PROJECTS}",
        "",
        "cache-r is read from the prompt cache and costs far less than fresh input.",
        "sub is subagent usage, which lives in its own context and never enters yours.",
    ]
    lines += out
    lines += ["", "=" * 118, "TOTALS BY PROJECT", "=" * 118]
    for name, b in sorted(per_project.items(), key=lambda kv: -kv[1].total):
        if not b.total:
            continue
        lines.append(
            f"{human(b.total):>9}  all-in   {name}"
            f"   (in {human(b.input)} / cache-w {human(b.cache_w)} / cache-r {human(b.cache_r)}"
            f" / out {human(b.output)} / sub {human(b.sub)}, {b.requests} requests)"
        )
    lines += [
        "",
        f"GRAND TOTAL  {human(grand.total)} tokens across {grand.requests} requests"
        f" and {grand.sub_requests} subagent requests",
        f"  fresh input {human(grand.input)} | cache write {human(grand.cache_w)}"
        f" | cache read {human(grand.cache_r)} | output {human(grand.output)}"
        f" | subagents {human(grand.sub)}",
    ]

    target = Path(args.out).expanduser()
    target.write_text("\n".join(lines) + "\n")
    print(f"wrote {target}  ({grand.requests} requests, {human(grand.total)} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
