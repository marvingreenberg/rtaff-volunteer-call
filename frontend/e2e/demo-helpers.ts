/**
 * Demo-only helpers: narration overlay, Mailpit integration, bulk
 * subprocess invocation. Imported by demo.spec.ts.
 */

import { execFile } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import type { APIRequestContext, Page } from "@playwright/test";

const execFileP = promisify(execFile);

declare global {
  interface Window {
    __demoNarratorText?: string;
  }
}

const HERE = path.dirname(fileURLToPath(import.meta.url));

export const BASE_URL = process.env.BASE_URL || "http://localhost:5173";
export const MAILPIT_URL = process.env.MAILPIT_URL || "http://localhost:8025";
const PROJECT_ROOT = path.resolve(HERE, "..", "..");

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// Narration overlay
// ---------------------------------------------------------------------------

const NARRATOR_INIT_SCRIPT = `
(() => {
  const ID = "__demo_narrator__";
  const ensure = () => {
    if (!document.body) return;
    if (document.getElementById(ID)) return;
    const div = document.createElement("div");
    div.id = ID;
    div.style.cssText = [
      "position:fixed",
      "left:32px",
      "right:32px",
      "bottom:32px",
      "background:rgba(0,30,55,0.94)",
      "color:#fff",
      "font:600 22px/1.4 system-ui,-apple-system,sans-serif",
      "padding:18px 26px",
      "border-radius:14px",
      "box-shadow:0 12px 36px rgba(0,0,0,.28)",
      "z-index:2147483647",
      "pointer-events:none",
      "transition:opacity .25s",
      "opacity:0",
    ].join(";");
    document.body.appendChild(div);
    // Restore any in-flight narration text after navigation.
    const t = window.__demoNarratorText;
    if (t) {
      div.textContent = t;
      div.style.opacity = "1";
    }
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensure);
  } else {
    ensure();
  }
})();
`;

/**
 * Registers the narration overlay so it survives navigations.
 * Call once per page at the start of the test.
 */
export async function installNarrator(page: Page): Promise<void> {
  await page.addInitScript(NARRATOR_INIT_SCRIPT);
}

// ---------------------------------------------------------------------------
// Click visualizer
// ---------------------------------------------------------------------------

const CLICK_VISUALIZER_INIT_SCRIPT = `
(() => {
  const KEYFRAME_ID = "__demo_click_keyframes__";
  const CURSOR_ID = "__demo_cursor__";
  const ATTR = "__demo_click_visualizer_installed__";
  const ensure = () => {
    if (!document.body) return;
    if ((document.body as any).dataset && (document.body as any).dataset[ATTR]) return;
    (document.body as any).dataset && ((document.body as any).dataset[ATTR] = "1");
    if (!document.getElementById(KEYFRAME_ID)) {
      const style = document.createElement("style");
      style.id = KEYFRAME_ID;
      style.textContent =
        "@keyframes __demo_click_ripple{0%{transform:scale(0.4);opacity:1}100%{transform:scale(2.2);opacity:0}}" +
        "@keyframes __demo_cursor_pulse{0%{transform:scale(1)}50%{transform:scale(1.6)}100%{transform:scale(1)}}";
      document.head.appendChild(style);
    }
    // Persistent red-ball cursor — teleports to wherever Playwright's
    // synthesized mousemove lands. (page.click() under the hood does
    // hover → move → down → up, so mousemove fires here in the page.)
    let cursor = document.getElementById(CURSOR_ID) as HTMLDivElement | null;
    if (!cursor) {
      cursor = document.createElement("div");
      cursor.id = CURSOR_ID;
      cursor.style.cssText = [
        "position:fixed",
        "left:-100px",
        "top:-100px",
        "width:18px",
        "height:18px",
        "margin-left:-9px",
        "margin-top:-9px",
        "border-radius:50%",
        "background:rgba(220,38,38,0.85)",
        "box-shadow:0 0 0 2px rgba(255,255,255,0.9),0 2px 6px rgba(0,0,0,0.35)",
        "pointer-events:none",
        "z-index:2147483646",
        "transition:left .05s linear,top .05s linear",
      ].join(";");
      document.body.appendChild(cursor);
    }
    const moveCursor = (e) => {
      const x = e.clientX;
      const y = e.clientY;
      if (typeof x !== "number" || typeof y !== "number") return;
      if (cursor) {
        cursor.style.left = x + "px";
        cursor.style.top = y + "px";
      }
    };
    window.addEventListener("pointermove", moveCursor, true);
    window.addEventListener("mousemove", moveCursor, true);

    const onDown = (e) => {
      const x = e.clientX;
      const y = e.clientY;
      if (typeof x !== "number" || typeof y !== "number") return;
      // Pulse the cursor itself.
      if (cursor) {
        cursor.style.animation = "none";
        // Force reflow so the animation can restart on rapid clicks.
        void cursor.offsetWidth;
        cursor.style.animation = "__demo_cursor_pulse 320ms ease-out";
      }
      // Plus the existing ripple, for emphasis.
      const dot = document.createElement("div");
      dot.style.cssText = [
        "position:fixed",
        "left:" + (x - 18) + "px",
        "top:" + (y - 18) + "px",
        "width:36px",
        "height:36px",
        "border-radius:50%",
        "background:rgba(220,38,38,0.28)",
        "border:2px solid rgba(220,38,38,0.95)",
        "pointer-events:none",
        "z-index:2147483645",
        "animation:__demo_click_ripple 520ms ease-out forwards",
      ].join(";");
      document.body.appendChild(dot);
      setTimeout(() => dot.remove(), 600);
    };
    // Capture phase so we see the click even when downstream handlers stop
    // propagation. Use pointerdown (covers mouse + touch + pen).
    window.addEventListener("pointerdown", onDown, true);
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensure);
  } else {
    ensure();
  }
})();
`;

