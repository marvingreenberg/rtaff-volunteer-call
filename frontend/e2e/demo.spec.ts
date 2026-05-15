/**
 * Demo Scenario — follows Demo.md.
 *
 * Prerequisites (one shell):
 *   make dev-db-reset           # fresh seed with real RT-AFF contacts
 *   make dev                    # backend + frontend + Mailpit
 * Then in another shell:
 *   cd frontend && pnpm exec playwright install chromium    # one-time
 *   cd frontend && pnpm exec playwright test e2e/demo.spec.ts
 *
 * Output: test-results/demo/<run>/video.webm
 *
 * The spec uses the real magic-link flow (not DEMO_MODE) so the login
 * emails actually arrive in Mailpit and the demo can showcase them.
 */

import { request, test } from "@playwright/test";
import {
  BASE_URL,
  clearNarration,
  extractAppLink,
  fetchMessageHtml,
  hideMailpitPanel,
  installNarrator,
  loginViaMagicLink,
  logout,
  narrate,
  runBulk,
  showMailpitInbox,
  showMailpitPanel,
  sleep,
  waitForMessage,
} from "./demo-helpers";

const DON_GMAIL_ALIAS = "donryanemail@gmail.com";
const VICK = "vgfisher@gmail.com";
const BRYAN = "bcobb2014@gmail.com";

