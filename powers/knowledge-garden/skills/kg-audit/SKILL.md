---
name: kg-audit
description: "Audit the existing codebase (whole project, one module, or one path) against the project's defined coding rules, best practices, and security. Produces a severity-ranked report with path:line evidence for every finding. Use for a periodic health check, before a release, or when taking over a codebase. Use /kg-review for a diff instead."
license: MIT
---

# Audit

> **Input:** the text typed after `/kg-audit`, or the user's request when Kiro loads this skill on its own.

**Purpose:** Check the code that **already exists** against three things:

1. **Rules:** the coding rules this project defines (the project's `AGENTS.md` / its own `.kiro/steering/` files, the
   stack ruleset installed in `.kiro/steering/`, and `critical-patterns.md`)
2. **Best practices:** performance, robustness, type safety, tests, maintainability
3. **Security:** OWASP-mapped checks for the stack, plus vulnerable dependencies

Every finding is verified against the code and cited with `path:line`.

**How this differs from `/kg-review`:** review looks at a diff and only flags lines the diff
touches. Audit looks at the codebase as it stands.

**Read-only on project code.** This skill never edits project files and never touches other
skills' files. The only file it writes is its own report (Step 6). Fixing is handed off to
`/kg-quickfix` or `/kg-plan`.

---

## Process

<step number="1" required="true">
### Step 1: Parse Scope

Read the input. Both parts are optional and can come in either order.

| Part | Values | Default |
|------|--------|---------|
| **Dimension** | `rules`, `practices`, `security` (comma-separated for several) | all three |
| **Target** | a module name (matched to `docs/knowledge/modules/{name}.md`) or a path (`app/Services`, `src/app/(admin)`) | the whole project |

Examples: `/kg-audit` · `/kg-audit security` · `/kg-audit rules Order` · `/kg-audit rules,security app/Http`

State the scope you picked in one line, for example `Auditing: rules + security, whole project.`
Do not ask clarifying questions. Make a reasonable interpretation.
</step>

<step number="2" required="true" depends_on="1">
### Step 2: Load Context

Read these in parallel. Skip any that don't exist, without comment:

1. `kg.local.md`, or `knowledge-garden.local.md` for projects set up before 0.4.0. It gives the
   **stack**. If neither exists, detect it: `artisan` + `composer.json` means Laravel,
   `next.config.*` means Next.js, both means full-stack, neither means generic.
2. The project's `AGENTS.md` / its own `.kiro/steering/` files. Its rules **outrank** the plugin rulesets.
3. `docs/knowledge/patterns/critical-patterns.md`. Each documented pattern is a rule to check.
4. The stack's rulesets: the kg coding rules installed by `/kg-setup` as steering: `.kiro/steering/kg-laravel.md`, `.kiro/steering/kg-nextjs.md`, or both, matching the stack in `kg.local.md` (or the legacy `knowledge-garden.local.md`). Skip for a `generic` stack. If the stack has rules but the steering file is missing, say so and suggest re-running `/kg-setup`.
5. `docs/knowledge/index.md`, only to resolve a module target into its file map.

**Resolve the target into a file set:**

- Module: use the module doc's file map. If there's no module doc, Glob for the module name.
- Path: everything under it.
- Whole project: the app source only. **Always exclude** `vendor/`, `node_modules/`, `.next/`,
  `storage/`, `public/build/`, `dist/`, lock files, and generated or minified files.
</step>

<step number="3" required="true" depends_on="2">
### Step 3: Signal Scan

Run **targeted Grep searches**. Never read the tree file by file. Every hit is a **candidate**, not
a finding, until Step 4 confirms it.

> **Regex note:** the checklists are markdown tables, so a `|` inside a pattern is written `\|`.
> When you pass a pattern to Grep, write it as a plain `|` (alternation). Passing `\|` through
> matches a literal pipe character and the search will quietly find nothing.

**3a. Rules (`rules`).** Check the code against the rules this project defines, in precedence
order:

