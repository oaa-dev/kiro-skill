---
name: kg-generate-module-docs
description: "Scan project and generate module documentation in docs/knowledge/modules/"
license: MIT
---

# Generate Module Docs

Scan the project and generate per-module documentation using the `kg-module-docs` skill.

<instructions>

## Execution

1. Read `kg.local.md` (or the legacy `knowledge-garden.local.md`) or `docs/knowledge/schema.yaml` to determine the project stack
2. If neither exists, inform the user: "Run /kg-setup to initialize Knowledge Garden first."
3. If the input is provided, treat it as a specific module name to scan (e.g., `/kg-generate-module-docs User`)
4. If no arguments, scan all modules in the project
5. Execute the `kg-module-docs` skill with the detected stack and optional module filter
6. Report results with a summary table of generated module docs

## Input

The input is the text typed after the slash command, or the user's request when Kiro loads this skill on its own.

- **Input** (optional): specific module name to scan. If omitted, scans all modules.

</instructions>
