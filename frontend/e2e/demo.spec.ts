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
 *
 * Set AUTODEMO=0 to step through manually — a Continue/Cancel overlay
 * appears in the top-left at the major beats (login, call created, tasks
 * added, invites sent, Vick's invite shown, responses in, assignment pane,
 * assignments done, notifications sent, assignment emails reviewed). The
 * spec timeout is removed in this mode so you can sit on a pause as long
 * as you need.
 */

import { suggestCallTitle } from "../src/lib/api/types";
import { request, test, type Page } from "@playwright/test";
import {
  BASE_URL,
  addTaskByForm,
  bulkAddTasks,
  bulkRespondAvailability,
  clearNarration,
  clickCallAction,
  clickWithCursor,
  extractAppLink,
  fetchMessageHtml,
  fillTaskCards,
  hideMailpitPanel,
  installClickVisualizer,
  installNarrator,
  loginViaMagicLink,
  logout,
  narrate,
  pauseForUser,
  pickComboboxByAriaLabel,
  pickTasks,
  scrollMailpitToHref,
  setMaxPerWeek,
  showEmailFor,
  showEmailMatching,
  showMailpitInbox,
  sleep,
} from "./demo-helpers";

const DON_GMAIL_ALIAS = "donryanemail@gmail.com";
const VICK = "vgfisher@gmail.com";
const BRYAN = "bcobb2014@gmail.com";

// Per-row pick cadence (ms) for the live volunteer ticks.
const LIVE_PICK_DELAY_MS = 500;
// Bryan picks a couple of tasks from each ISO week. The demo schedule
// (scheduleSlotMMDD) places offsets 0..4 in week 1 and 5..10 in week 2,
// so these indices visibly hit both weeks.
const BRYAN_PICK_INDICES = [0, 2, 6, 8];

// All viewing pauses — narrations, mailpit panels, post-action "look at
// the resulting screen" sleeps — are scaled in one place. Login flow
// timings are left at their unscaled values so the magic-link
// interactions stay snappy.
const DISPLAY_HOLD_MULTIPLIER = 2.5;
const display = (ms: number): number =>
  Math.round(ms * DISPLAY_HOLD_MULTIPLIER);

