# Security Checklist

Grep patterns for the `security` dimension of `/kg:audit`. Each row is a **candidate signal**:
a hit means "read this site", not "this is a vulnerability". Ids are stable, so reports from
different runs can be compared by hand.

**Regex note:** `\|` in the tables below is markdown escaping. Pass it to Grep as a plain `|`.

Run the **Common** checks for every stack, then the stack sections that apply.

## Common

| Id | OWASP | Look for | Grep (regex) | Confirm by checking |
|----|-------|----------|--------------|---------------------|
| `sec.secret-committed` | A02 | Live secrets in tracked files | `(sk_live_\|pk_live_\|AKIA[0-9A-Z]{16}\|ghp_[A-Za-z0-9]{36}\|xox[bp]-\|-----BEGIN (RSA \|EC )?PRIVATE KEY)` | The file is tracked (`git ls-files`), and it isn't `.env.example` or a test fixture with a fake value |
| `sec.env-tracked` | A05 | `.env` committed | `git ls-files \| grep -E '(^\|/)\.env($\|\.local$\|\.production$)'` | Any hit is confirmed. Also run `git log --all --oneline -- .env \| head` for history |
| `sec.hardcoded-credential` | A07 | Passwords/keys assigned in code | `(password\|secret\|api_key\|token)\s*[:=]\s*['"][^'"]{8,}['"]` | Not a placeholder, translation key, or test value |
| `sec.weak-hash` | A02 | Weak hashing for passwords/tokens | `\b(md5\|sha1)\s*\(` | Used for passwords, tokens, or signatures, not cache keys or ETags |
| `sec.insecure-random` | A02 | Non-crypto RNG for tokens | `Math\.random\(\)\|\brand\(\|\bmt_rand\(\|uniqid\(` | Output is used as a token, code, or identifier an attacker shouldn't guess |
| `sec.sensitive-log` | A09 | Secrets or PII written to logs | `(Log::\|logger\(\|console\.(log\|error))[^;]*(password\|token\|secret\|card\|authorization)` | The value itself is logged, not just the key name |
| `sec.ssrf` | A10 | Server fetching a user-supplied URL | `(Http::(get\|post)\|file_get_contents\|fetch)\(\s*\$?(request\|req\|params\|searchParams\|url)` | The URL comes from input with no allowlist |
| `sec.open-redirect` | A01 | Redirect to user input | `redirect\(\s*(\$request\|request\(\)\|searchParams\|req\.query)` | No allowlist or same-origin check |

## Laravel

