<script lang="ts">
  import TaskEntryForm from "./TaskEntryForm.svelte";
  import { formatDate, volunteersLabel } from "$lib/utils/format";
  import type { TaskCreate, TaskResponse } from "$lib/api/client";

  type Props = {
    task: TaskResponse;
    expanded: boolean;
    ontoggle: () => void;
    onchange: (taskId: string, value: TaskCreate | null, dirty: boolean) => void;
    ondelete: (taskId: string) => void;
  };

  let { task, expanded, ontoggle, onchange, ondelete }: Props = $props();

  function handleDeleteClick(e: MouseEvent) {
    e.stopPropagation();
    if (confirm(`Delete task "${task.short_description}"?`)) {
      ondelete(task.id);
    }
  }
</script>

<div class="task-row" class:expanded>
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
    <div class="form-wrapper">
      <TaskEntryForm
        initial={task}
        mode="edit"
        onchange={(value, dirty) => onchange(task.id, value, dirty)}
      />
      <div class="row-actions">
        <button
          type="button"
          class="delete-btn"
          onclick={handleDeleteClick}
          aria-label="Delete task"
        >
          Delete task
        </button>
      </div>
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

  .summary {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
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

  .row-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: var(--spacing-sm);
  }

  .delete-btn {
    background: none;
    border: 1px solid var(--rt-danger-text, #b00020);
    color: var(--rt-danger-text, #b00020);
    border-radius: var(--card-radius);
    padding: var(--spacing-xs) var(--spacing-sm);
    font: inherit;
    font-size: var(--font-size-sm);
    cursor: pointer;
  }

  .delete-btn:hover {
    background: var(--rt-danger-bg, #fdecea);
  }
</style>
