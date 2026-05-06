/**
 * Demo Scenario: Full volunteer call lifecycle with visible browser.
 *
 * Prerequisites:
 *   - Backend running with DEMO_MODE=true
 *   - Frontend dev server running (via `make dev`)
 *   - DB seeded with reference data (scripts/dev-db.sh start)
 *   - Playwright installed: cd frontend && pnpm add -D @playwright/test && pnpm exec playwright install chromium
 *
 * Run:
 *   cd frontend && pnpm exec playwright test e2e/demo-scenario.spec.ts --headed
 *
 * The test uses slowMo and explicit pauses so you can watch the flow in the browser.
 */

import { test, expect, type Page } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:5173";
const PAUSE_MS = 1200;

function pause(ms = PAUSE_MS) {
  return new Promise((r) => setTimeout(r, ms));
}

async function login(page: Page, email: string) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('input[type="email"]');
  await page.fill('input[type="email"]', email);
  await pause(500);
  await page.click('button[type="submit"]');
  // Demo mode auto-redirects through /verify to the app
  await page.waitForURL(/\/(volunteering|$)/, { timeout: 10000 });
  await pause();
}

async function logout(page: Page) {
  // Open avatar menu
  const avatarBtn = page.locator(".avatar-btn");
  await avatarBtn.click();
  await pause(400);
  // Click logout
  await page.click(".drawer-logout");
  await page.waitForURL("**/login");
  await pause();
}

test.use({
  viewport: { width: 1280, height: 900 },
  launchOptions: { slowMo: 150 },
});

test("full flow — admin creates call, volunteers respond, admin closes", async ({
  page,
}) => {
  test.setTimeout(120_000);

  // ===========================================================================
  // STEP 1: Admin (Sarah) logs in
  // ===========================================================================
  await login(page, "sarah@rtaff.org");
  await expect(page.locator("h1")).toBeVisible();
  await pause();

  // ===========================================================================
  // STEP 2: Navigate to Volunteer Calls and create a new call
  // ===========================================================================
  await page.click('a[href="/volunteer-calls"]');
  await page.waitForSelector(".calls-page");
  await pause();

  await page.click("text=New Call");
  await pause(500);

  await page.fill('input[placeholder="Call title"]', "June 2026 Weekend Build");
  await pause(300);
  const notesField = page.locator("textarea");
  await notesField.fill("Two-day build event — Arlington and Falls Church");
  await pause(500);

  await page.click('button:has-text("Create")');
  await page.waitForSelector("text=June 2026 Weekend Build");
  await pause();

  await page.click("text=June 2026 Weekend Build");
  await page.waitForSelector(".call-detail");
  await pause();

  // ===========================================================================
  // STEP 3: Add tasks to the call
  // ===========================================================================
  await page.click("text=Add Task");
  await pause(500);

  await page.fill(
    'input[placeholder="e.g., Roof repair at 123 Main St"]',
    "Kitchen remodel",
  );
  await page.fill('input[type="date"]', "2026-06-13");
  await page.fill(
    'input[placeholder="123 Main St"]',
    "1234 Oak St, Arlington, VA 22201",
  );
  await page.fill('input[placeholder="City"]', "Arlington");
  await pause(500);

  await page.click('button:has-text("Add Task")');
  await page.waitForSelector("text=Kitchen remodel");
  await pause();

  await page.click("text=Add Task");
  await pause(500);

  await page.fill(
    'input[placeholder="e.g., Roof repair at 123 Main St"]',
    "Deck repair",
  );
  await page.fill('input[type="date"]', "2026-06-14");
  await page.fill(
    'input[placeholder="123 Main St"]',
    "5678 Elm Ave, Falls Church, VA 22042",
  );
  await page.fill('input[placeholder="City"]', "Falls Church");
  await pause(500);

  await page.click('button:has-text("Add Task")');
  await page.waitForSelector("text=Deck repair");
  await pause();

  // ===========================================================================
  // STEP 4: Open the call for volunteers
  // ===========================================================================
  await page.click("text=Open for Volunteers");
  await page.waitForSelector('.badge:has-text("open")');
  await pause();

  // ===========================================================================
  // STEP 5: Send invites
  // ===========================================================================
  await page.click("text=Send Volunteer Invites");
  await page.waitForSelector(".result-banner");
  await pause(2000);

  // ===========================================================================
  // STEP 6: Admin logs out
  // ===========================================================================
  await logout(page);

  // ===========================================================================
  // STEP 7: Volunteer Alex logs in and submits availability
  // ===========================================================================
  await login(page, "alex.v@example.com");
  await page.waitForSelector("text=Open Volunteer Calls");
  await pause();

  const checkboxes = page.locator('input[type="checkbox"]');
  const checkboxCount = await checkboxes.count();
  for (let i = 0; i < checkboxCount; i++) {
    await checkboxes.nth(i).check();
    await pause(400);
  }

  await page.click('.toggle-btn:has-text("2")');
  await pause(400);

  await page.click("text=Submit Availability");
  await page.waitForSelector("text=Availability saved!");
  await pause(1500);

  await logout(page);

  // ===========================================================================
  // STEP 8: Volunteer Beth logs in and submits availability for task 1 only
  // ===========================================================================
  await login(page, "beth.h@example.com");
  await page.waitForSelector("text=Open Volunteer Calls");
  await pause();

  const bethCheckboxes = page.locator('input[type="checkbox"]');
  await bethCheckboxes.first().check();
  await pause(400);

  await page.click("text=Submit Availability");
  await page.waitForSelector("text=Availability saved!");
  await pause(1500);

  await logout(page);

  // ===========================================================================
  // STEP 9: Admin logs back in to review and close the call
  // ===========================================================================
  await login(page, "sarah@rtaff.org");
  await pause();

  await page.click('a[href="/volunteer-calls"]');
  await page.waitForSelector(".calls-page");
  await pause();

  await page.click("text=June 2026 Weekend Build");
  await page.waitForSelector(".call-detail");
  await pause();

  await page.click("text=Assignment Dashboard");
  await page.waitForURL(/\/dashboard$/);
  await pause(2000);

  await page.goBack();
  await page.waitForSelector(".call-detail");
  await pause();

  // ===========================================================================
  // STEP 10: Close the call (triggers summary notifications)
  // ===========================================================================
  await page.click("text=Close Call");
  await page.waitForSelector('.badge:has-text("closed")');
  await pause(2000);

  // ===========================================================================
  // STEP 11: Admin logs out, Alex logs in to see final state
  // ===========================================================================
  await logout(page);
  await login(page, "alex.v@example.com");
  await page.waitForSelector("text=Volunteering");
  await pause(3000);
});
