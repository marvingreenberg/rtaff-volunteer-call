/* eslint-disable @typescript-eslint/no-explicit-any */
export interface Column {
  key: string;
  label: string;
  getValue: (item: any) => string | number;
  sortable?: boolean;
  truncate?: number;
  align?: "left" | "right";
  badgeClass?: (item: any) => string;
  hideOnNarrow?: boolean;
}

export type SortDir = "asc" | "desc";

export function sortItems<T>(
  items: T[],
  columns: Column[],
  sortKey: string,
  sortDir: SortDir,
): T[] {
  const col = columns.find((c) => c.key === sortKey);
  if (!col) return items;

  return [...items].sort((a, b) => {
    const va = col.getValue(a);
    const vb = col.getValue(b);
    let cmp: number;
    if (typeof va === "number" && typeof vb === "number") {
      cmp = va - vb;
    } else {
      cmp = String(va).localeCompare(String(vb), undefined, {
        sensitivity: "base",
      });
    }
    return sortDir === "desc" ? -cmp : cmp;
  });
}

export function nextSortState(
  currentKey: string,
  currentDir: SortDir,
  clickedKey: string,
): { key: string; dir: SortDir } | null {
  if (currentKey !== clickedKey) {
    return { key: clickedKey, dir: "asc" };
  }
  if (currentDir === "asc") {
    return { key: clickedKey, dir: "desc" };
  }
  return null;
}

export function truncateText(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + "\u2026";
}