1. **Project `AGENTS.md` / its own `.kiro/steering/` files:** for every concrete rule ("use X, never Y", "all A go
   through B"), derive one or two Grep patterns that would catch a violation.
2. **`critical-patterns.md`:** Grep for the anti-pattern each entry documents. A match is the
   highest-value finding an audit can produce: a mistake this team already paid for once.
3. **Stack ruleset:** for each numbered section of `kg-laravel.md` / `kg-nextjs.md`, derive one or two
   Grep patterns. For example, `use App\\Models\\` inside `Http/Controllers/` catches "controllers
   never touch Eloquent", and `$guarded = []` catches the fillable rule. Use rule ids
   `rules.{ruleset}-{section}`, e.g. `rules.laravel-1`, `rules.claude-md`, `rules.critical`.

**Convention detection.** Before you report a stack-ruleset violation, count the conforming and
non-conforming occurrences. If the project departs from a rule **consistently** (most files do it
the other way), it's a convention, not a finding. Report it once as a Convention note, following
the *Precedence and conflicts* section at the end of each kg steering file, and don't list every file. This does not apply to `AGENTS.md` rules or critical
patterns: those are the project's own decisions, so every violation counts.

**3b. Best practices (`practices`).** Run the checks in
[best-practices.md](./references/best-practices.md): N+1 queries, unbounded queries, missing
indexes, swallowed exceptions, missing transactions, type safety, test gaps, and maintainability.

Where the project already has the tool, run it and record the **counts**. These commands are
read-only and their output is evidence:

```bash
npx tsc --noEmit 2>&1 | tail -5          # Next.js / TS
npm run lint 2>&1 | tail -15
vendor/bin/pint --test 2>&1 | tail -10   # Laravel
vendor/bin/phpstan analyse --no-progress 2>&1 | tail -15   # only if phpstan.neon exists
```

**3c. Security (`security`).** Run the checks in
[security-checklist.md](./references/security-checklist.md) for the stack: secrets, injection,
XSS, authorization, tenant scoping, mass assignment, CSRF/CORS, uploads, crypto, config, logging.

Then check dependencies with the package manager's own audit. Run only the ones whose lock file
exists:

```bash
composer audit --format=plain 2>&1 | tail -40          # composer.lock
npm audit --omit=dev 2>&1 | tail -40                   # package-lock.json
pnpm audit --prod 2>&1 | tail -40                      # pnpm-lock.yaml
```

If the project has dedicated scanners installed (`gitleaks`, `semgrep`), run them too. They are
more thorough than Grep, especially for secrets in git history.

Skip any tool the project doesn't have, never install one, and list everything skipped in the
report's Coverage section. Never claim "no vulnerable dependencies" without having run the audit.
</step>

<step number="4" required="true" depends_on="3">
### Step 4: Verify

For each candidate, **read the surrounding lines** (about 20, not the whole file) and decide:

- **Confirmed:** the defect is real in context. Keep it.
- **False positive:** e.g. the input is already validated, the raw SQL has no user input, or the
  secret is a placeholder in `.env.example`. Drop it silently.
- **Needs runtime check:** you can't tell statically, e.g. whether a middleware is applied
  globally. Keep it as **Unverified** and say what would confirm it.

**Budget:** verify at most about 40 candidates. Verify in this order: security, then `AGENTS.md`
and critical-pattern violations, then everything else. If there are more, group the rest by rule
with a count (e.g. "`whereRaw` with interpolation: 14 more sites, listed below, not individually
verified").
</step>

<step number="5" required="true" depends_on="4">
### Step 5: Classify

| Level | Meaning | Examples |
|-------|---------|----------|
| **Critical** | Exploitable now, or data exposure | SQL injection with user input, committed live secret, missing auth on a write endpoint, tenant leak, known-exploited CVE |
| **High** | Security weakness, or a violation of `AGENTS.md` / a critical pattern | `$guarded = []`, missing Policy on route-model binding, `APP_DEBUG=true` in a prod config, high-severity CVE, repeat of a documented mistake |
| **Medium** | Stack-rule violation or best-practice gap with a real cost | controller querying Eloquent, N+1 in a list endpoint, swallowed exceptions, untested endpoint |
| **Low** | Hygiene | naming, `any`, TODO debt, dead code, lint count |

Tag every finding with its dimension and rule id. For security findings, add the OWASP Top 10
category (e.g. `A01 Broken Access Control`).
</step>

<step number="6" required="true" depends_on="5">
### Step 6: Report and Save

Print the report and write the same content to
`docs/knowledge/audits/YYYY-MM-DD-{scope-slug}.md` (e.g. `2026-10-15-full.md`,
`2026-10-15-security-order.md`). Create the directory if it's missing. If a file with that name
already exists today, add `-2`.

```markdown
---
date: YYYY-MM-DD
scope: { dimensions: [rules, practices, security], target: "whole project" }
stack: laravel
counts: { critical: 0, high: 0, medium: 0, low: 0, unverified: 0 }
---

# Audit: {scope}, YYYY-MM-DD

## Summary

| Dimension | Critical | High | Medium | Low |
|-----------|----------|------|--------|-----|
| Rules     | | | | |
| Practices | | | | |
| Security  | | | | |

**Top 3 to fix first:** one line each, the highest severity with the smallest fix.

## Findings

### Critical

#### C1. [Title]   `security` · `A03 Injection` · rule: `sec.sql-raw`
- **Where:** `app/Repositories/OrderRepository.php:88`
- **Evidence:** the offending line or two
- **Why it matters:** one sentence on the impact
- **Fix:** one or two sentences, or a short WRONG/CORRECT snippet
- **Rule source:** `AGENTS.md` / `critical-patterns.md#...` / `kg-laravel.md §7` / checklist

### High
### Medium
### Low
(Low findings can be a compact table: `| rule | path:line | note |`)

### Unverified
[candidate, plus what would confirm it]

## Convention Notes
[Consistent departures from the stack ruleset. Candidates for the project's AGENTS.md.]

## Tool Results
| Tool | Result |
|------|--------|
| tsc | 0 errors |
| composer audit | 2 advisories (1 high) |

## Coverage
- Files in scope: N · Candidates: N · Verified: N · Grouped/unverified: N
- Rules checked: N from AGENTS.md, N critical patterns, N ruleset sections
- Skipped: [tools not installed, audits that needed network, dimensions not run]
```
</step>

<step number="7" required="true" depends_on="6">
### Step 7: Hand Off

End with a short list of next actions. Don't run any of them:

```
Next:
- /kg-quickfix "<C1 title> in <path>"                        (one-file fixes)
- /kg-plan "Fix tenant scoping across Order and Invoice"    (multi-file fixes)
- /kg-compound after fixing any Critical, so the lesson is captured
- Promote N convention notes into AGENTS.md
```

If a **Critical** finding is a committed secret, say first, in bold, that the secret must be
**rotated**. Removing it from the code doesn't revoke it, and it stays in git history.
</step>

---

## Guidelines

- Never edit project code, never install packages, never spawn agents.
- Grep first, read second. A finding without a `path:line` and evidence is not a finding.
- Never print a secret's value in the report. Show the key name and the first 4 characters only.
- Precedence follows the *Precedence and conflicts* section at the end of each kg steering file: `AGENTS.md` > critical patterns > consistent project
  convention > plugin rulesets.
- Prefer fewer, verified findings over a long speculative list. Group repeats by rule instead of
  listing 50 identical lines.
- Say plainly what wasn't checked. A clean report with an empty Coverage section is a false
  assurance.