/**
 * Inject a small "ripple at click point" visualizer that runs on every
 * page load and persists across navigations. Pointerdown events from
 * synthesized Playwright clicks fire normal DOM events, so the ripple
 * appears for every page.click() / .selectOption() / etc.
 */
export async function installClickVisualizer(page: Page): Promise<void> {
  await page.addInitScript(CLICK_VISUALIZER_INIT_SCRIPT);
}

// ---------------------------------------------------------------------------
// Mailpit panel: scroll inside the embedded iframe
// ---------------------------------------------------------------------------

/**
 * Scroll the Mailpit panel's iframe so that the first link whose href
 * matches `hrefPattern` is centered in view. Waits for the iframe to be
 * loaded (the panel sets srcdoc which is same-origin with the parent, so
 * we can reach into contentDocument freely). No-op if the panel or link
 * isn't present.
 */
export async function scrollMailpitToHref(
  page: Page,
  hrefPattern: RegExp,
  timeoutMs = 3000,
): Promise<void> {
  await page.evaluate(
    ({ source, timeout }) => {
      return new Promise<void>((resolve) => {
        const deadline = Date.now() + timeout;
        const re = new RegExp(source);
        const tick = () => {
          const iframe = document.querySelector(
            "#__demo_mailpit__ iframe",
          ) as HTMLIFrameElement | null;
          const doc = iframe?.contentDocument;
          const body = doc?.body;
          if (!doc || !body) {
            if (Date.now() < deadline) {
              setTimeout(tick, 80);
              return;
            }
            resolve();
            return;
          }
          const anchors = Array.from(
            doc.querySelectorAll("a"),
          ) as HTMLAnchorElement[];
          const link = anchors.find((a) =>
            re.test(a.getAttribute("href") || ""),
          );
          if (link) {
            link.scrollIntoView({ behavior: "smooth", block: "center" });
            resolve();
            return;
          }
          if (Date.now() < deadline) {
            setTimeout(tick, 80);
          } else {
            resolve();
          }
        };
        tick();
      });
    },
    { source: hrefPattern.source, timeout: timeoutMs },
  );
}

