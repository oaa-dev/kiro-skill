---
name: playwright-test
description: Write, run, and analyze Playwright E2E tests. Use when changes need browser-level testing or regression testing.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Playwright Testing Skill

**Purpose:** Write, run, and analyze Playwright end-to-end tests for Laravel + Next.js projects. Handles test scaffolding, execution, failure diagnosis, and optional knowledge capture.

## Overview

This skill covers the full lifecycle of E2E testing with Playwright: detecting what needs testing, discovering project conventions, writing tests with accessible locators, running them, diagnosing failures, and capturing non-trivial learnings into the knowledge base.

**Reference:** See [test-patterns.md](./references/test-patterns.md) for standard patterns covering auth, forms, data tables, modals, toasts, file uploads, and responsive testing.

---

<critical_sequence name="playwright-testing" enforce_order="strict">

## 7-Step Process

<step number="1" required="true">
### Step 1: Detect Test Context

Determine what needs testing:

- If `$ARGUMENTS` is provided, use it as the test target (feature name, route, or file path)
- If no arguments, run `git diff --name-only` to identify recently changed files

**Classify the test scope:**

| Changed files | Scope | Focus |
|---------------|-------|-------|
| Only `app/` or `routes/` (Laravel) | API | Test API endpoints via `request.get/post/etc` |
| Only `src/` or `app/` (Next.js) | E2E | Test UI interactions in the browser |
| Both backend + frontend | Full-stack | Test user flows end-to-end through the UI |

If the scope is unclear, ask:

```
What should I test?

1. API endpoints -- test backend responses directly
2. UI interactions -- test browser behavior end-to-end
3. Full user flow -- test a complete feature across frontend and backend
```

Wait for response before proceeding.
</step>

<step number="2" required="true" depends_on="1">
### Step 2: Check Playwright Setup

Verify Playwright is installed and configured:

1. Check for `@playwright/test` in `package.json`:
   ```
   Grep: pattern="@playwright/test" glob="package.json" output_mode=content
   ```

2. Check for config file:
   ```
   Glob: pattern="playwright.config.{ts,js,mjs}"
   ```

3. Check for test directory:
   ```
   Glob: pattern="{e2e,tests/e2e,test/e2e}/**/*.spec.ts" head_limit=1
   ```

**If Playwright is not installed:**

```
Playwright is not set up in this project. Want me to install it?

1. Install Playwright (recommended) -- runs `npm init playwright@latest`
2. Skip -- I'll set it up myself
```

If user chooses install, run:
```bash
npm init playwright@latest -- --quiet
```

**If installed but no config found**, check for non-standard config locations before reporting missing.
</step>

<step number="3" required="true" depends_on="2">
### Step 3: Discover Existing Tests

Scan the project to learn testing conventions:

1. **Find existing test files:**
   ```
   Glob: pattern="**/*.spec.ts"
   ```

2. **Read up to 5 test files** to extract project conventions:
   - Import patterns (custom fixtures, page objects, helpers)
   - Auth setup approach (storage state, login helper, API tokens)
   - Naming conventions (describe/test labels, file naming)
   - Common utilities or helpers used
   - Base URL configuration
   - Assertion patterns

3. **Check for page objects or fixtures:**
   ```
   Glob: pattern="{e2e,tests}/**/{fixtures,pages,helpers,utils}/*.ts"
   ```

4. **Check knowledge base** for past test-related solutions (if knowledge base exists):
   ```
   Grep: pattern="playwright|e2e|test" path=docs/knowledge/solutions/ -i=true output_mode=files_with_matches
   ```
   If matches found, read up to 3 most relevant files (first 30 lines each) to avoid known pitfalls.

**Capture conventions as a mental model** -- use these when writing tests in Step 4 so new tests match the project's existing style.
</step>

<step number="4" required="true" depends_on="3" blocking="true">
### Step 4: Write or Update Tests

<validation_gate name="test-plan-approval" blocking="true">

**Before writing any test code**, present a test plan to the user:

```
## Test Plan

**Target:** [feature/route/component being tested]
**Scope:** [API / E2E / Full-stack]
**File:** [proposed file path, e.g. e2e/merchants/create-merchant.spec.ts]

**Test cases:**
1. [test description] -- [what it verifies]
2. [test description] -- [what it verifies]
3. [test description] -- [what it verifies]
...

**Approach:**
- Auth: [how authentication is handled]
- Data: [test data strategy -- API seeding, fixtures, etc.]
- Cleanup: [if any teardown needed]

Proceed with this plan?
```

Wait for user approval. Adjust if they request changes.

</validation_gate>

**Writing guidelines:**

- **Accessible locators first:** Prefer `getByRole`, `getByLabel`, `getByText`, `getByPlaceholder` over CSS selectors or test IDs
- **Follow project conventions** discovered in Step 3 (imports, naming, helpers)
- **One assertion per concept** -- each `test()` block should verify one behavior
- **Descriptive test names** -- should read like a specification: `test('should show validation error when email is empty')`
- **Avoid flaky patterns:**
  - Use `waitFor` or assertions with auto-retry instead of arbitrary `waitForTimeout`
  - Use `toBeVisible()` before interacting with elements
  - Avoid hard-coded wait times
