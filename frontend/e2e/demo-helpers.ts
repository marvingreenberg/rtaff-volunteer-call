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
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const resp = await api.get(
      `${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`to:${recipient}`)}`,
    );
    if (resp.ok()) {
      const data = (await resp.json()) as { messages?: MailpitMessage[] };
      const hit = (data.messages || []).find((m) =>
        subjectMatch.test(m.Subject),
      );
      if (hit) return hit;
    }
    await sleep(400);
  }
  throw new Error(
    `No message to ${recipient} matching ${subjectMatch} within ${timeoutMs}ms`,
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
  const html = await fetchMessageHtml(api, messageId);
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
  await page.click('button[type="submit"]');
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

export async function logout(page: Page): Promise<void> {
  // The Mailpit panel and narration overlay both sit in the corners and
  // intercept clicks on the avatar/drawer if left around.
  await hideMailpitPanel(page);
  await clearNarration(page);
  const avatar = page.locator(".avatar-btn");
  if (await avatar.isVisible().catch(() => false)) {
    await avatar.click();
    await sleep(300);
    await page.click(".drawer-logout");
    await page.waitForURL(/\/login/);
  }
}
