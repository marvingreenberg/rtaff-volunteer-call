<script lang="ts">
  /**
   * Matrix view of assignments: tasks across the top (ASC date), responding
   * volunteers down the left (first-name alphabetical). Each cell is one of:
   *   ✓ assigned    — click to unassign
   *   □ available   — click to assign
   *   × unavailable — no interaction
   * Plus annotations:
   *   🛠️ skill-match (task has skilled_needed > 0 and volunteer has skills)
   *   ‼️ same-date conflict (this cell + at least one other are flagged)
   *   🥵 row-level: at weekly cap
   *   😴 row-level: idle quartile within the responding pool
   *
   * All click handlers come in via props so the parent owns the
   * single-source-of-truth overview + API mutations.
   */
  import { formatDate } from "$lib/utils/format";
  import {
    buildFairnessContext,
    badgesFor,
    spreadsheetConflictKeys,
  } from "$lib/utils/assignment-fairness";
  import type {
    AssignmentOverviewResponse,
    AvailableVolunteer,
    TaskAssignment,
    TaskOverviewItem,
    VolunteerOverviewItem,
  } from "$lib/api/types";

  // TaskOverviewItem is referenced by the type annotation on the cell-state
  // discriminated union; silence the unused-import linter via a no-op cast.
  type _UsedAlias = TaskOverviewItem;

  interface Props {
    overview: AssignmentOverviewResponse;
    busyTaskIds: Set<string>;
    onAssign: (
      taskId: string,
      candidate: AvailableVolunteer,
      isConflictOverride: boolean,
    ) => void;
    onUnassign: (taskId: string, assignment: TaskAssignment) => void;
  }
  let { overview, busyTaskIds, onAssign, onUnassign }: Props = $props();

  let fairness = $derived(
    buildFairnessContext(overview.volunteers, overview.tasks),
  );

  type CellState =
    | { kind: "assigned"; assignment: TaskAssignment }
    | { kind: "available"; candidate: AvailableVolunteer }
    | { kind: "unavailable" };

  /** Per-row index: person_id → (task_id → cell). Computed once per render. */
  let cellMatrix = $derived.by(() => {
    const out = new Map<string, Map<string, CellState>>();
    for (const v of overview.volunteers) {
      out.set(v.person_id, new Map());
    }
    for (const t of overview.tasks) {
      for (const a of t.assignments) {
        const row = out.get(a.person_id);
        if (row) row.set(t.task_id, { kind: "assigned", assignment: a });
      }
      const assignedIds = new Set(t.assignments.map((a) => a.person_id));
      for (const c of t.available_volunteers) {
        if (assignedIds.has(c.person_id)) continue;
        const row = out.get(c.person_id);
        if (row) row.set(t.task_id, { kind: "available", candidate: c });
      }
    }
    // Fill in unavailable for cells with no entry.
    for (const v of overview.volunteers) {
      const row = out.get(v.person_id)!;
      for (const t of overview.tasks) {
        if (!row.has(t.task_id)) {
          row.set(t.task_id, { kind: "unavailable" });
        }
      }
    }
    return out;
  });

  let conflictKeys = $derived(spreadsheetConflictKeys(overview.tasks));

  function cellState(person: VolunteerOverviewItem, task: TaskOverviewItem): CellState {
    return cellMatrix.get(person.person_id)?.get(task.task_id) ?? { kind: "unavailable" };
  }

  function isConflict(person: VolunteerOverviewItem, task: TaskOverviewItem): boolean {
    return conflictKeys.has(`${person.person_id}|${task.task_id}`);
  }

  function clickCell(person: VolunteerOverviewItem, task: TaskOverviewItem) {
    if (busyTaskIds.has(task.task_id)) return;
    const cell = cellState(person, task);
    if (cell.kind === "unavailable") return;
    if (cell.kind === "assigned") {
      onUnassign(task.task_id, cell.assignment);
      return;
    }
    // Available — check if assigning would create a same-date conflict with
    // an *existing* assignment for this person on the same date.
    const conflictExists =
      task.date != null &&
      overview.tasks.some(
        (other) =>
          other.task_id !== task.task_id &&
          other.date === task.date &&
          other.assignments.some((a) => a.person_id === person.person_id),
      );
    onAssign(task.task_id, cell.candidate, conflictExists);
  }
</script>