export async function injectNarrationOverlay(page: Page): Promise<void> {
  // Best-effort sync injection in case the script didn't run yet (e.g.
  // installNarrator was called after the first goto). The init script is
  // the durable mechanism.
  await page
    .evaluate(() => {
      if (document.getElementById("__demo_narrator__")) return;
      if (!document.body) return;
      const div = document.createElement("div");
      div.id = "__demo_narrator__";
      div.style.cssText =
        "position:fixed;left:32px;right:32px;bottom:32px;background:rgba(0,30,55,0.94);color:#fff;font:600 22px/1.4 system-ui,-apple-system,sans-serif;padding:18px 26px;border-radius:14px;box-shadow:0 12px 36px rgba(0,0,0,.28);z-index:2147483647;pointer-events:none;transition:opacity .25s;opacity:0";
      document.body.appendChild(div);
    })
    .catch(() => {});
}

export async function narrate(
  page: Page,
  text: string,
  holdMs = 1700,
): Promise<void> {
  await injectNarrationOverlay(page);
  await page
    .evaluate((t) => {
      window.__demoNarratorText = t;
      const div = document.getElementById("__demo_narrator__");
      if (div) {
        div.textContent = t;
        (div as HTMLElement).style.opacity = "1";
      }
    }, text)
    .catch(() => {});
  await sleep(holdMs);
}

export async function clearNarration(page: Page): Promise<void> {
  await page
    .evaluate(() => {
      window.__demoNarratorText = "";
      const div = document.getElementById("__demo_narrator__");
      if (div) (div as HTMLElement).style.opacity = "0";
    })
    .catch(() => {});
}

// ---------------------------------------------------------------------------
// Mailpit
// ---------------------------------------------------------------------------

export interface MailpitMessage {
  ID: string;
  Subject: string;
  To: { Address: string }[];
  Date: string;
}

export async function waitForMessage(
  api: APIRequestContext,
  recipient: string,
  subjectMatch: RegExp,
  timeoutMs = 15_000,
): Promise<MailpitMessage> {
  return waitForMessageMatching(api, subjectMatch, timeoutMs, {
    recipient,
  });
}

/**
 * Poll Mailpit until a message matching `subjectMatch` arrives. By default
 * scans the entire inbox; if `opts.recipient` is set, narrows the search
 * with a `to:` query (more efficient on busy inboxes). Useful when the
 * recipient is unknown ahead of time — e.g. "any team-lead roster email
 * that just went out."
 */
export async function waitForMessageMatching(
  api: APIRequestContext,
  subjectMatch: RegExp,
  timeoutMs = 15_000,
  opts: { recipient?: string } = {},
): Promise<MailpitMessage> {
  const deadline = Date.now() + timeoutMs;
  const url = opts.recipient
    ? `${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`to:${opts.recipient}`)}`
    : `${MAILPIT_URL}/api/v1/messages?limit=200`;
  while (Date.now() < deadline) {
    const resp = await api.get(url);
    if (resp.ok()) {
      const data = (await resp.json()) as { messages?: MailpitMessage[] };
      const hit = (data.messages || []).find((m) =>
        subjectMatch.test(m.Subject),
      );
      if (hit) return hit;
    }
    await sleep(400);
  }
  const where = opts.recipient ? `to ${opts.recipient} ` : "";
  throw new Error(
    `No message ${where}matching ${subjectMatch} within ${timeoutMs}ms`,
  );
}

export async function fetchMessageHtml(
  api: APIRequestContext,
  id: string,
): Promise<string> {
  const resp = await api.get(`${MAILPIT_URL}/api/v1/message/${id}`);
  const data = (await resp.json()) as { HTML?: string; Text?: string };
  return data.HTML || data.Text || "";
}

/**
 * Fetch the message HTML with `cid:<id>` references rewritten to live
 * Mailpit attachment URLs (`/api/v1/message/{id}/part/{partID}`). Without
 * this, inline images (the RT-AFF logo, accent strip) render as broken
 * placeholders when the body is dropped into an iframe `srcdoc` — the
 * srcdoc base is `about:srcdoc`, where `cid:` schemes don't resolve.
 */
