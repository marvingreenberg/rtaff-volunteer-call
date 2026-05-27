import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  authState,
  consumeInvitedCallId,
  initFromToken,
  login,
  verify,
} from "./auth.svelte";

vi.mock("$lib/api/client", () => ({
  auth: {
    me: vi.fn(),
    login: vi.fn(),
    verify: vi.fn(),
    logout: vi.fn(),
  },
}));

import { auth } from "$lib/api/client";

beforeEach(() => {
  authState.user = null;
  authState.loading = true;
  authState.error = null;
  // Flush any leaked invite id from a prior test.
  consumeInvitedCallId();
  vi.mocked(auth.me).mockReset();
  vi.mocked(auth.verify).mockReset();
});

describe("initFromToken", () => {
  it("hits /auth/me with no token when cookie should already be present", async () => {
    vi.mocked(auth.me).mockResolvedValue({ id: "p1" } as any);
    const result = await initFromToken(null);
    expect(auth.me).toHaveBeenCalledWith(undefined);
    expect(result).toEqual({ id: "p1" });
    expect(authState.loading).toBe(false);
  });

  it("passes urlToken to /auth/me to bootstrap the cookie", async () => {
    vi.mocked(auth.me).mockResolvedValue({ id: "p1" } as any);
    await initFromToken("magic-link-token");
    expect(auth.me).toHaveBeenCalledWith("magic-link-token");
    expect(authState.user).toEqual({ id: "p1" });
  });

  it("sets error only when a urlToken was supplied and rejected", async () => {
    vi.mocked(auth.me).mockRejectedValue(new Error("401"));
    await initFromToken("bad-token");
    expect(authState.error).toContain("Invalid or expired");
  });

  it("does not set error when no urlToken (cookie absent is not an error)", async () => {
    vi.mocked(auth.me).mockRejectedValue(new Error("401"));
    await initFromToken(null);
    expect(authState.user).toBeNull();
    expect(authState.error).toBeNull();
  });
});

describe("verify", () => {
  it("captures invited_call_id for the deep-link consumer to read once", async () => {
    vi.mocked(auth.verify).mockResolvedValue({
      person: { id: "p1" } as any,
      invited_call_id: "call-42",
    });
    await verify("invite-jwt");
    expect(consumeInvitedCallId()).toBe("call-42");
    // Second read returns null — the value is single-use.
    expect(consumeInvitedCallId()).toBeNull();
  });
});

describe("login", () => {
  it("returns null demoToken in normal mode so the page shows 'check email'", async () => {
    vi.mocked(auth.login).mockResolvedValue({
      message: "Magic link sent!",
    } as any);
    const result = await login("user@example.com");
    expect(result).toEqual({ message: "Magic link sent!", demoToken: null });
  });

  it("surfaces demo_token from the response when DEMO_MODE is on", async () => {
    vi.mocked(auth.login).mockResolvedValue({
      message: "Demo mode — logging in directly.",
      demo_token: "demo-token-abc",
    } as any);
    const result = await login("sarah@rtaff.org");
    expect(result.demoToken).toBe("demo-token-abc");
  });
});
