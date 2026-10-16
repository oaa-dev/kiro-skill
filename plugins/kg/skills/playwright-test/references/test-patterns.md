# Playwright Test Patterns for Laravel + Next.js

Standard patterns for common testing scenarios. Use these as starting points and adapt to project conventions.

---

## Authentication Setup

### Storage State (Recommended)

Save auth state once, reuse across tests:

```typescript
// e2e/auth.setup.ts
import { test as setup, expect } from '@playwright/test';

const authFile = 'e2e/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL('/dashboard');
  await page.context().storageState({ path: authFile });
});
```

```typescript
// playwright.config.ts (relevant section)
export default defineConfig({
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
});
```

### API Token Auth (Laravel Sanctum)

```typescript
// e2e/fixtures.ts
import { test as base } from '@playwright/test';

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // Set the auth cookie/token via API
    const response = await page.request.post('/api/login', {
      data: { email: 'test@example.com', password: 'password' },
    });
    const { token } = await response.json();
    await page.setExtraHTTPHeaders({ Authorization: `Bearer ${token}` });
    await use(page);
  },
});
```

---

## API Testing

### CRUD Endpoint Tests

```typescript
import { test, expect } from '@playwright/test';

test.describe('Merchants API', () => {
  let merchantId: number;

  test('POST /api/merchants -- creates a merchant', async ({ request }) => {
    const response = await request.post('/api/merchants', {
      data: { name: 'Test Merchant', email: 'merchant@test.com' },
    });
    expect(response.status()).toBe(201);
    const body = await response.json();
    expect(body.data).toMatchObject({ name: 'Test Merchant' });
    merchantId = body.data.id;
  });

  test('GET /api/merchants/:id -- returns the merchant', async ({ request }) => {
    const response = await request.get(`/api/merchants/${merchantId}`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.data.name).toBe('Test Merchant');
  });

  test('PUT /api/merchants/:id -- updates the merchant', async ({ request }) => {
    const response = await request.put(`/api/merchants/${merchantId}`, {
      data: { name: 'Updated Merchant' },
    });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.data.name).toBe('Updated Merchant');
  });

  test('DELETE /api/merchants/:id -- deletes the merchant', async ({ request }) => {
    const response = await request.delete(`/api/merchants/${merchantId}`);
    expect(response.status()).toBe(204);
  });
});
```

### Validation Error Tests

```typescript
test('POST /api/merchants -- returns validation errors', async ({ request }) => {
  const response = await request.post('/api/merchants', {
    data: {},
  });
  expect(response.status()).toBe(422);
  const body = await response.json();
  expect(body.errors).toHaveProperty('name');
});
```

---

## Form Interactions

### Basic Form Submission

```typescript
test('should submit the create form', async ({ page }) => {
  await page.goto('/merchants/create');

  await page.getByLabel('Name').fill('New Merchant');
  await page.getByLabel('Email').fill('new@merchant.com');
  await page.getByLabel('Phone').fill('+1234567890');

  await page.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText('Merchant created successfully')).toBeVisible();
});
```

### Select / Dropdown

```typescript
// Native select
await page.getByLabel('Country').selectOption('US');

// Custom combobox (Headless UI, Radix, etc.)
await page.getByRole('combobox', { name: 'Country' }).click();
await page.getByRole('option', { name: 'United States' }).click();
```

### Checkbox and Radio

```typescript
await page.getByLabel('I agree to the terms').check();
expect(await page.getByLabel('I agree to the terms').isChecked()).toBeTruthy();

await page.getByLabel('Monthly').check(); // radio
```

### Form Validation

```typescript
test('should show validation errors for empty required fields', async ({ page }) => {
  await page.goto('/merchants/create');
  await page.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText('Name is required')).toBeVisible();
  await expect(page.getByText('Email is required')).toBeVisible();
});
```

---

## Navigation and Routing

### Page Navigation

```typescript
test('should navigate to merchant details', async ({ page }) => {
  await page.goto('/merchants');
  await page.getByRole('link', { name: 'View Details' }).first().click();
  await expect(page).toHaveURL(/\/merchants\/\d+/);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
});
```

### Breadcrumbs

```typescript
test('should show correct breadcrumb trail', async ({ page }) => {
  await page.goto('/merchants/1/edit');
  const breadcrumb = page.getByRole('navigation', { name: 'Breadcrumb' });
  await expect(breadcrumb.getByRole('link', { name: 'Merchants' })).toBeVisible();
  await expect(breadcrumb.getByText('Edit')).toBeVisible();
});
```

---

## Data Tables

### Table Content

```typescript
test('should display merchants in the table', async ({ page }) => {
  await page.goto('/merchants');

  const table = page.getByRole('table');
  await expect(table).toBeVisible();

  // Check headers
  await expect(table.getByRole('columnheader', { name: 'Name' })).toBeVisible();
  await expect(table.getByRole('columnheader', { name: 'Email' })).toBeVisible();

  // Check at least one row exists
  const rows = table.getByRole('row');
  await expect(rows).toHaveCount(await rows.count()); // at least header + 1 data row
});
```

### Sorting