- **Use test.describe** for grouping related tests
- **Handle auth** using the project's established pattern (storage state, beforeAll login, etc.)

**For API tests:**
```typescript
test('should create a merchant', async ({ request }) => {
  const response = await request.post('/api/merchants', { data: { name: 'Test' } });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.data.name).toBe('Test');
});
```

**For E2E tests:**
```typescript
test('should submit the create merchant form', async ({ page }) => {
  await page.goto('/merchants/create');
  await page.getByLabel('Name').fill('Test Merchant');
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText('Merchant created')).toBeVisible();
});
```
</step>

<step number="5" required="true" depends_on="4">
### Step 5: Run Tests

**Before running, verify the dev server is accessible:**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "not running"
```

If the dev server is not running, inform the user:

```
The dev server doesn't appear to be running at the expected URL.
Please start it before I run the tests, or tell me the correct URL.
```

Wait for confirmation before proceeding.

**Run the tests:**

For a specific file:
```bash
npx playwright test [file] --reporter=list
```

For all tests in a directory:
```bash
npx playwright test [directory] --reporter=list
```

**If tests need a specific project/browser:**
```bash
npx playwright test [file] --project=chromium --reporter=list
```

Capture the full output for analysis in Step 6.
</step>

<step number="6" required="true" depends_on="5">
### Step 6: Analyze Results and Fix

**If all tests pass:**

```
All [N] tests passed.

[Brief summary of what was verified]
```

Done -- skip to Step 7.

**If tests fail:**

1. **Parse the failure output** -- extract:
   - Which tests failed
   - Error messages and stack traces
   - Expected vs actual values
   - Screenshot/trace paths if generated

2. **Diagnose each failure** -- classify as:
   - **Locator issue** -- element not found or wrong locator
   - **Timing issue** -- race condition, element not ready
   - **Data issue** -- test data not set up correctly
   - **Application bug** -- actual defect in the code under test
   - **Environment issue** -- server not running, wrong URL, missing setup

3. **Present findings:**

   ```
   ## Test Results: [N] passed, [M] failed

   ### Failures:

   1. **[test name]**
      - Error: [error message]
      - Cause: [diagnosis]
      - Fix: [suggested fix]

   2. **[test name]**
      - Error: [error message]
      - Cause: [diagnosis]
      - Fix: [suggested fix]

   Want me to apply fixes and re-run?
   1. Fix all and re-run (recommended)
   2. Fix specific tests -- [list which]
   3. Show me the fixes first
   4. Skip -- these are application bugs to fix separately
   ```

4. **If user approves fixes**, apply them and re-run (loop back to Step 5). Limit to 3 retry cycles to avoid infinite loops.

5. **If failures are application bugs**, clearly separate them from test issues:
   ```
   These failures indicate application bugs (not test issues):
   - [bug description and affected test]

   The tests are correctly detecting these issues.
   ```
</step>

<step number="7" required="false" depends_on="6">
### Step 7: Knowledge Capture (Optional)

If non-trivial issues were encountered during testing:

- Flaky test patterns that needed workarounds
- Environment setup gotchas
- Authentication flow complexities
- Framework-specific quirks (Next.js hydration, Laravel session handling, etc.)

**Recommend capturing the learning:**

```
Some non-trivial testing issues came up during this session:
- [brief description of issue and solution]

Want to document this for future reference?
1. Capture with /kg:compound (recommended)
2. Skip -- not worth documenting
```

This keeps the knowledge base growing with real testing insights.
</step>

</critical_sequence>

---

## Error Handling

**Playwright not installed:**
- Offer to install, or direct user to set it up manually
- Do not assume installation -- always ask first

**Dev server not running:**
- Do not attempt to start the server yourself
- Inform the user and wait for them to start it

**Config issues (baseURL, auth, etc.):**
- Read `playwright.config.*` to understand the setup
- Suggest config fixes if the test environment doesn't match

**Test timeouts:**
- Check if the default timeout is too low for the operation
- Suggest increasing test-specific timeouts rather than global ones

**Flaky tests:**
- Never mask flakiness with retries or arbitrary waits
- Diagnose the root cause (race condition, data dependency, animation timing)
- Fix the underlying issue

---

## Quality Guidelines

**Good E2E tests have:**
- Accessible locators (`getByRole`, `getByLabel`, `getByText`)
- Clear test names that read like specifications
- One logical assertion per test
- Proper setup and teardown
- No hard-coded wait times
- Deterministic test data

**Avoid:**
- CSS selectors when accessible locators work
- `page.waitForTimeout()` -- use assertions with auto-retry instead
- Testing implementation details (internal state, CSS classes)
- Overly broad tests that verify too many things at once
- Tests that depend on execution order
- Ignoring the project's existing test conventions
