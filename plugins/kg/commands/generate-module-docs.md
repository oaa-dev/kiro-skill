---
name: generate-module-docs
description: Scan project and generate module documentation in docs/knowledge/modules/
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Generate Module Docs

Scan the project and generate per-module documentation using the module-docs skill.

<instructions>

## Execution

1. Read `kg.local.md` (or the legacy `knowledge-garden.local.md`) or `docs/knowledge/schema.yaml` to determine the project stack
2. If neither exists, inform the user: "Run /kg:setup to initialize Knowledge Garden first."
3. If `$ARGUMENTS` is provided, treat it as a specific module name to scan (e.g., `/kg:generate-module-docs User`)
4. If no arguments, scan all modules in the project
5. Execute the module-docs skill with the detected stack and optional module filter
6. Report results with a summary table of generated module docs

## Arguments

- `$ARGUMENTS` (optional): specific module name to scan. If omitted, scans all modules.

</instructions>
