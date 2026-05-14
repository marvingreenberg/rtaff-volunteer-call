/**
 * Demo-only helpers: narration overlay, Mailpit integration, bulk
 * subprocess invocation. Imported by demo.spec.ts.
 */

import { execFile } from "node:child_process";
import * as path from "node:path";
import { promisify } from "node:util";
import type { APIRequestContext, Page } from "@playwright/test";

const execFileP = promisify(execFile);

export const BASE_URL = process.env.BASE_URL || "http://localhost:5173";
export const MAILPIT_URL = process.env.MAILPIT_URL || "http://localhost:8025";
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// Narration overlay
// ---------------------------------------------------------------------------

export async function injectNarrationOverlay(page: Page): Promise<void> {
  await page.evaluate(() => {
    if (document.getElementById("__demo_narrator__")) return;
    const div = document.createElement("div");
    div.id = "__demo_narrator__";
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
  });
}

export async function narrate(
  page: Page,
  text: string,
  holdMs = 1700,
): Promise<void> {
  await injectNarrationOverlay(page);
  await page.evaluate((t) => {
    const div = document.getElementById("__demo_narrator__");
    if (!div) return;
    div.textContent = t;
    (div as HTMLElement).style.opacity = "1";
  }, text);
  await sleep(holdMs);
}

export async function clearNarration(page: Page): Promise<void> {
  await page.evaluate(() => {
    const div = document.getElementById("__demo_narrator__");
    if (div) (div as HTMLElement).style.opacity = "0";
  });
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
  const m = html.match(/href="([^"]*\/verify\?token=[^"]+)"/);
  if (!m) throw new Error("No /verify link found in message HTML");
  return m[1].replace(/&amp;/g, "&");
}

/**
 * Pin a Mailpit message view onto the right side of the app page as an
 * iframe, so the recorded video shows the email arriving without context
 * switching. The panel persists until hideMailpitPanel is called.
 */
export async function showMailpitPanel(
  page: Page,
  messageId: string,
): Promise<void> {
  await page.evaluate(
    ({ id, base }) => {
      const existing = document.getElementById("__demo_mailpit__");
      if (existing) existing.remove();
      const panel = document.createElement("div");
      panel.id = "__demo_mailpit__";
      panel.style.cssText = [
        "position:fixed",
        "top:16px",
        "right:16px",
        "width:620px",
        "height:78vh",
        "background:#fff",
        "border:2px solid #003a5d",
        "border-radius:10px",
        "box-shadow:0 18px 48px rgba(0,0,0,.28)",
        "overflow:hidden",
        "z-index:2147483646",
      ].join(";");
      const header = document.createElement("div");
      header.style.cssText =
        "background:#003a5d;color:#fff;padding:10px 16px;font:600 15px/1 system-ui;";
      header.textContent = "📬 Mailpit — incoming email";
      panel.appendChild(header);
      const iframe = document.createElement("iframe");
      iframe.src = `${base}/view/${id}.html`;
      iframe.style.cssText =
        "width:100%;height:calc(100% - 40px);border:0;background:#fff;";
      panel.appendChild(iframe);
      document.body.appendChild(panel);
    },
    { id: messageId, base: MAILPIT_URL },
  );
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
    await showMailpitPanel(page, msg.ID);
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
  const avatar = page.locator(".avatar-btn");
  if (await avatar.isVisible().catch(() => false)) {
    await avatar.click();
    await sleep(300);
    await page.click(".drawer-logout");
    await page.waitForURL(/\/login/);
  }
}
