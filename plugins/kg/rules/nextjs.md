# Next.js Coding Rules

Applies to Next.js 15/16 App Router projects with React 19 and Tailwind v4. See
[README.md](./README.md) for precedence — the project's own `CLAUDE.md` always outranks this file.

> **Check the installed version first.** Recent App Router releases carry breaking changes against
> older knowledge. Before writing App Router code, read `node_modules/next/dist/docs/` if present,
> or the installed version's docs — do not write from recalled conventions.

## 1. Data flow

```
services/*-service.ts     axios call, returns response.data
  → hooks/use-*.ts        React Query; mutations toast and invalidate
  → app/**/page.tsx       screen composition only
```

- A component never calls axios directly. It calls a hook.
- A hook never builds a URL by hand. It calls a service.
- Mutations invalidate every query key the write affects, not just their own.

```ts
// WRONG — a write that moves stock invalidates only its own list
onSuccess: () => queryClient.invalidateQueries({ queryKey: ["transfers"] }),

// CORRECT
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ["transfers"] });
  queryClient.invalidateQueries({ queryKey: ["inventory"] });
},
```

## 2. Naming

| Thing | Case | Example |
|-------|------|---------|
| Component file | `kebab-case.tsx` | `order-form-dialog.tsx` |
| Component | `PascalCase` | `OrderFormDialog` |
| Hook | `use` + `camelCase` | `useCreateStockTransfer` |
| Service file | `kebab-case-service.ts` | `product-service.ts` |
| Variable, function | `camelCase` | `perPage`, `buildQueryParams` |
| Type / interface | `PascalCase` | `UserResponse` |
| Route segment | `kebab-case` | `app/(protected)/stock-transfers/` |

Use the `@/*` path alias for cross-directory imports; relative paths only within a folder.

## 3. Server and client components

- Server component by default. Add `"use client"` only when the file needs state, effects, event
  handlers, or browser APIs.
- Push `"use client"` **down** the tree. A client boundary on a layout makes everything beneath it
  a client component.
- Never `await` data in a client component. Fetch in a server component or in a React Query hook.

## 4. Reading the API envelope

The backend returns `{success, message, data}`, and paginated endpoints **spread** the paginator —
rows are at `data`, not `data.data`.

```ts
// WRONG
const rows = response.data.data.data;

// CORRECT — the service already unwrapped one level
const { data: rows, meta } = await productService.list(params);
```

Filters go out as Spatie params — `filter[store_id]`, not `store_id`. A top-level param the
backend does not declare is **silently ignored** and the request returns unfiltered rows. Build
them with the project's query-param helper rather than by hand.

## 5. Forms

- `react-hook-form` + `zodResolver`.
- `reset()` the form on `[open, entity?.id]` so a reused dialog does not carry the previous row's
  values.
- **Zod 4:** `z.coerce.number()` produces an `unknown` input type that breaks the resolver with an
  unreadable type error. Use `z.number()` with `{ valueAsNumber: true }` on the input.

## 6. Permission gating is cosmetic

Route→permission maps, `<Can>` wrappers, and guarded layouts hide UI. **The API is the security
boundary.** Never remove a backend guard because the button is hidden.

Any guard reading persisted auth state must wait for hydration. Zustand rehydrates from
`localStorage` after first render, so a check that runs early sees zero permissions and hides the
app from its own owner on every refresh. Handle it inside the guard component so call sites cannot
get it wrong.

## 7. Styling

- Tailwind v4 — no `tailwind.config`. The theme lives in `app/globals.css`.
- Use design tokens (`bg-primary`, `text-muted-foreground`), not raw hex.
- **Never combine the `background` shorthand with a Tailwind `bg-*` utility.** The shorthand resets
  `background-color`, so the utility silently loses. Use `background-image` for the gradient layer.
- Add shadcn/ui components with the CLI so they land in `components/ui/` with the project's style,
  rather than pasting them in.

## 8. Types

- No `any`. Use `unknown` and narrow.
- Types describing API payloads live in `types/`, named for the wire shape (`UserResponse`), and
  are the single definition — do not redeclare them per screen.
- A field that can be absent is `?:`, a field that can be empty is `| null`. They are different
  states and the distinction reaches the UI.
- `npx tsc --noEmit` must stay clean. If `npm run lint` is red at baseline, compare counts rather
  than expecting zero — but never add to them.

## 9. Reuse before adding

Before writing a list screen, dialog, status badge, confirm prompt, or currency formatter, check
whether the project already has one. List screens in particular usually follow a fixed shape —
`page.tsx` + `columns.tsx` + `actions.tsx` + a form dialog. Match the existing one rather than
inventing a second pattern.

When a route→permission list exists in more than one place (a nav config and a sidebar component
are the usual pair), adding a page means editing **both**. An entry in only one gives either a
reachable route nothing links to, or a link the guard refuses.
