/**
 * Helpers for grouping a call's tasks into ISO weeks (Mon-Sun).
 *
 * Used by the volunteering page to decide whether to show a separate
 * "Week 2" pulldown on the Maximum-tasks selector. Stays pure so it
 * can be unit-tested without the SvelteKit runtime.
 */

/**
 * The Monday of the ISO week containing `iso` (YYYY-MM-DD).
 * Returns null when the date is missing or unparseable.
 *
 * Anchored at local-noon to avoid the same TZ rollback the
 * `formatDate` helper guards against.
 */
function isoWeekMonday(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  if (!/^\d{4}-\d{2}-\d{2}/.test(iso)) return null;
  const d = new Date(iso + "T12:00:00");
  if (isNaN(d.getTime())) return null;
  const dow = d.getDay(); // 0=Sun..6=Sat
  // Number of days back to the Monday of this week:
  //   Sun → 6, Mon → 0, Tue → 1, ..., Sat → 5
  const offsetToMon = dow === 0 ? 6 : dow - 1;
  const monday = new Date(d);
  monday.setDate(d.getDate() - offsetToMon);
  return monday;
}

/** Stable per-week key like "2026-05-11". Same week → same key. */
function weekKey(monday: Date): string {
  const y = monday.getFullYear();
  const m = String(monday.getMonth() + 1).padStart(2, "0");
  const d = String(monday.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Returns true if any of the supplied tasks land in an ISO week
 * after the earliest task's ISO week. Unscheduled tasks are ignored
 * — they don't anchor or extend the span.
 *
 * Used to decide visibility of the "Week 2" Maximum-tasks pulldown:
 * hide it when the call lives entirely in a single week.
 */
export function tasksSpanMultipleWeeks(
  tasks: { date: string | null }[],
): boolean {
  const keys = new Set<string>();
  for (const t of tasks) {
    const mon = isoWeekMonday(t.date);
    if (mon) keys.add(weekKey(mon));
  }
  return keys.size >= 2;
}

/**
 * Bucket each task into "week 1" or "week 2" relative to the call's
 * earliest-dated task. Tasks past week 2 (a rare 3-week call) collapse
 * into week 2 — that bucket effectively means "anything beyond week 1".
 *
 * Returns the week index (1 or 2) or null when the task has no date.
 * Exported for callers that need to color-code or filter tasks per
 * week; not currently used by the volunteering page itself.
 */
export function taskWeekIndex(
  task: { date: string | null },
  tasks: { date: string | null }[],
): 1 | 2 | null {
  const taskMon = isoWeekMonday(task.date);
  if (!taskMon) return null;
  let earliest: Date | null = null;
  for (const t of tasks) {
    const m = isoWeekMonday(t.date);
    if (m && (!earliest || m < earliest)) earliest = m;
  }
  if (!earliest) return null;
  return weekKey(taskMon) === weekKey(earliest) ? 1 : 2;
}
