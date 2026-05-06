/** Format a date string for display (short format: "Jan 15, 2025") */
export function formatDate(d: string | null): string {
  if (!d) return "";
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Format a date with weekday ("Mon, Jan 15, 2025") */
export function formatDateFull(d: string | null): string {
  if (!d) return "";
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Format a date short, no year ("Jan 15") */
export function formatDateShort(d: string | null): string {
  if (!d) return "";
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
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
