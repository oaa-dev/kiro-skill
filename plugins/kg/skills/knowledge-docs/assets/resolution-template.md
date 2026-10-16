<!--
Every frontmatter value below is quoted so this template parses as valid YAML even before it is
filled in. Keep the quotes when you substitute real values -- a file with malformed frontmatter is
silently skipped by the knowledge-index skill and becomes invisible to every lookup.
-->
---
module: "<Module name, or System for system-wide>"
date: "<YYYY-MM-DD>"
problem_type: "<from schema.yaml enums>"
component: "<from schema.yaml enums>"
symptoms:
  - "<Observable symptom 1 - specific error message or behavior>"
  - "<Observable symptom 2 - what the user actually saw/experienced>"
root_cause: "<from schema.yaml enums>"
framework_version: "<e.g. Laravel 11.x or Next.js 15.1>"
resolution_type: "<code_fix|migration|config_change|test_fix|dependency_update|environment_setup>"
severity: "<critical|high|medium|low>"
tags:
  - "<keyword1>"
  - "<keyword2>"
---

# Troubleshooting: [Clear Problem Title]

## Problem
[1-2 sentence clear description of the issue and what the user experienced]

## Environment
- Module: [Name or "System-wide"]
- Framework Version: [e.g., Laravel 11.x, Next.js 15.1]
- Affected Component: [e.g., "User model", "Dashboard page", "Order service"]
- Date: [YYYY-MM-DD when this was solved]

## Symptoms
- [Observable symptom 1 - what the user saw/experienced]
- [Observable symptom 2 - error messages, visual issues, unexpected behavior]
- [Continue as needed - be specific]

## What Didn't Work

**Attempted Solution 1:** [Description of what was tried]
- **Why it failed:** [Technical reason this didn't solve the problem]

**Attempted Solution 2:** [Description of second attempt]
- **Why it failed:** [Technical reason]

[Continue for all significant attempts that didn't work]

[If nothing else was attempted first, write:]
**Direct solution:** The problem was identified and fixed on the first attempt.

## Solution

[The actual fix that worked - provide specific details]

**Code changes** (if applicable):
```
# Before (broken):
[Show the problematic code]

# After (fixed):
[Show the corrected code with explanation]
```

**Configuration changes** (if applicable):
```
[Show what was changed]
```

**Commands run** (if applicable):
```bash
[Steps taken to fix]
```

## Why This Works

[Technical explanation of:]
1. What was the ROOT CAUSE of the problem?
2. Why does the solution address this root cause?
3. What was the underlying issue?

[Be detailed enough that future developers understand the "why", not just the "what"]

## Prevention

[How to avoid this problem in future development:]
- [Specific coding practice, check, or pattern to follow]
- [What to watch out for]
- [How to catch this early]

## Related Issues

[If any similar problems exist in docs/knowledge/solutions/, link to them:]
- See also: [another-related-issue.md](../category/another-related-issue.md)

[If no related issues, write:]
No related issues documented yet.
