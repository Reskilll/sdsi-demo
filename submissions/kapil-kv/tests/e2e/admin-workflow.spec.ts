import { test, expect } from "@playwright/test";

test.describe("Admin SLA Tracker Workflow", () => {
  test("should redirect unauthenticated users to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("should login successfully with valid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || "ChangeMe123!");
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
  });

  test("should show validation errors on empty login", async ({ page }) => {
    await page.goto("/login");
    await page.click('button[type="submit"]');
    // Should still be on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test("should show dashboard with summary cards after login", async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.fill('input[type="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || "ChangeMe123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });

    // Verify dashboard elements
    await expect(page.locator("text=Total Tickets")).toBeVisible();
  });

  test("should navigate to ticket list page", async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.fill('input[type="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || "ChangeMe123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });

    // Navigate to tickets
    await page.click("text=Tickets");
    await expect(page).toHaveURL(/\/tickets/);
  });

  test("should show SLA policies page", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || "ChangeMe123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });

    await page.click("text=SLA Policies");
    await expect(page.locator("text=SLA Policies")).toBeVisible();
  });

  test("should show reports page with export button", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || "ChangeMe123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });

    await page.click("text=Reports");
    await expect(page.locator("text=Export CSV")).toBeVisible();
  });

  test("should logout and redirect to login", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || "ChangeMe123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });

    // Logout
    await page.click("text=Logout");
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test("should create a new ticket", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || "ChangeMe123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });

    await page.click("text=Tickets");
    await page.click("text=+ New Ticket");

    await expect(page).toHaveURL(/\/tickets\/new/);

    // Fill form
    await page.fill('input[name="title"]', "E2E Test: Network Issue");
    await page.selectOption('select[name="priority"]', "P2");
    await page.click('button[type="submit"]');

    // Should redirect to ticket detail
    await expect(page).toHaveURL(/\/tickets\//, { timeout: 10000 });
  });
});