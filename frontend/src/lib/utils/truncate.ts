/**
 * Truncate `text` to at most `maxChars`, ending at a word boundary, and
 * append a horizontal ellipsis (…) only when truncation actually occurs.
 * Internal whitespace runs (including newlines) collapse to a single space
 * so the summary reads as a one-line preview. If no whitespace exists
 * before `maxChars`, falls back to a hard cut at `maxChars`.
 *
 * `maxChars` counts UTF-16 code units (the JS `String.length` unit), not
 * graphemes. Astral characters (emoji, some CJK) and combining-mark
 * sequences may count as 2+ units each; the cut still respects word
 * boundaries but the resulting display width is approximate for those.
 */
export function truncateOnWord(text: string, maxChars: number): string {
  const normalized = text.trim().replace(/\s+/g, " ");
  if (normalized.length <= maxChars) return normalized;

  const window = normalized.slice(0, maxChars + 1);
  const lastSpace = window.lastIndexOf(" ");
  const cut =
    lastSpace > 0 ? window.slice(0, lastSpace) : window.slice(0, maxChars);
  return `${cut}…`;
}
