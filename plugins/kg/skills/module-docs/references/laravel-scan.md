# Laravel Scanning Strategy

Reference-tracing approach for Laravel projects. Start from the model, then find everything that references it.

## Step 1: Identify the Module Anchor

Scan `app/Models/` for model files. Each model = one module.

Read the model file to extract:
- Class name
- Table name (from `$table` property or convention: snake_case plural of class name)
- Relationships (methods returning `hasMany`, `belongsTo`, `hasOne`, `belongsToMany`, `morphTo`, `morphMany`, etc.)
- Casts (from `$casts` property or `casts()` method)
- Traits (from `use` statements inside the class body)
- Scopes (methods prefixed with `scope`)
- Fillable fields (from `$fillable` property)

## Step 2: Grep the Entire Project for the Model Class Name

Run these Grep calls in parallel:

```
Grep: pattern="use.*Models\\{ModelName}|{ModelName}::|new {ModelName}|{ModelName} \$|@param.*{ModelName}|@return.*{ModelName}" path=app/ -i=false
Grep: pattern="{ModelName}" path=database/ -i=false
Grep: pattern="{ModelName}" path=tests/ -i=false
Grep: pattern="{ModelName}" path=routes/ -i=false
```

This catches everything: controllers, services, DTOs, enums, actions, repositories, observers, events, jobs, notifications, mail, casts, form requests, resources, policies -- and any custom file types the project uses (e.g., `app/Builders/`, `app/QueryFilters/`, `app/ViewModels/`).

## Step 3: Read Each Matched File's First 30 Lines

For each matched file, read the first 30 lines to determine its type:

```
Read: [file_path] with limit:30
```

Extract:
- Class name
- Namespace
- Extends/implements
- Use statements

Auto-categorize by namespace path:
- `App\Http\Controllers\*` -> Controller
- `App\Services\*` -> Service
- `App\Repositories\*` -> Repository
- `App\Data\*` or `App\DTOs\*` -> DTO
- `App\Enums\*` -> Enum
- `App\Http\Requests\*` -> FormRequest
- `App\Http\Resources\*` -> Resource
- `App\Policies\*` -> Policy
- `App\Events\*` -> Event
- `App\Listeners\*` -> Listener
- `App\Observers\*` -> Observer
- `App\Jobs\*` -> Job
- `App\Notifications\*` -> Notification
- `App\Mail\*` -> Mail
- `App\Actions\*` -> Action
- `App\Casts\*` -> Cast
- Other namespaces -> use the last segment of the namespace as category

## Step 4: Trace Migration by Table Name

```
Grep: pattern="create_{snake_case_plural}_table|Schema::.*'{table_name}'" path=database/migrations/
```

Also check for factory and seeder:
```
Glob: pattern="database/factories/{ModelName}Factory.php"
Glob: pattern="database/seeders/{ModelName}Seeder.php"
```

## Step 5: Trace Routes by Controller

For each controller found in Step 3:
```
Grep: pattern="{ControllerName}|{model_name}" path=routes/
```

Read matched route files and extract route definitions (method, URI, action).

## Step 6: Write the Module Doc

Group all discovered files by their auto-detected category. Create sections dynamically based on what was found:

```markdown
# {ModelName} Module

## Model
- **Path**: app/Models/{ModelName}.php
- **Table**: {table_name}
- **Fillable**: [extracted fields]
- **Casts**: [extracted casts]
- **Relationships**: [extracted relationships]
- **Traits**: [extracted traits]
- **Scopes**: [extracted scopes]

## Connected Files
| Category | File | Notes |
|----------|------|-------|
| Controller | app/Http/Controllers/{...}.php | index, store, show, update, destroy |
| DTO | app/Data/{...}Data.php | properties: name, email, ... |
| Enum | app/Enums/{...}Status.php | Active, Inactive, Pending |
| FormRequest | app/Http/Requests/{...}Request.php | validation rules |
| Resource | app/Http/Resources/{...}Resource.php | API response shape |
| Service | app/Services/{...}Service.php | business logic |
| ... | ... | ... |

## Routes
| Method | URI | Action |
|--------|-----|--------|
| GET | /api/{models} | index |
| POST | /api/{models} | store |
| ... | ... | ... |

## Database
| Type | File |
|------|------|
| Migration | database/migrations/xxxx_create_{table}_table.php |
| Factory | database/factories/{ModelName}Factory.php |
| Seeder | database/seeders/{ModelName}Seeder.php |

## Tests
| Type | File |
|------|------|
| Feature | tests/Feature/{...}Test.php |
| Unit | tests/Unit/{...}Test.php |
```

The table format naturally accommodates any file type. If a project has `app/Builders/`, `app/Pipelines/`, or `app/ViewModels/`, they appear in "Connected Files" automatically because grep found the model reference there.
