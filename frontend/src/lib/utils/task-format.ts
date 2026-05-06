/** Format an ISO YYYY-MM-DD as MM/DD. Returns "—" when null/blank. */
export function formatMonthDay(d: string | null | undefined): string {
  if (!d) return "—";
  const [, m, day] = d.split("-");
  if (!m || !day) return "—";
  return `${m}/${day}`;
}

/**
 * Compact "(N)" or "(N/M)" volunteer-needed label. The slashed form only
 * appears when the skilled count is positive.
 */
export function volunteersLabel(needed: number, skilled: number): string {
  return skilled > 0 ? `(${needed}/${skilled})` : `(${needed})`;
}
