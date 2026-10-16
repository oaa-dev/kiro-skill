# Laravel Coding Rules

Applies to Laravel 11/12 API projects. See [README.md](./README.md) for precedence — the project's
own `CLAUDE.md` always outranks this file.

## 1. Request flow

Every request passes through the full chain. Do not skip a layer, do not add one.

```
routes/api.php
  → Http/Requests/*Request        validation
  → Http/Controllers/Api/V1/*Controller   thin; constructor-injects a Service
  → Data/*Data                    spatie/laravel-data DTO, built with ::from()
  → Services/*Service             business rules, orchestration
  → Repositories/*Repository      all Eloquent access
  → Models/*
  → Http/Resources/*Resource      + Traits/ApiResponse envelope
```

**The three boundary rules:**

- Controllers never touch Eloquent or `DB`.
- Services never build queries.
- Repositories never contain business rules.

```php
// WRONG — controller reaching past the service into Eloquent
public function index(Request $request)
{
    return User::with('profile')->paginate(15);
}

// CORRECT — controller delegates; the repository owns the query
public function index(IndexUserRequest $request)
{
    return $this->successResponse($this->userService->paginate($request->perPage()));
}
```

## 2. Naming

| Thing | Case | Example |
|-------|------|---------|
| Class / file | `StudlyCase` | `UserProfileService.php` |
| Method, variable, property | `camelCase` | `findAllBy()`, `$perPage` |
| DB table, column | `snake_case` | `user_profiles`, `store_id` |
| Route path | `kebab-case` | `/api/v1/stock-transfers` |
| Config / lang key | `snake_case` | `config('services.paymongo.key')` |
| Enum case | `StudlyCase` | `AccountStatusEnum::Suspended` |
| Permission | `module.action` | `sales.void`, `products.cost` |

Never kebab-case a permission. Never camelCase a column.

## 3. Data crosses the controller→service boundary as a `Data` object

Not an array, not the `Request`.

```php
// WRONG
$this->userService->update($user, $request->validated());

// CORRECT
$this->userService->update($user, UserData::from($request));
```

Exceptions are legitimate but must be deliberate — a hot path carrying several nested collections
at once, or two scalars going into named arguments. If you make one, say so in your result.

**`Optional` means "not submitted"; an explicit `null` means "clear it".** Default every DTO field
to `new Optional` and filter on `instanceof Optional` in the service.

```php
// WRONG — a field can never be cleared
$payload = array_filter($data->all(), fn ($v) => $v !== null);

// WRONG — a PATCH of one field wipes the rest
$model->update($data->all());

// CORRECT
$payload = collect($data->all())->reject(fn ($v) => $v instanceof Optional)->all();
```

## 4. Every list endpoint uses Spatie QueryBuilder, inside the repository

Declare `allowedFilters()`, and `allowedSorts()` / `allowedIncludes()` / `defaultSort()` as needed.
`query()` assembles them and stays `protected`; index endpoints call `paginate()`.

```php
protected function allowedFilters(): array
{
    return ['name', 'status', AllowedFilter::custom('q', new GlobalSearchFilter(['name', 'category.name']))];
}
```

A filter the frontend sends but the repository does not declare is **silently ignored** and the
endpoint returns unfiltered rows. When adding a filter, add it on both sides in the same change.

## 5. Every endpoint returns a Resource through the ApiResponse envelope

Never return a model, an array, or a bare collection.

```php
// WRONG
return response()->json($user);

// CORRECT
return $this->successResponse(new UserResource($user), 'User retrieved');
```

- `successResponse` / `errorResponse` → `{success, message, data}`
- `paginatedResponse` **spreads** the paginator → `{success, message, data: [...], links, meta}`.
  Rows are at `data`, **not** `data.data`.

**Use the callback form of `whenLoaded`.** The one-argument form drops the key entirely when the
relation is loaded but null, giving an unstable response shape:

```php
// WRONG — key vanishes when the relation is loaded but empty
'role' => new RoleResource($this->whenLoaded('role')),

// CORRECT — key absent means "not loaded", null means "loaded and empty"
'role' => $this->whenLoaded('role', fn () => new RoleResource($this->role)),
```

Moving a field behind `whenLoaded()` is a two-part change: add the eager load in the same commit,
or the field silently disappears from every row with no error.

## 6. Repositories

- Every repository has an interface in `Repositories/Contracts/`, bound in
  `AppServiceProvider::$bindings`. **Services type-hint the interface, never the concrete class.**
  Any public method beyond the base must be declared on the interface.
- `update(Model $model, …)` and `delete(Model $model)` take **models, not ids** — controllers use
  route-model binding and pass the bound instance.
- `findById()` throws `ModelNotFoundException`; `find()` is the nullable one.
- Use `find($id, $columns)`, never `select($columns)->find($id)` — the latter drops the primary key
  when `$columns` omits `id`, which breaks `refresh()`.

## 7. Models

- Cast every enum-backed column on the model (`protected $casts`).
- Declare `$fillable` explicitly. Never `$guarded = []`.
- A model belonging to a tenant or branch must be scoped in its repository — a listing that
  forgets it leaks one tenant's rows to another. Treat that as a security defect, not a bug.