| Id | OWASP | Look for | Grep (regex) | Confirm by checking |
|----|-------|----------|--------------|---------------------|
| `sec.sql-raw` | A03 | Raw SQL with interpolation | `(whereRaw\|selectRaw\|orderByRaw\|havingRaw\|DB::(raw\|select\|statement\|unprepared))\(\s*["'][^"']*(\$\|\{\|\.\s*\$)` | A variable reaches the string and isn't passed as a binding (`?`, second argument) |
| `sec.order-by-input` | A03 | Sort column taken from input | `orderBy\(\s*\$request` | No allowlist (Spatie `allowedSorts` counts as one) |
| `sec.mass-assignment` | A08 | Unguarded models / blind fill | `\$guarded\s*=\s*\[\s*\]\|->fill\(\s*\$request->all\(\)\|::create\(\s*\$request->all\(\)` | Any `$guarded = []` is confirmed. For `->all()`, check whether a FormRequest limits the keys |
| `sec.unescaped-blade` | A03 | Unescaped Blade output | `\{!!` | The value can hold user content (not a trusted, pre-sanitized HTML block) |
| `sec.route-no-auth` | A01 | Write routes outside auth middleware | Read `routes/api.php` and `routes/web.php`; list `post\|put\|patch\|delete` routes outside an `auth:` / `auth:sanctum` group | The route isn't intentionally public (login, register, webhook with signature check) |
| `sec.route-no-permission` | A01 | Write route with no `can:` / Policy | Write routes without `->middleware('can:` or a matching Policy method | The controller doesn't call `authorize()`/`Gate` either |
| `sec.binding-no-policy` | A01 | Route-model binding with no Policy (rules §7) | Controller methods type-hinting a tenant-owned Model, with no Policy registered for that model | Another tenant's id would load the record. Treat as **Critical** if it does |
| `sec.tenant-scope` | A01 | Tenant model listing without scope (rules §7) | Repositories of models with `tenant_id`/`store_id`/`branch_id` whose query has no `where(…tenant…)` or global scope | The listing really returns cross-tenant rows |
| `sec.gate-before-false` | A01 | `Gate::before` returning `false` (rules §8) | `Gate::before` | It returns `false` on some path |
| `sec.csrf-except` | A01 | CSRF exclusions | `validateCsrfTokens\(except\|\$except\s*=` | Excluded routes are state-changing and not signature-verified webhooks |
| `sec.cors-wildcard` | A05 | CORS wide open with credentials | `config/cors.php`: `'allowed_origins' => ['*']` with `'supports_credentials' => true` | Both are set |
| `sec.debug-on` | A05 | Debug in non-local config | `APP_DEBUG=true` in tracked env files; `'debug' => true` hard-coded in `config/app.php` | Not `.env.example` with a local note |
| `sec.upload-validation` | A04 | Uploads without type/size rules | `->file\(\|->store\(\|->storeAs\(` | The FormRequest has no `mimes:`/`mimetypes:` and `max:` rule. Also check for user-controlled filenames |
| `sec.rate-limit-auth` | A07 | Login/OTP/reset without throttle | Auth routes in `routes/` | No `throttle:` middleware or `RateLimiter::for` covers them |
| `sec.unserialize` | A08 | `unserialize` on input | `unserialize\(` | The input isn't fully trusted |
| `sec.shell` | A03 | Shell execution | `\b(exec\|shell_exec\|system\|passthru\|proc_open)\(\|Process::run\(` | Input reaches the command without `escapeshellarg` or an array-form command |

## Next.js

| Id | OWASP | Look for | Grep (regex) | Confirm by checking |
|----|-------|----------|--------------|---------------------|
| `sec.public-env-secret` | A02 | Secrets exposed to the browser | `NEXT_PUBLIC_[A-Z_]*(SECRET\|KEY\|TOKEN\|PASSWORD)` | It's a real secret, not a publishable key (e.g. Stripe `pk_`) |
| `sec.dangerous-html` | A03 | Raw HTML injection | `dangerouslySetInnerHTML` | The content isn't sanitized (DOMPurify or a trusted source) |
| `sec.server-action-auth` | A01 | Server Actions / route handlers with no auth | Files with `'use server'` and `app/**/route.ts` | The exported function mutates data or reads private data without checking the session first |
| `sec.client-only-guard` | A01 | Security enforced only in the UI (rules §6) | `<Can\|hasPermission\|usePermission` around mutations | The matching API endpoint has no backend guard. Check the backend if it's in the repo |
| `sec.token-localstorage` | A07 | Auth tokens in `localStorage` | `localStorage\.setItem\([^)]*(token\|jwt\|auth)` | It's a bearer token, not a non-sensitive preference |
| `sec.middleware-matcher` | A01 | Auth middleware that misses routes | `middleware.ts` `matcher` | Protected route groups fall outside the matcher |
| `sec.eval` | A03 | Dynamic code execution | `\beval\(\|new Function\(` | Any input reaches it |
| `sec.image-remote-wildcard` | A05 | `images.remotePatterns` with `hostname: '**'` | `next.config.*` | Wildcard host, which lets anyone use your optimizer as a proxy |
| `sec.headers-missing` | A05 | No security headers | `next.config.*` `headers()` / middleware | No CSP, `X-Frame-Options`/`frame-ancestors`, or `Referrer-Policy` set anywhere (**Low** unless the app embeds untrusted content) |

## Generic stack

Run **Common**, then adapt the Laravel/Next.js ideas to what the project uses: raw query strings
with interpolation, template output that skips escaping, routes or handlers with no auth check,
and debug flags in committed config.
