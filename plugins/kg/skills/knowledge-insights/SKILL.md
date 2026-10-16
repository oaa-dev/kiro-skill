---
name: knowledge-insights
description: Analyze knowledge base to surface patterns and metrics. Use to understand recurring problems, hotspot modules, and knowledge trends.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# Knowledge Insights

**Purpose:** Scan all documented solutions and aggregate metrics to surface patterns, hotspots, and trends in the knowledge base.

## Overview

This skill reads YAML frontmatter from all files in `docs/knowledge/solutions/` and presents aggregated insights as formatted markdown tables.

---

## Process

### Step 1: Check for Knowledge Index

Try to read `docs/knowledge/index.md`.

**If found and not empty (Solutions > 0):** The index already contains Module, Type, Component, Severity, Date, and Tags for every solution. Use it directly -- skip Step 2 entirely and proceed to Step 3 with the index data.

**If found but empty (Solutions: 0):** Report: "No solutions documented yet. Use the knowledge-docs skill after solving problems to build your knowledge base."

**If not found:** Fall back to the legacy approach (Steps 1b and 2).

<details><summary>Step 1b: Legacy fallback (only if no index)</summary>

```
Glob: pattern="docs/knowledge/solutions/**/*.md"
```

If no files found, report: "No solutions documented yet. Use the knowledge-docs skill after solving problems to build your knowledge base."
</details>

### Step 2: Extract Frontmatter From Each File (skip if index used)

This step is only needed when falling back to the legacy approach (no index).

For each solution file, read the first 20 lines to extract YAML frontmatter fields:
- `module`
- `problem_type`
- `component`
- `root_cause`
- `severity`
- `date`
- `tags`

Use parallel Read calls in batches of 10 for efficiency.

**Note:** When using the index, parse the Solutions table rows to extract these fields instead. The only field missing from the index is `root_cause` -- for root cause aggregation, do a targeted Grep:
```
Grep: pattern="root_cause:" path=docs/knowledge/solutions/ output_mode=content -n=true
```

### Step 3: Aggregate Metrics

Compute the following from extracted frontmatter:

**Top Problem Types:** Count occurrences of each `problem_type` value, sorted descending.

**Most Affected Modules:** Count occurrences of each `module` value, sorted descending.

**Common Root Causes:** Count occurrences of each `root_cause` value, sorted descending.

**Severity Distribution:** Count occurrences of each `severity` value.

**Monthly Trend:** Group by `date` (year-month), count per month.

**Hotspot Modules:** Modules with 3 or more documented issues.

**Top Tags:** Count tag frequency across all `tags` arrays, show top 10.

### Step 4: Present Results

Format as markdown:

```markdown
## Knowledge Base Insights

**Total solutions documented:** [N]
**Date range:** [earliest date] to [latest date]

### Problem Type Distribution
| Problem Type | Count | % |
|-------------|-------|---|
| runtime_error | 12 | 30% |
| performance_issue | 8 | 20% |
| ... | ... | ... |

### Most Affected Modules
| Module | Issues | Severity Breakdown |
|--------|--------|--------------------|
| User | 8 | 2 critical, 3 high, 3 medium |
| Order | 5 | 1 critical, 2 high, 2 low |
| ... | ... | ... |

### Common Root Causes
| Root Cause | Count |
|-----------|-------|
| missing_eager_load | 6 |
| logic_error | 5 |
| ... | ... |

### Severity Distribution
| Severity | Count | % |
|----------|-------|---|
| critical | 3 | 7% |
| high | 15 | 38% |
| medium | 18 | 45% |
| low | 4 | 10% |

### Monthly Trend
| Month | Issues Documented |
|-------|-------------------|
| 2026-02 | 5 |
| 2026-01 | 8 |
| ... | ... |

### Hotspot Modules (3+ issues)
| Module | Total Issues | Most Common Problem | Most Common Root Cause |
|--------|-------------|--------------------|-----------------------|
| User | 8 | runtime_error | missing_eager_load |
| ... | ... | ... | ... |

### Top Tags
| Tag | Occurrences |
|-----|-------------|
| performance | 12 |
| database | 9 |
| ... | ... |

### Recommendations
- [Based on the data, suggest focus areas]
- [e.g., "Consider adding eager loading guidelines to prevent the recurring missing_eager_load issues in User and Order modules"]
- [e.g., "The User module is a hotspot with 8 issues -- consider a focused refactoring effort"]
```

---

## Error Handling

**No solutions directory:**
- Suggest running setup: "Run /kg:setup to initialize Knowledge Garden first."

**No solution files:**
- Report that the knowledge base is empty and suggest using knowledge-docs after solving problems.

**Malformed frontmatter:**
- Skip files with invalid/missing frontmatter
- Report count of skipped files at the end