```typescript
test('should sort by name when column header is clicked', async ({ page }) => {
  await page.goto('/merchants');

  await page.getByRole('columnheader', { name: 'Name' }).click();

  // Verify sort indicator
  await expect(page.getByRole('columnheader', { name: 'Name' })).toHaveAttribute(
    'aria-sort',
    'ascending'
  );
});
```

### Pagination

```typescript
test('should paginate through results', async ({ page }) => {
  await page.goto('/merchants');

  const nextButton = page.getByRole('button', { name: 'Next' });
  await expect(nextButton).toBeEnabled();
  await nextButton.click();

  await expect(page).toHaveURL(/page=2/);
});
```

### Search / Filter

```typescript
test('should filter merchants by search term', async ({ page }) => {
  await page.goto('/merchants');

  await page.getByPlaceholder('Search merchants').fill('Acme');
  // Wait for filtered results
  await expect(page.getByRole('cell', { name: /Acme/ })).toBeVisible();
});
```

---

## Modals and Dialogs

### Confirmation Dialog

```typescript
test('should show confirmation before deleting', async ({ page }) => {
  await page.goto('/merchants');

  await page.getByRole('button', { name: 'Delete' }).first().click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('Are you sure')).toBeVisible();

  await dialog.getByRole('button', { name: 'Confirm' }).click();
  await expect(dialog).not.toBeVisible();
});
```

### Modal Form

```typescript
test('should open and submit a modal form', async ({ page }) => {
  await page.goto('/merchants');

  await page.getByRole('button', { name: 'Add Merchant' }).click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();

  await dialog.getByLabel('Name').fill('Modal Merchant');
  await dialog.getByRole('button', { name: 'Save' }).click();

  await expect(dialog).not.toBeVisible();
  await expect(page.getByText('Modal Merchant')).toBeVisible();
});
```

---

## Toast / Flash Messages

```typescript
test('should show success toast after saving', async ({ page }) => {
  await page.goto('/merchants/create');
  await page.getByLabel('Name').fill('Toast Test');
  await page.getByRole('button', { name: 'Save' }).click();

  // Toast messages typically use role="status" or role="alert"
  await expect(page.getByRole('status')).toContainText('saved');
});
```

---

## File Upload

```typescript
test('should upload a document', async ({ page }) => {
  await page.goto('/merchants/1/documents');

  const fileInput = page.getByLabel('Upload document');
  await fileInput.setInputFiles('e2e/fixtures/sample.pdf');

  await page.getByRole('button', { name: 'Upload' }).click();
  await expect(page.getByText('sample.pdf')).toBeVisible();
});
```

### Drag and Drop Upload

```typescript
test('should upload via drag and drop', async ({ page }) => {
  await page.goto('/merchants/1/documents');

  const dropZone = page.getByText('Drop files here');
  const dataTransfer = await page.evaluateHandle(() => new DataTransfer());

  await dropZone.dispatchEvent('drop', { dataTransfer });
});
```

---

## Responsive Testing

### Viewport-Based Tests

```typescript
test.describe('mobile viewport', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should show mobile navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Menu' })).toBeVisible();
    await expect(page.getByRole('navigation')).not.toBeVisible();

    await page.getByRole('button', { name: 'Menu' }).click();
    await expect(page.getByRole('navigation')).toBeVisible();
  });
});

test.describe('desktop viewport', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('should show sidebar navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('navigation')).toBeVisible();
  });
});
```

---

## Laravel-Specific Patterns

### Database Seeding Before Tests

```typescript
test.beforeAll(async ({ request }) => {
  // Call a test-only artisan endpoint or API
  await request.post('/api/test/seed', {
    data: { seeder: 'MerchantSeeder' },
  });
});
```

### CSRF Token Handling

```typescript
// Usually handled automatically if using session-based auth.
// For API tests, ensure your test uses Sanctum or token-based auth
// which doesn't require CSRF.
```

### Testing Laravel Validation Messages

```typescript
test('should display Laravel validation messages', async ({ page }) => {
  await page.goto('/merchants/create');
  await page.getByRole('button', { name: 'Save' }).click();

  // Laravel validation messages appear in the response
  await expect(page.getByText('The name field is required')).toBeVisible();
});
```

---

## Next.js-Specific Patterns

### Waiting for Hydration

```typescript
// Playwright's auto-waiting usually handles this.
// If you hit hydration issues, wait for a specific interactive element:
test('should interact after hydration', async ({ page }) => {
  await page.goto('/dashboard');
  // Wait for an interactive element that only works post-hydration
  const button = page.getByRole('button', { name: 'Refresh' });
  await expect(button).toBeEnabled();
  await button.click();
});
```

### Testing Server Components vs Client Components

```typescript
// Server components render immediately -- test content directly
test('should display server-rendered data', async ({ page }) => {
  await page.goto('/merchants');
  // Content from server components is available immediately
  await expect(page.getByRole('heading', { name: 'Merchants' })).toBeVisible();
});

// Client components may need interaction
test('should toggle client-side filter', async ({ page }) => {
  await page.goto('/merchants');
  await page.getByRole('button', { name: 'Active Only' }).click();
  await expect(page.getByText('Showing active merchants')).toBeVisible();
});
```

### API Route Testing

```typescript
test('should call Next.js API route', async ({ request }) => {
  const response = await request.get('/api/health');
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe('ok');
});
```