<div class="spreadsheet">
  <table class="grid">
    <thead>
      <tr>
        <th class="corner" scope="col"></th>
        {#each overview.tasks as task (task.task_id)}
          <th class="task-header" scope="col" title={task.short_description}>
            <div class="task-date">{task.date ? formatDate(task.date) : "—"}</div>
            <div class="task-city">{task.city ?? ""}</div>
            <div class="task-desc">{task.short_description}</div>
            <div class="task-progress">
              {task.assignments.length}/{task.volunteers_needed}
            </div>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each overview.volunteers as person (person.person_id)}
        {@const rowExhausted = person.assignments_this_call >= person.max_tasks_per_week}
        {@const rowIdle = fairness.idleQuartile.has(person.person_id)}
        <tr>
          <th class="row-header" scope="row" title={person.person_name}>
            <span class="row-name">{person.first_name} {person.last_name[0] ?? ""}.</span>
            {#if rowExhausted}<span class="fairness-badge" title="At weekly cap">🥵</span>{/if}
            {#if rowIdle}<span class="fairness-badge" title="Idle">😴</span>{/if}
          </th>
          {#each overview.tasks as task (task.task_id)}
            {@const cell = cellState(person, task)}
            {@const conflict = isConflict(person, task)}
            {@const b = badgesFor(person.person_id, task, fairness)}
            <td
              class="cell {cell.kind}"
              class:conflict
              class:skill={b.skilled && cell.kind !== "unavailable"}
              title={cell.kind === "assigned"
                ? `Assigned: ${person.person_name} → ${task.short_description}${conflict ? " ‼️ Same-day conflict" : ""}`
                : cell.kind === "available"
                  ? `Available: ${person.person_name} for ${task.short_description}`
                  : `Not available`}
            >
              {#if cell.kind !== "unavailable"}
                <button
                  type="button"
                  class="cell-btn {cell.kind}"
                  disabled={busyTaskIds.has(task.task_id)}
                  aria-label={cell.kind === "assigned"
                    ? `Unassign ${person.person_name} from ${task.short_description}`
                    : `Assign ${person.person_name} to ${task.short_description}`}
                  onclick={() => clickCell(person, task)}
                >
                  {#if cell.kind === "assigned"}✓{:else}□{/if}
                  {#if conflict}<span class="cell-mark" aria-hidden="true">‼️</span>{/if}
                  {#if b.skilled}<span class="cell-mark" aria-hidden="true">🛠️</span>{/if}
                </button>
              {:else}
                <span class="cell-x" aria-hidden="true">×</span>
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .spreadsheet {
    overflow: auto;
    max-height: 70vh;
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    background: var(--rt-white, #fff);
  }

  table.grid {
    border-collapse: separate;
    border-spacing: 0;
    font-size: var(--font-size-sm);
  }

  thead th {
    position: sticky;
    top: 0;
    background: var(--rt-bg-subtle, #f9f7f2);
    z-index: 2;
    border-bottom: 2px solid var(--rt-gray-200, #e4dfda);
    padding: 8px 10px;
    font-weight: 600;
    text-align: left;
    min-width: 120px;
    max-width: 160px;
    vertical-align: top;
  }

  th.corner,
  th.row-header {
    position: sticky;
    left: 0;
    background: var(--rt-bg-subtle, #f9f7f2);
    z-index: 1;
    text-align: left;
    padding: 8px 12px;
    min-width: 180px;
    border-right: 2px solid var(--rt-gray-200, #e4dfda);
  }

  th.corner {
    z-index: 3;
  }

  .task-date {
    font-weight: 600;
    color: var(--color-text);
  }
  .task-city {
    color: var(--rt-text-muted, #777);
    font-size: var(--font-size-xs);
  }
  .task-desc {
    color: var(--rt-text-light, #555);
    font-size: var(--font-size-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .task-progress {
    margin-top: 4px;
    color: var(--rt-text-muted, #777);
    font-variant-numeric: tabular-nums;
    font-size: var(--font-size-xs);
  }

  .row-header {
    font-weight: 500;
  }
  .row-name {
    margin-right: 4px;
  }

  td.cell {
    border-bottom: 1px solid var(--rt-gray-100, #f1efea);
    border-right: 1px solid var(--rt-gray-100, #f1efea);
    padding: 0;
    text-align: center;
    vertical-align: middle;
    width: 64px;
    min-width: 64px;
    height: 40px;
  }

  td.cell.unavailable {
    background: var(--rt-gray-50, #fafaf7);
    color: var(--rt-text-muted, #aaa);
  }

  td.cell.available {
    background: rgba(58, 109, 181, 0.08);
  }

  td.cell.assigned {
    background: rgba(47, 122, 69, 0.18);
  }

  td.cell.conflict {
    outline: 2px solid var(--rt-warning-text, #b35900);
    outline-offset: -2px;
  }

  .cell-btn {
    width: 100%;
    height: 100%;
    border: 0;
    background: transparent;
    cursor: pointer;
    font-size: 1.1em;
    line-height: 1;
    color: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 2px;
  }

  .cell-btn.assigned {
    color: var(--rt-success-text, #2f7a45);
    font-weight: 700;
  }

  .cell-btn:disabled {
    cursor: progress;
    opacity: 0.6;
  }

  .cell-x {
    color: var(--rt-text-muted, #bbb);
  }

  .cell-mark {
    font-size: 0.8em;
  }

  .fairness-badge {
    font-size: 0.95em;
    margin-left: 2px;
  }
</style>