test("RT-AFF volunteer-call demo", async ({ page }) => {
  // 20 minutes — long enough that manual-stepping pauses for discussion
  // don't expire mid-conversation, but still finite so a wedged spec
  // doesn't hang forever. The Makefile sets the same value via
  // --timeout, so both code paths agree.
  test.setTimeout(1_200_000);
  const api = await request.newContext();

  // `say` and `pause` bake the display-hold multiplier into the two call
  // shapes that dominate this file. Local closures so they pick up `page`
  // without threading it through.
  const say = (text: string, ms: number) => narrate(page, text, display(ms));
  const pause = (ms: number) => sleep(display(ms));

  // Register the narration overlay BEFORE any navigation so it re-attaches
  // automatically on every page load. Same for the click-ripple visualizer
  // — registered up front so every synthesized Playwright click leaves a
  // visible mark.
  await installNarrator(page);
  await installClickVisualizer(page);

  // ===========================================================================
  // STEP 1: Admin Don Ryan logs in — entering his *gmail alias*. The magic
  // link arrives at the gmail address; Mailpit panel proves it.
  // ===========================================================================
  await page.goto(`${BASE_URL}/login`);
  await narrate(
    page,
    "Don Ryan is an admin. He logs in to the RT-AFF volunteer call site.",
    2000,
  );
  await loginViaMagicLink(page, api, DON_GMAIL_ALIAS);
  await narrate(page, "Logged in. No active volunteer calls shown.", 900);
  await pauseForUser(page, "Don logged in");

  // ===========================================================================
  // STEP 2: Create a new call
  // ===========================================================================
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await page.waitForSelector(".calls-page");
  await say("Don creates a new volunteer call.", 1500);
  await clickWithCursor(page.locator("text=New Call"), { postMs: 600 });

  const callTitle = `Call for Volunteers ${suggestCallTitle("RTX")}`;
  await page.fill('input[placeholder*="Spring NRD"]', callTitle);
  await page.fill("textarea", "Call for Volunteers");
  await sleep(500);
  await clickWithCursor(
    page.locator('button[type="submit"]:has-text("Create")'),
  );
  await page.waitForSelector(`text=${callTitle}`);
  await sleep(500);
  await pauseForUser(page, "Call created");

  // ===========================================================================
  // STEP 3: Drill into the call and add two tasks manually
  // ===========================================================================
  await clickWithCursor(page.locator(`text=${callTitle}`));
  await page.waitForURL(/\/volunteer-calls\/[0-9a-f-]+/);
  const callId = page.url().split("/").pop()!;

  await say("Adding two tasks by hand", 1200);
  await addTaskByForm(page, {
    desc: "Dishwasher replacement.  Install baseboard trim in kitchen.  Update lighting in kitchen and dining area.",
    date: scheduleSlotMMDD(0),
    address: "102 Maple Ave",
    city: "Arlington",
  });
  await addTaskByForm(page, {
    desc: "Bathroom grab-bar install",
    date: scheduleSlotMMDD(1),
    address: "44 Oak St",
    city: "Falls Church",
  });
  await pauseForUser(page, "Two tasks added by hand");

  // ===========================================================================
  // STEP 3a: Bulk add the remaining 9 tasks (slots 2..10 of the schedule)
  // ===========================================================================
  await say(
    "The rest of the two-week schedule is added... (nine more total).",
    2400,
  );
  await bulkAddTasks(callId, 9, 2);
  await page.reload();
  await page.waitForSelector(".call-detail, .task-row, table");
  await pause(1500);

  // ===========================================================================
  // STEP 4 + 5: Send the call (transitions open → waiting; invites go out)
  // ===========================================================================
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await page.waitForSelector(".calls-page");
  await say("Don sends the call out to volunteers.", 2000);
  await clickCallAction(page, callId, "send_invites");
  await pause(2000);
  await pauseForUser(page, "Call sent — invites going out");

  // Don's role in this scene is done — log him out, then narrate over the
  // logged-out app while showing what every volunteer just received.
  await say("Don logs out, waits for the responses to roll in.", 1000);
  await clearNarration(page);
  await logout(page);

  await showMailpitInbox(page);
  await say("Every active volunteer gets an email — here's the outbox.", 2400);
  await pause(4000);

  // Zoom in on Vick's invite specifically, then scroll the panel to the
  // verify button before navigating away.
  await say(
    "Here's Vick Fisher's invite. The link brings up the Volunteer page for Vick — no log in.",
    2800,
  );
  const inviteMsg = await showEmailFor(api, page, VICK, /invite|call/i);
  await pause(3500);
  await pauseForUser(page, "Vick's invite shown");

  // ===========================================================================
  // STEP 6: Vick clicks the invite link — auto-authenticates, lands on
  // the availability page. No login form.
  // ===========================================================================
  const inviteHtml = await fetchMessageHtml(api, inviteMsg.ID);
  const inviteLink = extractAppLink(inviteHtml, /\/volunteering\?token=/);
  await scrollMailpitToHref(page, /\/volunteering\?token=/);
  await pause(1500);
  await hideMailpitPanel(page);
  await clearNarration(page);
  await say(
    "Vick clicks the link and lands straight on the availability page.",
    2000,
  );
  await page.goto(inviteLink);
  await page.waitForSelector("text=/Volunteer|Open Volunteer Calls/i");
  await sleep(800);

  await say("Vick signs up for every project — clicking down the list.", 1600);
  await pickTasks(page, "all", LIVE_PICK_DELAY_MS);
  await say(
    "Then he scrolls back up and caps himself: 2 tasks in week 1, 4 in week 2.",
    1800,
  );
  await setMaxPerWeek(page, 2, 4);
  await pause(800);
  await submitAvailability(page);
  await pause(1200);
  await logout(page);

  // ===========================================================================
  // STEP 7: Bryan responds live — leaves the per-week cap alone but picks
  // a couple tasks in each of the two ISO weeks to show week-aware
  // selection.
  // ===========================================================================
  await loginViaMagicLink(page, api, BRYAN, { showInMailpit: false });
  await page.waitForSelector("text=/Volunteer|Open Volunteer Calls/i");
  await say(
    "Bryan picks a couple of projects in week 1, then a couple more in week 2.",
    1800,
  );
  await pickTasks(page, BRYAN_PICK_INDICES, LIVE_PICK_DELAY_MS);
  await submitAvailability(page);
  await pause(1000);
  await logout(page);

  // ===========================================================================
  // STEP 8: Bulk-fill availability for the rest of the schedule.
  // ===========================================================================
  await page.goto(`${BASE_URL}/login`);
  await say(
    "Selection continues for the remaining tasks (23 more volunteers respond).",
    2200,
  );
  await bulkRespondAvailability(callId, 23);

  // ===========================================================================
  // STEP 9: Admin logs back in, opens Assignment Dashboard
  // ===========================================================================
  await loginViaMagicLink(page, api, DON_GMAIL_ALIAS, { showInMailpit: false });
  await pauseForUser(page, "Responses in — Don logs back in");
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await say("Don opens the Assignment Dashboard, now full of responses.", 2000);
  await clickCallAction(page, callId, "assign");
  await page.waitForURL(/\/assign/);
  await pause(2500);
  await pauseForUser(page, "Assignment pane open");

  // Auto-pick team leads — clears the "9 tasks need a team lead" gate in
  // one click using the new endpoint.
  await say("Auto-assign all the team leads (for the demo).", 2400);
  await clickWithCursor(page.locator("button.auto-leads-btn"), {
    postMs: display(2500),
  });

  // Assign volunteers task-by-task. Two cards get a deliberate over-fill
  // to surface the "Extra!" / 🥵 state.
  await say(
    "Volunteers are assigned task by task — prioritize idle (😴) and skilled (🛠️) where available.",
    1600,
  );
  await fillTaskCards(page, {
    maxCards: 11,
    overFill: new Set([4, 5]),
    narrateOver: () =>
      say("Adding one extra here — admin can deliberately over-fill.", 900),
  });

  // Take a beat on the alternate spreadsheet view before closing out the
  // assignment phase — same data, all-tasks-at-once matrix.
  await say(
    "There's also an alternate spreadsheet view showing every volunteer × task at once.",
    2400,
  );
  await clickViewTab(page, "spreadsheet");
  await pause(3500);
  await pauseForUser(page, "Spreadsheet view shown");
  await clickViewTab(page, "task");
  await pause(800);

  // Walk through the completion-policy gate. Every task is at or above
  // its volunteers_needed, but two were deliberately over-filled — so the
  // default "exact" policy still blocks closing and the Done button is
  // disabled. The demo narrates the gate, then the admin relaxes the
  // policy to "Allow extra" and clicks Done.
  await say(
    "By default, can't close the assignment unless every task has exactly its requested volunteers.",
    2600,
  );
  await pause(800);
  await say(
    "But the admin can override — for example, allow extras if more volunteers would help.",
    2400,
  );
  // Desired-policy picker is a Select.svelte combobox (feat/17); drive
  // it through the trigger-then-option click flow.
  await pickComboboxByAriaLabel(page, "Desired", "Allow extra").catch(() => {});
  await pause(1000);
  await say("Now Done Assigning is enabled — close the call.", 1600);
  await clickWithCursor(page.locator("button:has-text('Done Assigning')"), {
    postMs: display(1500),
  });

  // ===========================================================================
  // STEP 10: Send Assignments — show one assignment + one team-lead roster
  // ===========================================================================
  await page.goto(`${BASE_URL}/volunteer-calls`);
  await pauseForUser(page, "Assignments finished — back on Calls");
  await say(
    "Sending assignments. Volunteers get individual emails; team leads get rosters.",
    2400,
  );
  await clickCallAction(page, callId, "send_assignments");
  await pause(2500);
  await pauseForUser(page, "Assignment notifications sent");

  // Best-effort peek at Vick's assignment email + a team-lead roster
  // email. Both swallow errors so a Mailpit hiccup doesn't tank the
  // recording.
  await peekEmail(
    say,
    pause,
    "Here's Vick's individual assignment email.",
    () => showEmailFor(api, page, VICK, /assign|task/i),
    4000,
  );
  await peekEmail(
    say,
    pause,
    "And here's what a team lead gets — the full roster for their task.",
    () => showEmailMatching(api, page, /^Your team for /i),
    4500,
  );
  await pauseForUser(page, "Assignment emails reviewed");

  // ===========================================================================
  // STEP 11: Vick logs in and sees the final assignment
  // ===========================================================================
  await logout(page);
  await loginViaMagicLink(page, api, VICK, { showInMailpit: false });
  await say("Vick logs in and sees his assignment(s).", 2500);
  await pause(3000);
});

