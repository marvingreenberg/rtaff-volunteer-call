/**
 * Canonical date display: "Monday, May 11".
 *
 * One formatter used everywhere in the UI (and matched by `_format_date`
 * in backend/services/notifications.py for emails). Accepts:
 *  - ISO date strings ("2025-05-11"), parsed as local-noon to dodge timezone
 *    rollover so a date never displays as the day before.
 *  - Full ISO timestamps ("2025-05-11T10:30:00Z"), parsed natively.
 */
export function formatDate(d: string | null | undefined): string {
  if (!d) return "";
  const dateObj = d.includes("T") ? new Date(d) : new Date(d + "T12:00:00");
  if (isNaN(dateObj.getTime())) return "";
  return dateObj.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

/** Format an area key like "living_room" to "Living Room" */
export function formatArea(area: string): string {
  return area
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Group items with an `area` field by formatted area name */
export function groupByArea<T extends { area: string }>(
  items: T[],
): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  for (const item of items) {
    const key = formatArea(item.area);
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }
  return groups;
}

/** Format a number as currency ("$12.50") */
export function formatCurrency(amount: number): string {
  return "$" + Number(amount).toFixed(2);
}

/**
 * Compact "(N)" or "(N/M)" volunteer-needed label. The slashed form only
 * appears when the skilled count is positive.
 */
export function volunteersLabel(needed: number, skilled: number): string {
  return skilled > 0 ? `(${needed}/${skilled})` : `(${needed})`;
}