test("RT-AFF volunteer-call demo", async ({ page }) => {
  test.setTimeout(300_000);
  const api = await request.newContext();

  // Register the narration overlay BEFORE any navigation so it re-attaches
  // automatically on every page load.
  await installNarrator(page);

  // ===========================================================================
  // STEP 1: Admin Don Ryan logs in — entering his *gmail alias*. The magic
  // link arrives at the gmail address; Mailpit panel proves it.
  // ===========================================================================
  await page.goto(`${BASE_URL}/login`);
  await narrate(
    page,
    "Don Ryan is an admin. He logs in with his personal gmail — an email alias on his RT-AFF account.",
    2400,
  );
  await loginViaMagicLink(page, api, DON_GMAIL_ALIAS);
  await narrate(
    page,
    "Logged in. Notification emails still go to his @rebuildingtogether-aff.org address.",
    2200,
  );

  // ===========================================================================
  // STEP 2: Create a new call
  // ===========================================================================
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await page.waitForSelector(".calls-page");
  await narrate(page, "Don creates a new volunteer call.", 1500);
  await page.click("text=New Call");
  await sleep(600);

  const callTitle = `Weekend Build — Demo ${new Date().toISOString().slice(0, 10)}`;
  await page.fill('input[placeholder*="Spring NRD"]', callTitle);
  await page.fill(
    "textarea",
    "Two-day weekend build across Arlington and Falls Church",
  );
  await sleep(500);
  await page.click('button[type="submit"]:has-text("Create")');
  await page.waitForSelector(`text=${callTitle}`);
  await sleep(500);

  // ===========================================================================
  // STEP 3: Drill into the call and add two tasks manually
  // ===========================================================================
  await page.click(`text=${callTitle}`);
  await page.waitForURL(/\/volunteer-calls\/[0-9a-f-]+/);
  const callUrl = page.url();
  const callId = callUrl.split("/").pop()!;

  await narrate(page, "Adding two tasks by hand…", 1600);

  for (const t of [
    {
      desc: "Roof patch at 102 Maple Ave",
      date: dateOffsetMMDD(5),
      address: "102 Maple Ave",
      city: "Arlington",
    },
    {
      desc: "Bathroom grab-bar install",
      date: dateOffsetMMDD(6),
      address: "44 Oak St",
      city: "Falls Church",
    },
  ]) {
    await page.click('[data-testid="task-add-open"]');
    await page.waitForSelector('[data-testid="task-description"]');
    await sleep(400);
    await page.fill('[data-testid="task-date"]', t.date);
    await page.fill('[data-testid="task-address"]', t.address);
    await page.selectOption('[data-testid="task-city"]', t.city);
    await page.fill('[data-testid="task-description"]', t.desc);
    // Button is disabled until TaskEntryForm reports a valid payload.
    const submit = page.locator('[data-testid="task-add-submit"]');
    await submit.waitFor({ state: "visible" });
    await page.waitForFunction(
      () =>
        !(
          document.querySelector(
            '[data-testid="task-add-submit"]',
          ) as HTMLButtonElement | null
        )?.disabled,
    );
    await submit.click();
    await sleep(800);
  }

  // ===========================================================================
  // STEP 3a: Bulk add 7 more tasks (2 on the upcoming Thursday)
  // ===========================================================================
  await narrate(
    page,
    "…and the rest of the schedule lands in bulk (seven more, two on Thursday).",
    2200,
  );
  await runBulk([
    "add-tasks",
    "--call-id",
    callId,
    "--count",
    "7",
    "--thursday",
    "2",
  ]);
  await page.reload();
  await page.waitForSelector(".call-detail, .task-row, table");
  await sleep(1500);

  // ===========================================================================
  // STEP 4 + 5: Send the call (transitions open → waiting; invites go out)
  // ===========================================================================
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await page.waitForSelector(".calls-page");
  await narrate(page, "Don sends the call out to volunteers.", 2000);

  const sendRow = page.locator(`[data-testid="call-row"][data-call-id="${callId}"]`);
  await sendRow.locator('[data-testid="row-action-send_invites"]').click();
  await sleep(2000);

  // Don's role in this scene is done — log him out, then narrate over the
  // logged-out app while showing what every volunteer just received.
  await clearNarration(page);
  await logout(page);

  await narrate(
    page,
    "Every active volunteer just received an invite — here's the outbox.",
    2400,
  );
  await showMailpitInbox(page);
  await sleep(4000);

  // Zoom in on one volunteer's invite specifically.
  const inviteMsg = await waitForMessage(api, VICK, /invite|call/i, 12_000);
  await narrate(
    page,
    "Here's Vick Fisher's invite. The button below logs Vick in directly — no password.",
    2800,
  );
  await showMailpitPanel(api, page, inviteMsg.ID);
  await sleep(3500);

  // ===========================================================================
  // STEP 6: Vick clicks the invite link — auto-authenticates, lands on
  // the availability page. No login form.
  // ===========================================================================
  const inviteHtml = await fetchMessageHtml(api, inviteMsg.ID);
  const inviteLink = extractAppLink(inviteHtml, /\/volunteering\?token=/);
  await hideMailpitPanel(page);
  await clearNarration(page);
  await narrate(
    page,
    "Vick clicks the link and lands straight on the availability page.",
    2000,
  );
  await page.goto(inviteLink);
  await page.waitForSelector("text=/Volunteer|Open Volunteer Calls/i");
  await sleep(800);

  const vickChecks = page.locator('input[type="checkbox"]');
  const vickCount = await vickChecks.count();
  for (let i = 0; i < vickCount; i++) {
    await vickChecks.nth(i).check();
    await sleep(160);
  }
  await page.click("text=/Submit Availability/i");
  await page
    .waitForSelector("text=/saved/i", { timeout: 5000 })
    .catch(() => {});
  await sleep(1200);
  await logout(page);

  // ===========================================================================
  // STEP 7: Bryan Cobb logs in with partial availability
  // ===========================================================================
  await loginViaMagicLink(page, api, BRYAN, { showInMailpit: false });
  await page.waitForSelector("text=/Volunteer|Open Volunteer Calls/i");
  const bryanChecks = page.locator('input[type="checkbox"]');
  const bryanTotal = await bryanChecks.count();
  for (let i = 0; i < Math.min(2, bryanTotal); i++) {
    await bryanChecks.nth(i).check();
    await sleep(160);
  }
  await page.click("text=/Submit Availability/i");
  await sleep(1200);
  await logout(page);

  // ===========================================================================
  // STEP 8: Narration overlay — "24 more responded overnight" while bulk
  // availability seeds in parallel
  // ===========================================================================
  await page.goto(`${BASE_URL}/login`);
  await narrate(page, "Overnight, 24 more volunteers responded…", 2000);
  await runBulk(["respond-availability", "--call-id", callId, "--count", "24"]);

  // ===========================================================================
  // STEP 9: Admin logs back in, opens Assignment Dashboard
  // ===========================================================================
  await loginViaMagicLink(page, api, DON_GMAIL_ALIAS, { showInMailpit: false });
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await narrate(
    page,
    "Don opens the Assignment Dashboard, now full of responses.",
    2000,
  );

  const assignRow = page.locator(`[data-testid="call-row"][data-call-id="${callId}"]`);
  await assignRow.locator('[data-testid="row-action-assign"]').click();
  await page.waitForURL(/\/assign/);
  await sleep(3500);

  // Heuristic auto-assign: click the first Available button for each task
  const assignButtons = page.locator(
    ".available-list button:has-text('Assign'), button.assign-btn",
  );
  const btnCount = await assignButtons.count();
  for (let i = 0; i < Math.min(btnCount, 12); i++) {
    await assignButtons
      .nth(i)
      .click()
      .catch(() => {});
    await sleep(200);
  }

  await page.click("button:has-text('Done Assigning')").catch(() => {});
  await sleep(1500);

  // ===========================================================================
  // STEP 10: Send Assignments — show one assignment + one team-lead roster
  // ===========================================================================
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await narrate(
    page,
    "Sending assignments. Volunteers get individual emails; team leads get rosters.",
    2400,
  );
  const sendAssignRow = page.locator(`[data-testid="call-row"][data-call-id="${callId}"]`);
  await sendAssignRow.locator('[data-testid="row-action-send_assignments"]').click();
  await sleep(2500);

  try {
    const assignmentMsg = await waitForMessage(
      api,
      VICK,
      /assign|task/i,
      12_000,
    );
    await showMailpitPanel(api, page, assignmentMsg.ID);
    await sleep(4000);
  } catch {
    /* swallow — recording still useful */
  }

  // ===========================================================================
  // STEP 11: Vick logs in and sees the final assignment
  // ===========================================================================
  await logout(page);
  await loginViaMagicLink(page, api, VICK, { showInMailpit: false });
  await narrate(page, "Vick logs in and sees the final assignment.", 2500);
  await sleep(3000);
});

// ---------------------------------------------------------------------------
// helpers local to this spec
// ---------------------------------------------------------------------------

function dateOffsetMMDD(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
}
