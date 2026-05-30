import { describe, it, expect } from "vitest";
import { urlWithoutToken, hasToken } from "./auth-url";

describe("urlWithoutToken", () => {
  it("removes the token param", () => {
    // Catches a regression that leaves the JWT in the URL after login.
    const out = urlWithoutToken(
      new URL("https://app.test/verify?token=abc.def.ghi"),
    );
    expect(out.searchParams.has("token")).toBe(false);
    expect(out.pathname).toBe("/verify");
  });

  it("preserves other query params", () => {
    // Catches a regression that nukes the whole query string (e.g.
    // dropping returnTo or a deep-link param alongside the token).
    const out = urlWithoutToken(
      new URL("https://app.test/volunteering?token=abc&returnTo=%2Fcalls"),
    );
    expect(out.searchParams.has("token")).toBe(false);
    expect(out.searchParams.get("returnTo")).toBe("/calls");
  });

  it("is a no-op when there is no token", () => {
    // Catches a regression that mangles a clean URL.
    const out = urlWithoutToken(new URL("https://app.test/volunteering?x=1"));
    expect(out.toString()).toBe("https://app.test/volunteering?x=1");
  });

  it("does not mutate the input URL", () => {
    // Catches deleting the param on the caller's live page.url object.
    const input = new URL("https://app.test/verify?token=abc");
    urlWithoutToken(input);
    expect(input.searchParams.get("token")).toBe("abc");
  });
});

describe("hasToken", () => {
  it("true when a token param is present", () => {
    expect(hasToken(new URL("https://app.test/verify?token=abc"))).toBe(true);
  });

  it("false when absent", () => {
    // Catches scrubbing/replacing history on every page load, not just
    // token landings.
    expect(hasToken(new URL("https://app.test/volunteering"))).toBe(false);
  });
});
