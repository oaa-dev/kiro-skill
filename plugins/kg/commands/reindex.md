---
name: reindex
description: Regenerate the knowledge index from all solution files
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
---

# Reindex Knowledge Base

Regenerate `docs/knowledge/index.md` by scanning all solution files and extracting their frontmatter into a compact lookup table.

<instructions>

Execute the full knowledge-index skill workflow:

1. Verify `docs/knowledge/solutions/` exists. If not: "Run /kg:setup to initialize Knowledge Garden first."
2. Glob all solution files in `docs/knowledge/solutions/**/*.md`
3. Read `docs/knowledge/patterns/critical-patterns.md` and extract pattern names + file references
4. Scan module docs: Glob `docs/knowledge/modules/*.md`. For each, read first 40 lines to extract module name, file count, key components, and relationships. Skip if none found.
5. For each solution file, read the first 20 lines to extract YAML frontmatter (parallel batches of 10)
6. Scan saved answers: Glob `docs/knowledge/answers/*.md`. For each, read first 12 lines to extract question, modules, tags, date. Skip if none found.
7. Write `docs/knowledge/index.md` with the standard index format (header with counts, Critical Patterns section, Modules table, Solutions table sorted by date descending, Answers table if any)
8. Report: solutions indexed, skipped, critical patterns count, modules indexed, answers indexed

See the knowledge-index skill for the full index file format specification.

</instructions>