export async function fetchRenderedMessageHtml(
  api: APIRequestContext,
  id: string,
): Promise<string> {
  const resp = await api.get(`${MAILPIT_URL}/api/v1/message/${id}`);
  const data = (await resp.json()) as {
    HTML?: string;
    Text?: string;
    Inline?: { PartID: string; ContentID: string }[];
  };
  let html = data.HTML || data.Text || "";
  for (const part of data.Inline ?? []) {
    const url = `${MAILPIT_URL}/api/v1/message/${id}/part/${part.PartID}`;
    // Match cid: in src/href/background, optionally quoted/escaped.
    const cidRe = new RegExp(`cid:${escapeRegex(part.ContentID)}`, "gi");
    html = html.replace(cidRe, url);
  }
  return html;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function extractVerifyLink(html: string): string {
  return extractAppLink(html, /\/verify\?token=/);
}

/**
 * Extract the first anchor href whose path matches `pathRe`. Used for
 * pulling the magic-link or invite link out of an email body.
 */
export function extractAppLink(html: string, pathRe: RegExp): string {
  const re = new RegExp(`href="([^"]*${pathRe.source}[^"]+)"`);
  const m = html.match(re);
  if (!m) throw new Error(`No link matching ${pathRe} found in message HTML`);
  return m[1].replace(/&amp;/g, "&");
}

/**
 * Pin a Mailpit message view onto the right side of the app page as an
 * iframe, so the recorded video shows the email arriving without context
 * switching. The panel persists until hideMailpitPanel is called.
 */
export async function showMailpitPanel(
  api: APIRequestContext,
  page: Page,
  messageId: string,
): Promise<void> {
  const html = await fetchRenderedMessageHtml(api, messageId);
  await page.evaluate(
    ({ body }) => {
      const existing = document.getElementById("__demo_mailpit__");
      if (existing) existing.remove();
      const panel = document.createElement("div");
      panel.id = "__demo_mailpit__";
      panel.style.cssText = [
        "position:fixed",
        "top:16px",
        "right:16px",
        "width:460px",
        "height:72vh",
        "background:#fff",
        "border:2px solid #003a5d",
        "border-radius:10px",
        "box-shadow:0 18px 48px rgba(0,0,0,.28)",
        "overflow:hidden",
        "display:flex",
        "flex-direction:column",
        "z-index:2147483646",
      ].join(";");
      const header = document.createElement("div");
      header.style.cssText =
        "background:#003a5d;color:#fff;padding:10px 16px;font:600 15px/1 system-ui;flex:0 0 auto;";
      header.textContent = "📬 Mailpit — incoming email";
      panel.appendChild(header);
      const viewport = document.createElement("div");
      // `zoom` (Chromium) shrinks the layout box too, unlike transform:scale,
      // so the iframe at 100% width visually fits without horizontal clipping.
      viewport.style.cssText =
        "flex:1 1 auto;overflow:auto;background:#fff;zoom:0.72;";
      const iframe = document.createElement("iframe");
      iframe.srcdoc = body;
      iframe.style.cssText =
        "border:0;background:#fff;width:100%;height:100%;display:block;";
      viewport.appendChild(iframe);
      panel.appendChild(viewport);
      document.body.appendChild(panel);
    },
    { body: html },
  );
}

/**
 * Show Mailpit's actual inbox UI inside the demo panel — useful for
 * "here are all the emails that just went out" beats. No srcdoc; the
 * iframe points straight at the running Mailpit instance.
 */
export async function showMailpitInbox(page: Page): Promise<void> {
  await page.evaluate((base) => {
    const existing = document.getElementById("__demo_mailpit__");
    if (existing) existing.remove();
    const panel = document.createElement("div");
    panel.id = "__demo_mailpit__";
    panel.style.cssText = [
      "position:fixed",
      "top:16px",
      "right:16px",
      "width:460px",
      "height:72vh",
      "background:#fff",
      "border:2px solid #003a5d",
      "border-radius:10px",
      "box-shadow:0 18px 48px rgba(0,0,0,.28)",
      "overflow:hidden",
      "display:flex",
      "flex-direction:column",
      "z-index:2147483646",
    ].join(";");
    const header = document.createElement("div");
    header.style.cssText =
      "background:#003a5d;color:#fff;padding:10px 16px;font:600 15px/1 system-ui;flex:0 0 auto;";
    header.textContent = "📬 Mailpit — outgoing inbox";
    panel.appendChild(header);
    const viewport = document.createElement("div");
    viewport.style.cssText =
      "flex:1 1 auto;overflow:hidden;background:#fff;zoom:0.72;";
    const iframe = document.createElement("iframe");
    iframe.src = `${base}/`;
    iframe.style.cssText =
      "border:0;background:#fff;width:100%;height:100%;display:block;";
    viewport.appendChild(iframe);
    panel.appendChild(viewport);
    document.body.appendChild(panel);
  }, MAILPIT_URL);
}

export async function hideMailpitPanel(page: Page): Promise<void> {
  await page.evaluate(() => {
    const el = document.getElementById("__demo_mailpit__");
    if (el) el.remove();
  });
}

// ---------------------------------------------------------------------------
// Bulk demo script subprocess
// ---------------------------------------------------------------------------

export async function runBulk(args: string[]): Promise<string> {
  const backendDir = path.join(PROJECT_ROOT, "backend");
  const scriptPath = path.join(PROJECT_ROOT, "scripts", "demo_bulk.py");
  const { stdout } = await execFileP(
    "uv",
    ["run", "python", scriptPath, ...args],
    {
      cwd: backendDir,
    },
  );
  return stdout.trim();
}

// ---------------------------------------------------------------------------
// Login flow (real magic-link, observed in Mailpit)
// ---------------------------------------------------------------------------

export async function loginViaMagicLink(
  page: Page,
  api: APIRequestContext,
  email: string,
  options: { showInMailpit?: boolean } = {},
): Promise<void> {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForSelector('input[type="email"]');
  await page.fill('input[type="email"]', email);
  await sleep(400);
  await clickWithCursor(page.locator('button[type="submit"]'));
  await page.waitForSelector(".alert-success", { timeout: 8000 });

  const msg = await waitForMessage(api, email, /log in/i);
  const html = await fetchMessageHtml(api, msg.ID);
  const link = extractVerifyLink(html);

  if (options.showInMailpit !== false) {
    await showMailpitPanel(api, page, msg.ID);
    await sleep(2400);
    await hideMailpitPanel(page);
  }

  await page.goto(link);
  // After verify, the app routes to /volunteering for volunteers and the
  // top-level layout for staff. Either way, /login and /verify should be
  // gone.
  await page.waitForURL((url) => !/\/(login|verify)/.test(url.pathname), {
    timeout: 10_000,
  });
}

/**
 * Hover the cursor onto the target, hold for `preMs` so the red-ball
 * visualizer lands on camera, click, then hold for `postMs`. Both
 * pauses default sensibly — most callers can just pass a Locator. Pass
 * `postMs` to absorb the rhythm sleep that callers used to chain after
 * the click ("click, breathe, click").
 *
 * All steps swallow errors so an off-screen / detached target doesn't
 * tank the demo recording.
 */
export async function clickWithCursor(
  target: import("@playwright/test").Locator,
  opts: { preMs?: number; postMs?: number } = {},
): Promise<void> {
  const preMs = opts.preMs ?? 200;
  const postMs = opts.postMs ?? 0;
  await target.hover().catch(() => {});
  await sleep(preMs);
  await target.click().catch(() => {});
  if (postMs > 0) await sleep(postMs);
}

/**
 * Tick task rows on the /volunteering page with a deliberate "scroll,
 * hover-then-click" rhythm so the recording reads as a human picking.
 * Pass `"all"` to tick every row, or an explicit list of 0-based indices.
 * Returns the number of rows actually ticked.
 */
export async function pickTasks(
  page: Page,
  which: number[] | "all",
  delayMs: number,
): Promise<number> {
  const rows = page.locator(".task-row");
  const total = await rows.count();
  const targets =
    which === "all"
      ? Array.from({ length: total }, (_, i) => i)
      : which.filter((i) => i >= 0 && i < total);
  for (const idx of targets) {
    const row = rows.nth(idx);
    await row.scrollIntoViewIfNeeded().catch(() => {});
    await clickWithCursor(row.locator('input[type="checkbox"]'), {
      postMs: delayMs,
    });
  }
  return targets.length;
}

/**
 * Set the Maximum-tasks-per-week pulldowns on /volunteering. Picks the
 * single-week or two-week variant automatically by sniffing aria-labels —
 * the Week 2 pulldown is only rendered when the call's tasks span two ISO
 * weeks. Scrolls into view first so the change is visible on camera.
 */
export async function setMaxPerWeek(
  page: Page,
  week1: number,
  week2: number | null,
): Promise<void> {
  const sel1 = page.locator('select[aria-label="Maximum tasks, week 1"]');
  const single = page.locator('select[aria-label="Maximum tasks per week"]');
  const sel2 = page.locator('select[aria-label="Maximum tasks, week 2"]');
  const target = (await sel1.count()) > 0 ? sel1 : single;
  await target
    .first()
    .scrollIntoViewIfNeeded()
    .catch(() => {});
  await sleep(400);
  await target
    .first()
    .selectOption(String(week1))
    .catch(() => {});
  await sleep(500);
  if (week2 != null && (await sel2.count()) > 0) {
    await sel2
      .first()
      .selectOption(String(week2))
      .catch(() => {});
    await sleep(500);
  }
}

// ---------------------------------------------------------------------------
// Bulk script wrappers — typed-shorter aliases over runBulk(). Keep one
// function per subcommand so the spec reads like a sentence ("bulk add 9
// tasks at offset 2") rather than an opaque argv array.
// ---------------------------------------------------------------------------

export function bulkAddTasks(
  callId: string,
  count: number,
  offset: number,
): Promise<string> {
  return runBulk([
    "add-tasks",
    "--call-id",
    callId,
    "--count",
    String(count),
    "--offset",
    String(offset),
  ]);
}

export function bulkRespondAvailability(
  callId: string,
  count: number,
): Promise<string> {
  return runBulk([
    "respond-availability",
    "--call-id",
    callId,
    "--count",
    String(count),
  ]);
}

// ---------------------------------------------------------------------------
// Call list row actions — both the row locator and the per-action click
// follow the same pattern (`data-testid="call-row"` + `row-action-<name>`).
// One helper covers send_invites, assign, send_assignments, etc.
// ---------------------------------------------------------------------------

export function callRow(page: Page, callId: string) {
  return page.locator(`[data-testid="call-row"][data-call-id="${callId}"]`);
}

export async function clickCallAction(
  page: Page,
  callId: string,
  action: "send_invites" | "assign" | "send_assignments",
): Promise<void> {
  await clickWithCursor(
    callRow(page, callId).locator(`[data-testid="row-action-${action}"]`),
  );
}

/**
 * Wait for the next mail to `recipient` matching `subjectRe`, then pin it
 * in the demo's Mailpit panel. Returns the message metadata so the caller
 * can extract links from the body.
 */
export async function showEmailFor(
  api: APIRequestContext,
  page: Page,
  recipient: string,
  subjectRe: RegExp,
  timeoutMs = 12_000,
): Promise<MailpitMessage> {
  const msg = await waitForMessage(api, recipient, subjectRe, timeoutMs);
  await showMailpitPanel(api, page, msg.ID);
  return msg;
}

/**
 * Like `showEmailFor` but without a specific recipient — scans the whole
 * inbox for the first subject match. Useful for "show any team-lead
 * roster" where the auto-assigned lead's address isn't known ahead of
 * time.
 */
export async function showEmailMatching(
  api: APIRequestContext,
  page: Page,
  subjectRe: RegExp,
  timeoutMs = 12_000,
): Promise<MailpitMessage> {
  const msg = await waitForMessageMatching(api, subjectRe, timeoutMs);
  await showMailpitPanel(api, page, msg.ID);
  return msg;
}

/** Inputs for `addTaskByForm`. Date is MM/DD (matches the form's mask). */
export interface TaskFormFields {
  desc: string;
  date: string;
  address: string;
  city: string;
}

/**
 * Open the inline Add Task form on the call detail page, fill the four
 * required fields, wait for the submit button to enable (the form
 * validates before allowing submit), and click. Used by the demo to add
 * the two hand-crafted tasks at the start of the call.
 */
export async function addTaskByForm(
  page: Page,
  t: TaskFormFields,
): Promise<void> {
  await clickWithCursor(page.locator('[data-testid="task-add-open"]'));
  await page.waitForSelector('[data-testid="task-description"]');
  await sleep(400);
  await page.fill('[data-testid="task-date"]', t.date);
  await page.fill('[data-testid="task-address"]', t.address);
  await page.selectOption('[data-testid="task-city"]', t.city);
  await page.fill('[data-testid="task-description"]', t.desc);
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
  await clickWithCursor(submit, { postMs: 1600 });
}

/**
 * Fill each task card to a target volunteer count, walking the on-page
 * `.task-card` list in order. The target for card `i` is
 * `volunteers_needed + (overFill.has(i) ? 1 : 0)` — extra clicks land in
 * the "Extra!" state, demonstrating the over-fill UI. Always re-clicks the
 * top of each card's Available list since it re-sorts by fairness after
 * each assignment.
 *
 * `narrateOver` (optional) is invoked once per over-fill card so the demo
 * can call out the deliberate move on screen.
 */
export async function fillTaskCards(
  page: Page,
  options: {
    maxCards: number;
    overFill?: Set<number>;
    narrateOver?: (cardIndex: number) => Promise<void>;
    clickPauseMs?: number;
  },
): Promise<void> {
  const overFill = options.overFill ?? new Set<number>();
  const pause = options.clickPauseMs ?? 300;
  const cards = page.locator(".task-card");
  const count = Math.min(await cards.count(), options.maxCards);

  // Fill a single card up to its target. Returns true if the card hit its
  // target. Extracted so the second-pass sweep below can reuse the logic
  // without duplicating the read/click cadence.
  const fillOne = async (i: number, allowNarrate: boolean): Promise<boolean> => {
    const card = cards.nth(i);
    await card.scrollIntoViewIfNeeded().catch(() => {});
    const progressText =
      (await card
        .locator(".progress")
        .first()
        .textContent()
        .catch(() => "")) ?? "";
    const m = progressText.match(/(\d+)\s*\/\s*(\d+)/);
    if (!m) return false;
    const filled = parseInt(m[1], 10);
    const needed = parseInt(m[2], 10);
    const target = needed + (overFill.has(i) ? 1 : 0);
    const toClick = Math.max(0, target - filled);
    if (toClick === 0) return true;
    const availBtn = card.locator(
      ".list-block.available-block button.person-row",
    );
    for (let k = 0; k < toClick; k++) {
      if ((await availBtn.count()) === 0) break;
      // Narrate the over-fill exactly when the extra click is about to
      // happen, not at the top of the iteration — otherwise the "adding
      // one extra here" line plays during the routine fills and the
      // viewer can't connect narration to action.
      const isExtraClick = overFill.has(i) && k === toClick - 1 && target > needed;
      if (allowNarrate && isExtraClick && options.narrateOver) {
        await options.narrateOver(i);
      }
      await clickWithCursor(availBtn.first(), { postMs: pause });
    }
    return true;
  };

  for (let i = 0; i < count; i++) {
    await fillOne(i, true);
  }

  // Second-pass sweep: a card can be left short if a refresh races a
  // click (e.g. two tasks on the same date — assigning to the first
  // re-renders the available list while the next card is being read).
  // Re-check each card and top up any that didn't reach its target.
  for (let i = 0; i < count; i++) {
    const progressText =
      (await cards
        .nth(i)
        .locator(".progress")
        .first()
        .textContent()
        .catch(() => "")) ?? "";
    const m = progressText.match(/(\d+)\s*\/\s*(\d+)/);
    if (!m) continue;
    const filled = parseInt(m[1], 10);
    const needed = parseInt(m[2], 10);
    const target = needed + (overFill.has(i) ? 1 : 0);
    if (filled < target) {
      await fillOne(i, false);
    }
  }
}

export async function logout(page: Page): Promise<void> {
  // The Mailpit panel and narration overlay both sit in the corners and
  // intercept clicks on the avatar/drawer if left around.
  await hideMailpitPanel(page);
  await clearNarration(page);
  const avatar = page.locator(".avatar-btn");
  if (await avatar.isVisible().catch(() => false)) {
    await clickWithCursor(avatar, { postMs: 300 });
    await clickWithCursor(page.locator(".drawer-logout"));
    await page.waitForURL(/\/login/);
  }
}
