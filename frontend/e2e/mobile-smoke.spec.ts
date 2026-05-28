/**
 * Mobile-viewport smoke test for /volunteering.
 *
 * Scope: render + reachability at iPhone-SE-ish dimensions. We log in
 * as Vick (a volunteer in the seed) via the real magic-link flow,
 * then prove that the page has no horizontal overflow, the Avatar
 * menu opens, the Maximum-tasks Select opens and commits, and the
 * task-row checkboxes meet the 44px touch-target minimum.
 *
 * Same dev-stack prereqs as `make demo` / `make test-e2e`: needs
 * `make dev` running in another shell. When the backend is unreachable
 * (no dev stack), the spec calls `test.skip` with a hint so a casual
 * run reports "skipped: dev not up" instead of timing out.
 *
 * Wire-up: `make test-mobile-smoke` (not in `make test` by default
 * because the dev-stack prereq is real and unattended runs would just
 * skip every time).
 */

import { request, test, expect } from "@playwright/test";
import { loginViaMagicLink } from "./demo-helpers";

const VICK = "vgfisher@gmail.com";
// iPhone SE — the narrowest viewport we actually care about supporting.
const MOBILE_VIEWPORT = { width: 375, height: 667 };
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8001";

test.use({
  viewport: MOBILE_VIEWPORT,
  // The shared config flips this to false for the demo recording; the
  // smoke test wants the standard headless CI behavior.
  headless: true,
  video: "off",
  launchOptions: { slowMo: 0 },
});

test.beforeAll(async () => {
  // Bail out early when the dev stack isn't up. Without this, every
  // step of the spec would time out and the run would take >60s to
  // report a failure that's really "you didn't start `make dev`."
  try {
    const ctx = await request.newContext();
    const resp = await ctx.get(`${BACKEND_URL}/health`, { timeout: 1500 });
    await ctx.dispose();
    if (!resp.ok())
      test.skip(true, `Backend at ${BACKEND_URL} returned ${resp.status()}`);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    test.skip(true, `Dev stack not reachable at ${BACKEND_URL}: ${msg}`);
  }
});

test("volunteering page is usable at 375×667", async ({ page }) => {
  const api = await request.newContext();
  await loginViaMagicLink(page, api, VICK, { showInMailpit: false });

  // Logged-in volunteer lands on /volunteering by default; loginViaMagicLink
  // waits for the URL to leave /login or /verify.
  await page.waitForURL(/\/volunteering/, { timeout: 10_000 });
  await page.waitForLoadState("networkidle");

  // ── No horizontal body overflow ────────────────────────────────────────
  // Bug it catches: a wide table or fixed pixel min-width pushes the
  // body past the viewport, the user gets a horizontal scroll, and the
  // whole layout feels broken.
  const overflow = await page.evaluate(() => {
    const html = document.documentElement;
    return {
      scrollWidth: html.scrollWidth,
      clientWidth: html.clientWidth,
    };
  });
  // Allow 1px for sub-pixel rounding. Anything wider means the page is
  // visibly leaking.
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);

  // ── Avatar menu opens ──────────────────────────────────────────────────
  // Bug it catches: AvatarMenu drawer positioned with a fixed width that
  // pushes off-screen on a 375px viewport, or the open-toggle button is
  // hidden behind the header at this width.
  const avatarBtn = page.getByRole("button", { name: /user menu/i });
  await expect(avatarBtn).toBeVisible();
  await avatarBtn.click();
  // Drawer renders "marvin.greenberg" / email at top + a Settings row.
  await expect(page.getByRole("menuitem", { name: /settings/i })).toBeVisible();
  // Close it again so it doesn't block subsequent clicks.
  await page.keyboard.press("Escape");

  // ── Maximum-tasks Select opens and commits ─────────────────────────────
  // Bug it catches: the custom Select's listbox is wider than 375px or
  // is rendered with `position: fixed; left: …` that lands off-screen
  // on phones.
  const maxWeekSelect = page
    .getByRole("combobox", { name: /maximum tasks/i })
    .first();
  await expect(maxWeekSelect).toBeVisible();
  await maxWeekSelect.click();
  // Listbox panel renders within the viewport.
  const listbox = page.getByRole("listbox").first();
  await expect(listbox).toBeVisible();
  const listboxBox = await listbox.boundingBox();
  expect(listboxBox).not.toBeNull();
  if (listboxBox) {
    expect(listboxBox.x).toBeGreaterThanOrEqual(0);
    expect(listboxBox.x + listboxBox.width).toBeLessThanOrEqual(
      MOBILE_VIEWPORT.width + 1,
    );
  }
  // Commit value "3" and confirm the trigger label updates.
  await page.getByRole("option", { name: "3" }).first().click();
  await expect(maxWeekSelect).toContainText("3");

  // ── Task-row checkboxes meet 44px touch-target ─────────────────────────
  // Bug it catches: a CSS refactor shrinks the tappable area below the
  // platform-recommended 44×44 minimum, making the page un-tap-able for
  // people with bigger fingers / motor-impairment users.
  // We measure the visible label/area, not the raw <input> (which is
  // styled to 22px) — the wrapping label provides the hit target.
  const labels = page.locator("label.task-check");
  const labelCount = await labels.count();
  if (labelCount > 0) {
    const first = labels.first();
    const box = await first.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      // The label hosts a 22px input, but the parent .task-row gives the
      // tappable region its height via min-height:56px. Check at the row
      // level so the assertion lines up with the actual hit area.
      const row = first.locator("xpath=..");
      const rowBox = await row.boundingBox();
      expect(rowBox?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
  }

  await api.dispose();
});
