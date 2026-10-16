# Next.js Scanning Strategy

Reference-tracing approach for Next.js projects. Start from route segments, then find everything connected.

## Step 1: Identify the Module Anchor

Detect router type:
- **App Router**: check for `app/` directory with `page.tsx` or `page.jsx` files
- **Pages Router**: check for `pages/` directory with `.tsx` or `.jsx` files

Each top-level route segment = one module:
- App Router: `app/dashboard/`, `app/settings/`, `app/(auth)/login/`
- Pages Router: `pages/dashboard.tsx`, `pages/settings/index.tsx`

Read `page.tsx`/`layout.tsx` (App Router) or the page file (Pages Router) to extract component names and imports.

## Step 2: Trace All Imports From Route Files

Read all files in the route segment directory:
```
Glob: pattern="app/{segment}/**/*.{ts,tsx,js,jsx}"
```

For each file, extract every import statement:
```
Grep: pattern="^import .+ from ['\"]" path=app/{segment}/ output_mode=content
```

Build a dependency graph. Follow imports recursively (1 level deep) to find shared modules that this route depends on.

## Step 3: Grep the Entire Project for the Module Name

```
Grep: pattern="from.*['\"].*/{segment}/|/{segment}['\"]" path=src/ -i=false output_mode=files_with_matches
Grep: pattern="{ModuleType}|{ModuleName}" path=src/ -i=false output_mode=files_with_matches
```

Also check common alternative locations:
```
Grep: pattern="{segment}" path=lib/ -i=false output_mode=files_with_matches
Grep: pattern="{segment}" path=utils/ -i=false output_mode=files_with_matches
Grep: pattern="{segment}" path=hooks/ -i=false output_mode=files_with_matches
Grep: pattern="{segment}" path=stores/ -i=false output_mode=files_with_matches
Grep: pattern="{segment}" path=types/ -i=false output_mode=files_with_matches
```

This catches: components, hooks, stores, API clients, types, zod schemas, constants, enums, utils -- and any custom patterns the project uses (e.g., `src/features/`, `src/domains/`).

## Step 4: Auto-Categorize Matched Files

Read the first 20 lines of each matched file and categorize:

**By file content:**
- Contains `"use server"` -> Server Action
- Contains `"use client"` -> Client Component
- Contains `export default function` + JSX return -> Component (server by default in App Router)

**By path convention:**
- `hooks/` or filename `use-*.ts` -> Hook
- `stores/` or filename `*-store.ts` -> Store
- `types/` or filename `*.types.ts` -> Type Definition
- `schemas/` or contains `z.object` -> Zod Schema
- `constants/` or contains `as const` -> Enum/Constant
- `services/` or `api/` or `clients/` -> Service/API Client
- `components/` -> Component
- `utils/` or `lib/` -> Utility
- `actions.ts` or `actions/` -> Server Action
- `app/api/{segment}/route.ts` -> API Route

**By exports:**
- Exports `z.object(...)` -> Zod Schema
- Exports `enum` or `as const` object -> Enum/Constant
- Exports `interface` or `type` -> Type Definition

## Step 5: Write the Module Doc

Group all discovered files by their auto-detected category:

```markdown
# {Route Segment} Module

## Route Files
| File | Type | Notes |
|------|------|-------|
| app/{segment}/page.tsx | Page | main route component |
| app/{segment}/layout.tsx | Layout | wraps child routes |
| app/{segment}/loading.tsx | Loading | suspense fallback |
| app/{segment}/error.tsx | Error | error boundary |

## Connected Files
| Category | File | Notes |
|----------|------|-------|
| Component | app/{segment}/components/{...}.tsx | used in page |
| Server Action | app/{segment}/actions.ts | createItem, updateItem |
| API Route | app/api/{segment}/route.ts | GET, POST |
| Type | types/{segment}.ts | Item, ItemFormData |
| Zod Schema | schemas/{segment}.ts | itemSchema |
| Enum/Constant | constants/{segment}.ts | ItemStatus |
| Hook | hooks/use-{segment}.ts | data fetching |
| Store | stores/{segment}-store.ts | zustand slice |
| API Client | services/{segment}-api.ts | fetch wrapper |
| ... | ... | ... |

## Tests
| File | Type |
|------|------|
| __tests__/{...}.test.tsx | Component test |
| __tests__/api/{...}.test.ts | API test |
```

The table format automatically includes whatever file types exist. If a project uses `src/features/`, `src/domains/`, or colocates everything, the grep-and-trace approach finds it all.
