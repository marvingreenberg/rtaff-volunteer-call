import { describe, it, expect, vi, beforeEach } from "vitest";
import { authState, initFromToken, login } from "./auth.svelte";

vi.mock("$lib/api/client", () => ({
  auth: {
    me: vi.fn(),
    login: vi.fn(),
  },
}));

import { auth } from "$lib/api/client";

beforeEach(() => {
  authState.user = null;
  authState.loading = true;
  authState.error = null;
  vi.mocked(auth.me).mockReset();
  if (typeof localStorage !== "undefined") {
    localStorage.removeItem("vcall_token");
  }
});

describe("initFromToken", () => {
  it("returns null and sets loading false when no token", async () => {
    const result = await initFromToken(null);
    expect(result).toBeNull();
    expect(authState.loading).toBe(false);
    expect(authState.user).toBeNull();
  });

  it("calls auth.me with token and sets user on success", async () => {
    const mockPerson = {
      id: "p1",
      first_name: "Jane",
      last_name: "Doe",
      skill_category: "skilled",
      active: true,
      roles: ["volunteer"],
    };
    vi.mocked(auth.me).mockResolvedValue(mockPerson as any);

    const result = await initFromToken("test-token");
    expect(auth.me).toHaveBeenCalledWith("test-token");
    expect(result).toEqual(mockPerson);
    expect(authState.user).toEqual(mockPerson);
    expect(authState.loading).toBe(false);
    expect(authState.error).toBeNull();
  });

  it("sets error on failure", async () => {
    vi.mocked(auth.me).mockRejectedValue(new Error("401"));

    const result = await initFromToken("bad-token");
    expect(result).toBeNull();
    expect(authState.user).toBeNull();
    expect(authState.error).toContain("Invalid or expired");
    expect(authState.loading).toBe(false);
  });

  it("stores token in localStorage on success", async () => {
    vi.mocked(auth.me).mockResolvedValue({ id: "p1" } as any);
    await initFromToken("persist-token");
    expect(localStorage.getItem("vcall_token")).toBe("persist-token");
  });

  it("removes token from localStorage on failure", async () => {
    localStorage.setItem("vcall_token", "old-token");
    vi.mocked(auth.me).mockRejectedValue(new Error("401"));
    await initFromToken("old-token");
    expect(localStorage.getItem("vcall_token")).toBeNull();
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
    // demoToken must be populated so the login page can redirect to /verify.
    expect(result.demoToken).toBe("demo-token-abc");
  });
});
