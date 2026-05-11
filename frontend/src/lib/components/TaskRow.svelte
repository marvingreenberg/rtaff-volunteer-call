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
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    background: var(--rt-white, #ffffff);
    margin-bottom: var(--spacing-sm);
    overflow: hidden;
  }

  /* Expanded row reads as one unit: light-green background flowing through
     summary and form, no internal divider. */
  .task-row.expanded {
    background: var(--rt-success-bg, #e6f4ea);
    border-color: var(--rt-success-text, #2f7a45);
  }

  .summary-row {
    display: flex;
    align-items: stretch;
  }

  .summary {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex: 1;
    min-width: 0;
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    cursor: pointer;
    font: inherit;
    color: inherit;
    text-align: left;
    min-height: var(--btn-min-height);
  }

  .task-row:not(.expanded) .summary:hover {
    background: var(--rt-gray-100, #f5f3ef);
  }

  .action-btn {
    align-self: center;
    margin-right: var(--spacing-sm);
    padding: var(--spacing-xs) var(--spacing-md);
    background: var(--color-primary, #3a6db5);
    color: white;
    border: none;
    border-radius: var(--card-radius);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    min-height: 32px;
    flex-shrink: 0;
  }

  .action-btn:disabled {
    background: var(--rt-gray-200, #e4dfda);
    color: var(--rt-text-muted, #888);
    cursor: not-allowed;
  }

  .action-btn:not(:disabled):hover {
    opacity: 0.9;
  }

  .trash-btn {
    background: none;
    border: none;
    padding: 0 var(--spacing-md);
    font-size: 1.2em;
    line-height: 1;
    cursor: pointer;
    flex-shrink: 0;
    color: var(--rt-text-muted, #888);
  }

  .trash-btn:hover {
    background: var(--rt-danger-bg, #fdecea);
  }

  .caret {
    width: 1em;
    color: var(--rt-text-muted, #777);
    flex-shrink: 0;
  }

  .date {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    flex-shrink: 0;
  }

  .volunteers {
    color: var(--rt-text-muted, #777);
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
  }

  .city {
    flex-shrink: 0;
    color: var(--rt-text-muted, #777);
  }

  .description {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .form-wrapper {
    padding: var(--spacing-md);
  }
</style>
