# Coding Rules

Stack-level rules that Claude follows when writing code in a project using Knowledge Garden.

These describe **how code is written** — naming, layering, which class may touch what. They are
distinct from the two knowledge tiers the plugin already has:

| File | Holds | Source |
|------|-------|--------|
| `rules/*.md` (here) | how to write code | shipped with the plugin, stack-level |
| `docs/knowledge/patterns/critical-patterns.md` | rules earned from a specific failure | `/kg:compound` |
| `docs/knowledge/solutions/**` | what broke, why, and how it was fixed | `/kg:compound` |

## Which file applies

`setup` records the stack in `kg.local.md` (or the legacy `knowledge-garden.local.md`). Load the ruleset that matches:

| Stack | Ruleset |
|-------|---------|
| Laravel | [laravel.md](./laravel.md) |
| Next.js | [nextjs.md](./nextjs.md) |
| Full-stack | both |
| Generic | neither — follow the surrounding code |

## Precedence

These rules are the **default**, not the authority. When sources conflict, the more specific one
wins:

1. **The project's `CLAUDE.md` / `AGENTS.md`** — explicit, human-authored, project-specific. Always wins.
2. **`docs/knowledge/patterns/critical-patterns.md`** — earned from a real failure in this repo.
3. **The surrounding code**, when it consistently and deliberately differs. Three files doing the
   same thing a different way is a convention, not a mistake.
4. **These rules** — what to do when nothing above says otherwise.

Never rewrite working code purely to conform to this file. These rules govern code you are
**adding or changing**, not code you happen to read.

## Reporting a conflict

If the project consistently contradicts a rule here, say so once in your result rather than
silently following either side:

```
Convention note: this project puts <X> in <Y>, where the ruleset expects <Z>.
Followed the project.
```

That is the signal for promoting the difference into the project's `CLAUDE.md`, or for fixing
this ruleset.
