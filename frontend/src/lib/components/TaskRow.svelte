<script lang="ts">
  import TaskEntryForm from "./TaskEntryForm.svelte";
  import { formatDate, volunteersLabel } from "$lib/utils/format";
  import type { TaskCreate, TaskResponse } from "$lib/api/client";

  type Props = {
    task: TaskResponse;
    expanded: boolean;
    ontoggle: () => void;
    onchange: (taskId: string, value: TaskCreate | null, dirty: boolean) => void;
    onupdate: (taskId: string, value: TaskCreate) => Promise<void> | void;
    ondelete: (taskId: string) => void;
  };

  let { task, expanded, ontoggle, onchange, onupdate, ondelete }: Props =
    $props();

  function handleDeleteClick(e: MouseEvent) {
    e.stopPropagation();
    const dateText = task.date ? `on ${formatDate(task.date)}` : task.short_description;
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
    <button
      type="button"
      class="delete-x"
      onclick={handleDeleteClick}
      aria-label="Delete task"
      title="Delete task"
    >
      ×
    </button>
  </div>

  {#if expanded}
    <div class="form-wrapper">
      <TaskEntryForm
        initial={task}
        mode="edit"
        onchange={(value, dirty) => onchange(task.id, value, dirty)}
        onupdate={(value) => onupdate(task.id, value)}
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

  .delete-x {
    background: none;
    border: none;
    padding: 0 var(--spacing-md);
    color: var(--rt-text-muted, #888);
    font-size: 1.4em;
    line-height: 1;
    cursor: pointer;
    flex-shrink: 0;
  }

  .delete-x:hover {
    color: var(--rt-danger-text, #b00020);
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
    /* No top border or background change — the form sits on the same green
       canvas as the summary. */
  }
</style>
