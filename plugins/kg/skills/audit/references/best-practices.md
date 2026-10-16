# Best-Practice Checklist

Checks for the `practices` dimension of `/kg:audit`. As in the security checklist, a Grep hit is a
candidate and the audit reads the site before reporting it. Ids are stable.

**Regex note:** `\|` in the tables below is markdown escaping. Pass it to Grep as a plain `|`.

Default severity is **Medium** for correctness and performance items and **Low** for hygiene. Raise
the severity when the site is on a hot path (a list endpoint, a dashboard, a checkout).

## Performance

| Id | Stack | Look for | How to find | Confirm by checking |
|----|-------|----------|-------------|---------------------|
| `bp.n-plus-one` | Laravel | Relation accessed in a loop without eager loading | Resources/loops touching `$this->relation` / `$item->relation`. Check the repository query that feeds them for `with(` / `load(` | The relation isn't eager-loaded on that path. Also check whether `Model::preventLazyLoading()` is enabled in `AppServiceProvider` (if it isn't, flag that once, **Low**) |
| `bp.unbounded-query` | Laravel | `->get()` / `::all()` on a listing | `::all\(\)\|->get\(\)` in repositories/controllers | The table can grow without bound and nothing paginates or limits it |
| `bp.missing-fk-index` | Laravel | Foreign keys without an index | Migrations: `unsignedBigInteger\('\w+_id'\)` with no `->index()` / `foreignId(...)->constrained()` | The column is filtered or joined on |
| `bp.query-in-loop` | Both | Query or fetch inside a loop | `foreach`/`.map(` blocks containing `::find\|->where\(\|await fetch\|await db` | It runs per item rather than once per batch |
| `bp.client-waterfall` | Next.js | Sequential awaits that could run in parallel | Consecutive `await fetch`/`await get…` in server components with no data dependency | They're independent and not wrapped in `Promise.all` |
| `bp.use-client-overuse` | Next.js | `'use client'` on components with no interactivity (rules §3) | `'use client'` files | No hooks, handlers, or browser APIs. It could be a server component |
| `bp.img-tag` | Next.js | Raw `<img>` instead of `next/image` | `<img ` in `.tsx` | Not an SVG icon, email template, or deliberate exception |

## Correctness and robustness

| Id | Stack | Look for | How to find | Confirm by checking |
|----|-------|----------|-------------|---------------------|
| `bp.swallowed-exception` | Both | Empty or log-only catch blocks | `catch\s*\([^)]*\)\s*\{\s*\}\|catch\s*\{\s*\}` and catches that only `console.log` | The error is lost and the caller sees success |
| `bp.missing-transaction` | Laravel | Multi-write service methods without a transaction | Service methods with two or more `create`/`update`/`delete` calls | No `DB::transaction` wraps them, so a mid-way failure leaves partial data |
| `bp.no-validation` | Laravel | Controller reading input with no FormRequest | `Request \$request` in controller signatures (rules §1) | No FormRequest and no `validate()` call |
| `bp.env-outside-config` | Laravel | `env()` called outside `config/` | `env\(` outside `config/` | Any hit. It returns `null` once config is cached |
| `bp.missing-error-boundary` | Next.js | Route segments with no `error.tsx` | Glob `app/**/page.tsx`, compare with `app/**/error.tsx` | Top-level segments with data fetching have no boundary |
| `bp.missing-loading` | Next.js | Async pages with no `loading.tsx` / Suspense | Same comparison with `loading.tsx` | **Low**. Only report for pages that fetch data |

## Type safety and standards

| Id | Stack | Look for | How to find | Notes |
|----|-------|----------|-------------|-------|
| `bp.any` | Next.js | `any` (rules §8) | `:\s*any\b\|as any\|<any>` | Report the count plus the worst five sites |
| `bp.ts-ignore` | Next.js | Suppressed type errors | `@ts-ignore\|@ts-expect-error\|eslint-disable` | Report the count. List the ones with no reason comment |
| `bp.missing-types` | Laravel | Public methods without return types | `public function \w+\([^)]*\)\s*\{` | Count only. **Low** |
| `bp.enum-cast` | Laravel | Enum columns without casts (rules §7) | Models with enum-backed columns and no `$casts` entry | |

## Tests

| Id | Stack | Look for | How to find |
|----|-------|----------|-------------|
| `bp.untested-endpoint` | Laravel | Controllers with no feature test file (rules §10) | For each `app/Http/Controllers/**/{Name}Controller.php`, Glob for the mirrored `tests/Feature/**/{Name}ControllerTest.php`. Report missing files, then public actions with no happy-path test. Missing optional cases (422/401/403/404) are not findings |
| `bp.status-only-assert` | Laravel | Tests asserting status only (rules §10) | Feature tests with `assertStatus\|assertOk` and no `assertJson\|assertJsonPath\|assertJsonStructure` |
| `bp.untested-route` | Next.js | Critical flows with no E2E test | If `playwright.config.*` exists, compare `app/**/page.tsx` routes with the paths in `tests/`/`e2e/`. Suggest `/kg:playwright-test` |
| `bp.no-tests` | Both | No test suite at all | No `tests/` / `__tests__` / `*.test.*` / `*.spec.*`. This one is **High** |

## Maintainability

| Id | Look for | How to find | Threshold |
|----|----------|-------------|-----------|
| `bp.god-file` | Oversized files | `find <src> -name '*.php' -o -name '*.ts*' \| xargs wc -l \| sort -rn \| head -10` | More than 500 lines for a service/controller/component. Report the top 5 |
| `bp.duplicate-pattern` | Second implementations (rules §9) | Multiple formatters, confirm dialogs, status badges: Grep `formatCurrency\|ConfirmDialog\|StatusBadge` and similar | More than one definition |
| `bp.todo-debt` | TODO / FIXME / HACK | `\b(TODO\|FIXME\|HACK\|XXX)\b` | Count only, plus any that mention security or data loss |
| `bp.dead-code` | Unused exports/classes | Classes or exports with zero references outside their own file | Spot-check only. Report as **Unverified** unless it's clearly unreachable |
| `bp.commented-code` | Large commented-out blocks | 5 or more consecutive lines starting with `//` and containing code (`;`, `=`, `(`) | **Low** |