- Route-model binding **bypasses the repository**, so a listing scope does not protect `show` or
  `update`. Those need a Policy.

## 8. Authorization

- Permission checks live on routes (`can:` middleware), not in services. A `can()` call inside a
  service should be data scoping, not a gate — and should say so in a comment.
- **`Gate::before` must return `true` or `null`, never `false`.** Returning `false` denies every
  ability and short-circuits every Policy.

## 9. Migrations and seeders

- One migration per structural change; never edit a migration that has shipped to another
  environment.
- Composite uniques that include a tenant column must be matched by the validation rule, or the
  second tenant cannot reuse a value the database would accept.
- **Every seeder must be idempotent** (`firstOrCreate` / `updateOrCreate` / `sync`). `db:seed` is
  expected to be re-runnable.

## 10. Tests

- Pest, `tests/Feature` for endpoints. `RefreshDatabase` on feature tests only.
- **Every controller has exactly one feature test file**, mirroring its path:
  `app/Http/Controllers/Api/V1/UserController.php` → `tests/Feature/Api/V1/UserControllerTest.php`.
  A new controller and its test file land in the same change.
- **Every public action in that controller has a happy-path test. Always, no exceptions.** It
  asserts the 200/201 status **and** the envelope body (§5), not just the status.
- Add these when they apply. They are recommended, not required:

  | Case | Expect |
  |------|--------|
  | Invalid input (actions with a FormRequest) | 422 and the failing field under `errors` (§12) |
  | Unauthenticated | 401 |
  | Missing permission (routes with `can:`) | 403 |
  | Unknown or other-tenant id (route-model binding) | 404 / 403 |
  | List endpoint filters and sorts (§4) | each declared filter actually narrows the rows |

  Group the cases per action with `describe('store', …)` so a missing action is visible at a glance.
- Assert on the response **body**, not just the status code. A wrong-but-200 response shape is the
  failure mode this catches.
- Distinguish absent from null: `array_key_exists('role', $row)` does, `$row['role'] === null`
  does not.
- A test that cannot fail proves nothing — check that a new regression test fails against the old
  behaviour before you keep it.

## 11. Formatting

`vendor/bin/pint` before finishing. It is the authority on whitespace, import order, and brace
placement — do not hand-format against it.

## 12. Exceptions are rendered in one place

Every exception an API request raises is turned into a response by the global handler in
`bootstrap/app.php` → `withExceptions()`, and that response uses the **same envelope as §5**:
`{success: false, message, data}`. Clients parse one shape for success and failure alike.

| Exception | Status | `message` |
|-----------|--------|-----------|
| `ValidationException` | 422 | `The given data was invalid.`, with field errors under `errors` |
| `AuthenticationException` | 401 | `Unauthenticated.` |
| `AuthorizationException` → `AccessDeniedHttpException` | 403 | `This action is unauthorized.` |
| `ModelNotFoundException` → `NotFoundHttpException` | 404 | `{Model} not found.` / `Resource not found.` |
| `ThrottleRequestsException` | 429 | `Too many requests.` |
| Any other `HttpExceptionInterface` | its status | its message |
| Anything else | 500 | `Server error.`. Never the real message unless `app.debug` is on |

```php
// bootstrap/app.php
->withExceptions(function (Exceptions $exceptions) {
    $exceptions->shouldRenderJsonWhen(fn (Request $r) => $r->is('api/*') || $r->expectsJson());

    $exceptions->render(function (ValidationException $e, Request $r) {
        return response()->json([
            'success' => false,
            'message' => $e->getMessage(),
            'data'    => null,
            'errors'  => $e->errors(),
        ], 422);
    });

    // ModelNotFoundException arrives here already converted — type-hint the HTTP exception
    $exceptions->render(function (NotFoundHttpException $e, Request $r) {
        $model = $e->getPrevious() instanceof ModelNotFoundException
            ? class_basename($e->getPrevious()->getModel()) . ' not found.'
            : 'Resource not found.';

        return response()->json(['success' => false, 'message' => $model, 'data' => null], 404);
    });

    // …one render() per row of the table above
})
```

- **Laravel converts some exceptions before your callback sees them.** `ModelNotFoundException`
  becomes `NotFoundHttpException` and `AuthorizationException` becomes `AccessDeniedHttpException`.
  A `render()` callback type-hinted on the original class **never fires**, and the response falls
  back to Laravel's default shape with no error. Type-hint the HTTP exception and read
  `getPrevious()` when you need the original.
- **Match the trait.** If `ApiResponse::errorResponse()` uses a different key for field errors
  than `errors`, the handler must use the same one. There is one error shape, not two.
- **Domain errors are exceptions, not early returns.** A business rule that fails in a service
  throws a named exception (`InsufficientStockException`) that either implements `render()` or has
  a row in the handler. The service never builds an HTTP response.
- **Log in the handler, not at the throw site.** `report()` callbacks decide what is logged.
  Don't `Log::error()` and rethrow, or the same failure is logged twice.
