<script lang="ts">
  import TaskEntryForm from "./TaskEntryForm.svelte";
  import { formatDate, volunteersLabel } from "$lib/utils/format";
  import type { TaskCreate, TaskResponse } from "$lib/api/client";

  type TeamLead = { id: string; first_name: string; last_name: string };

  type Props = {
    task: TaskResponse;
    expanded: boolean;
    teamLeads?: TeamLead[];
    ontoggle: () => void;
    onupdate: (taskId: string, value: TaskCreate) => Promise<void> | void;
    ondelete: (taskId: string) => void;
  };

  let {
    task,
    expanded,
    teamLeads = [],
    ontoggle,
    onupdate,
    ondelete,
  }: Props = $props();

  // Track the form's most recent payload + dirty flag so the Update button
  // in the summary row can enable/disable correctly and the click handler
  // has something to send. Cleared when the row collapses so reopening the
  // row starts fresh.
  let pendingPayload = $state<TaskCreate | null>(null);
  let dirty = $state(false);
  let saving = $state(false);

  function handleFormChange(value: TaskCreate | null, isDirty: boolean) {
    pendingPayload = value;
    dirty = isDirty;
  }

  $effect(() => {
    if (!expanded) {
      pendingPayload = null;
      dirty = false;
    }
  });

  let canUpdate = $derived(expanded && !!pendingPayload && dirty);

  async function handleUpdateClick(e: MouseEvent) {
    e.stopPropagation();
    if (!canUpdate || !pendingPayload || saving) return;
    saving = true;
    try {
      await onupdate(task.id, pendingPayload);
    } finally {
      saving = false;
    }
  }

  function handleDeleteClick(e: MouseEvent) {
    e.stopPropagation();
    const dateText = task.date
      ? `on ${formatDate(task.date)}`
      : task.short_description;
    if (window.confirm(`Delete task ${dateText}?`)) {
      ondelete(task.id);
    }
  }
</script>

<div class="task-row" class:expanded>
  <div class="summary-row">
    <button
      type="button"
      class="summary"
      aria-expanded={expanded}
      onclick={ontoggle}
    >
      <span class="caret" aria-hidden="true">{expanded ? "▾" : "▸"}</span>
      <span class="date">{task.date ? formatDate(task.date) : "—"}</span>
      <span class="volunteers">
        {volunteersLabel(task.volunteers_needed, task.skilled_needed)}
      </span>
      <span class="city">{task.city ?? ""}</span>
      <span class="description">{task.short_description}</span>
      {#if task.assignees && task.assignees.length > 0}
        <span class="assignees" aria-label="Assigned volunteers">
          {#each task.assignees as a (a.person_id)}
            <span
              class="assignee-chip"
              class:assignee-lead={a.is_team_lead}
              title={`${a.first_name} ${a.last_name}${a.is_team_lead ? " (team lead)" : ""}`}
            >
              {a.initials}
            </span>
          {/each}
        </span>
      {/if}
    </button>
    {#if expanded}
      <button
        type="button"
        class="action-btn"
        disabled={!canUpdate || saving}
        onclick={handleUpdateClick}
        aria-label="Update task"
      >
        {saving ? "Saving..." : "Update"}
      </button>
    {/if}
    <button
      type="button"
      class="trash-btn"
      onclick={handleDeleteClick}
      aria-label="Delete task"
      title="Delete task"
    >
      🗑️
    </button>
  </div>

  {#if expanded}
    <div class="form-wrapper">
      <TaskEntryForm
        initial={task}
        mode="edit"
        {teamLeads}
        onchange={handleFormChange}
      />
    </div>
  {/if}
</div>

<style>
  .task-row {
    border: 1px solid var(--hairline);
    border-radius: var(--radius-sm);
    background: var(--surface-1);
    margin-bottom: var(--sp-3);
    overflow: hidden;
  }

  /* Expanded row reads as one unit: light-green background flowing through
     summary and form, no internal divider. */
  .task-row.expanded {
    background: var(--rt-success-bg);
    border-color: var(--rt-success-text);
  }

  .summary-row {
    display: flex;
    align-items: stretch;
  }

  .summary {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    flex: 1;
    min-width: 0;
    padding: var(--sp-3) var(--sp-4);
    background: none;
    border: none;
    cursor: pointer;
    font: inherit;
    color: inherit;
    text-align: left;
    min-height: var(--btn-min-height);
  }

  .task-row:not(.expanded) .summary:hover {
    background: var(--surface-2);
  }

  /* Assignee chips — compact initials beside the description so an admin
     can see "who's on this task" without expanding. Team lead is the dark
     pill, regular volunteers are light. */
  .assignees {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: auto;
    flex-wrap: wrap;
  }

  .assignee-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 24px;
    padding: 0 6px;
    border-radius: 12px;
    background: var(--surface-3);
    color: var(--rt-text-light);
    font-size: 11px;
    font-weight: 600;
    line-height: 1;
    border: 1px solid var(--hairline);
  }

  .assignee-chip.assignee-lead {
    background: var(--color-primary);
    color: #fff;
    border-color: var(--color-primary);
  }

  .action-btn {
    align-self: center;
    margin-right: var(--sp-3);
    padding: var(--sp-2) var(--sp-4);
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    min-height: 32px;
    flex-shrink: 0;
  }

  .action-btn:disabled {
    background: var(--rt-gray-200);
    color: var(--rt-text-muted);
    cursor: not-allowed;
  }

  .action-btn:not(:disabled):hover {
    opacity: 0.9;
  }

  .trash-btn {
    background: none;
    border: none;
    padding: 0 var(--sp-4);
    font-size: 1.2em;
    line-height: 1;
    cursor: pointer;
    flex-shrink: 0;
    color: var(--rt-text-muted);
  }

  .trash-btn:hover {
    background: var(--rt-error-bg);
  }

  .caret {
    width: 1em;
    color: var(--rt-text-muted);
    flex-shrink: 0;
  }

  .date {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    flex-shrink: 0;
  }

  .volunteers {
    color: var(--rt-text-muted);
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
  }

  .city {
    flex-shrink: 0;
    color: var(--rt-text-muted);
  }

  .description {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .form-wrapper {
    padding: var(--sp-4);
  }
</style>