// ---------------------------------------------------------------------------
// helpers local to this spec
// ---------------------------------------------------------------------------

async function peekEmail(
  say: (text: string, ms: number) => Promise<void>,
  pause: (ms: number) => Promise<void>,
  narration: string,
  show: () => Promise<unknown>,
  holdMs: number,
): Promise<void> {
  await say(narration, 1600);
  await show()
    .then(() => pause(holdMs))
    .catch(() => {});
}

async function submitAvailability(page: Page): Promise<void> {
  await clickWithCursor(page.locator("text=/Submit Availability/i"));
  await page
    .waitForSelector("text=/saved/i", { timeout: 5000 })
    .catch(() => {});
}

async function clickViewTab(
  page: Page,
  view: "task" | "spreadsheet",
): Promise<void> {
  const text = view === "task" ? /task view/i : /spreadsheet/i;
  await clickWithCursor(page.locator(".view-tab", { hasText: text }));
}

/**
 * MM/DD for slot `idx` (0..10) of the two-week task schedule used by the
 * demo: Mon, Wed, Thu, Thu, Fri, Mon, Tue, Wed, Thu, Fri, Sat — anchored
 * on the first Monday strictly after today. Mirrors `_schedule_slots` in
 * scripts/demo_bulk.py.
 */
function scheduleSlotMMDD(idx: number): string {
  const offsets = [0, 2, 3, 3, 4, 7, 8, 9, 10, 11, 12];
  if (idx < 0 || idx >= offsets.length) {
    throw new Error(`scheduleSlotMMDD: idx ${idx} out of range`);
  }
  const today = new Date();
  const daysAhead = (1 - today.getDay() + 7) % 7 || 7; // first Monday after today
  const d = new Date(today);
  d.setDate(today.getDate() + daysAhead + offsets[idx]);
  return `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
}
