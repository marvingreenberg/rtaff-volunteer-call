import { describe, expect, it } from "vitest";
import { truncateOnWord } from "./truncate";

describe("truncateOnWord", () => {
  it("returns input unchanged when length is at or below the limit", () => {
    expect(truncateOnWord("Short text", 65)).toBe("Short text");
    expect(truncateOnWord("x".repeat(65), 65)).toBe("x".repeat(65));
  });

  it("truncates at a word boundary and appends an ellipsis when over the limit", () => {
    const input = "Stage driftwood pulled from the upper beach into the sort pile by the lot";
    const out = truncateOnWord(input, 65);
    expect(out.endsWith("…")).toBe(true);
    expect(out.length).toBeLessThanOrEqual(66); // 65 + the ellipsis itself
    // Last char before … should be a word char (no trailing space before the ellipsis)
    expect(out.slice(-2, -1)).toMatch(/\S/);
    // Reconstructed prefix must be a prefix of the input
    expect(input.startsWith(out.slice(0, -1))).toBe(true);
  });

  it("collapses internal whitespace runs and respects multi-line input", () => {
    const input =
      "Line one continues\n\nLine two is also long enough to push past sixty-five characters total";
    const out = truncateOnWord(input, 65);
    expect(out.endsWith("…")).toBe(true);
    expect(out).not.toContain("\n");
  });

  it("falls back to a hard cut when no word boundary exists below the limit", () => {
    const input = "a".repeat(200);
    const out = truncateOnWord(input, 65);
    expect(out).toBe("a".repeat(65) + "…");
  });

  it("trims leading/trailing whitespace before measuring", () => {
    expect(truncateOnWord("   short   ", 65)).toBe("short");
  });
});
