<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import {
    volunteerCalls,
    type VolunteerCallResponse,
    type TaskCreate,
  } from '$lib/api/client';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import TaskEntryForm from '$lib/components/TaskEntryForm.svelte';
  import TaskRow from '$lib/components/TaskRow.svelte';
  import { callStatusBadgeClass, programLabel } from '$lib/utils/badges';
  import { SINGLE_TASK_PROGRAMS } from '$lib/api/types';

  let call = $state<VolunteerCallResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  // The currently-open task row (at most one). Collapsing without clicking
  // Update silently discards in-flight edits — Update is explicit.
  let expandedTaskId: string | null = $state(null);
  // Whether the "- Add task to Project -" affordance has been expanded into
  // the entry form.
  let addOpen = $state(false);

  let callId = $derived(page.params.id!);
  let isSingleTaskProgram = $derived(call ? SINGLE_TASK_PROGRAMS.has(call.program) : false);

  onMount(loadCall);

  async function loadCall() {
    loading = true;
    error = null;
    try {
      call = await volunteerCalls.get(callId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load volunteer call';
    } finally {
      loading = false;
    }
  }

  function handleRowChange(_taskId: string, _value: TaskCreate | null, _dirty: boolean) {
    // Edit-mode autosave is gone — the row's TaskEntryForm fires onchange
    // for free; we ignore it. Saving happens through onupdate.
  }

  async function handleRowUpdate(taskId: string, value: TaskCreate) {
    error = null;
    try {
      await volunteerCalls.updateTask(callId, taskId, value);
      expandedTaskId = null;
      await loadCall();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save task';
    }
  }

  function handleToggleRow(taskId: string) {
    expandedTaskId = expandedTaskId === taskId ? null : taskId;
  }

  async function handleAddTask(data: TaskCreate) {
    error = null;
    try {
      await volunteerCalls.addTask(callId, data);
      addOpen = false;
      await loadCall();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to add task';
      throw e;
    }
  }

  async function handleDeleteTask(taskId: string) {
    error = null;
    try {
      if (expandedTaskId === taskId) expandedTaskId = null;
      await volunteerCalls.deleteTask(callId, taskId);
      await loadCall();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete task';
    }
  }
</script>

<svelte:head>
  <title>{call?.title || 'Volunteer Call'} - RT-AFF</title>
</svelte:head>

<div class="call-detail page-md">
  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if loading}
    <p class="loading">Loading...</p>
  {:else if call}
    <Breadcrumb crumbs={[{label: 'Volunteering', href: '/volunteering'}, {label: 'Volunteer Calls', href: '/volunteer-calls'}, {label: call?.title || 'Call'}]} />
    <div class="call-header">
      <h1>{call.title}</h1>
      <span class="program-tag">{programLabel(call.program)}</span>
      <span class="badge {callStatusBadgeClass(call.status)}">{call.status}</span>
    </div>

    {#if call.notes}
      <div class="call-info">
        <dl>
          <dt>Notes</dt>
          <dd>{call.notes}</dd>
        </dl>
      </div>
    {/if}

    <div class="section">
      <div class="section-header">
        <h2>{isSingleTaskProgram ? `Task (${programLabel(call.program)})` : `Tasks (${call.task_count})`}</h2>
      </div>

      {#if call.tasks.length > 0}
        <div class="task-list">
          {#each call.tasks as task (task.id)}
            <TaskRow
              {task}
              expanded={expandedTaskId === task.id}
              ontoggle={() => handleToggleRow(task.id)}
              onchange={handleRowChange}
              onupdate={handleRowUpdate}
              ondelete={handleDeleteTask}
            />
          {/each}
        </div>
      {/if}

      {#if call.status !== 'closed' && !isSingleTaskProgram}
        {#if addOpen}
          <div class="task-row task-row-add expanded">
            <div class="form-wrapper">
              <TaskEntryForm submitLabel="Done" onsubmit={handleAddTask} />
            </div>
          </div>
        {:else}
          <button type="button" class="add-task-label" onclick={() => (addOpen = true)}>
            - Add task to Project -
          </button>
        {/if}
      {:else if call.tasks.length === 0}
        <p class="empty">No tasks yet.</p>
      {/if}
    </div>
  {/if}

</div>

<style>
  .call-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
  }

  .call-header h1 {
    margin: 0;
  }

  .program-tag {
    padding: 2px var(--spacing-sm);
    background: var(--rt-bg-subtle, #f9f7f2);
    color: var(--rt-text-muted, #777);
    border: 1px solid var(--rt-gray-200);
    border-radius: 10px;
    font-size: var(--font-size-sm);
    font-weight: 500;
  }

  .call-info {
    margin-bottom: var(--spacing-md);
  }

  .call-info dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--spacing-xs) var(--spacing-md);
    margin: 0;
  }

  .call-info dt {
    font-weight: 600;
    color: var(--rt-text-light, #555);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .section-header h2 {
    margin: 0;
  }

  .task-list {
    display: flex;
    flex-direction: column;
  }

  /* "- Add task to Project -" affordance. Renders as a green italic label
     that behaves like a button. */
  .add-task-label {
    display: block;
    margin-top: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    color: var(--rt-success-text, #2f7a45);
    font: inherit;
    font-style: italic;
    font-weight: 600;
    text-decoration: underline;
    cursor: pointer;
    text-align: left;
  }

  .add-task-label:hover {
    color: var(--color-primary, #3a6db5);
  }

  /* The expanded add card reuses the same green panel styling as TaskRow's
     expanded state. */
  .task-row-add {
    border: 1px solid var(--rt-success-text, #2f7a45);
    border-radius: var(--card-radius);
    background: var(--rt-success-bg, #e6f4ea);
    margin-top: var(--spacing-md);
    overflow: hidden;
  }

  .task-row-add .form-wrapper {
    padding: var(--spacing-md);
  }

  .badge-draft {
    background: var(--rt-gray-100, #f5f3ef);
    color: var(--rt-text-muted, #777);
  }

  .badge-open {
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
  }

  .badge-closed {
    background: var(--rt-error-bg, #fce8e8);
    color: var(--rt-error, #c53030);
  }

  .badge-full {
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
  }

  .badge-cancelled {
    background: var(--rt-error-bg, #fce8e8);
    color: var(--rt-error, #c53030);
  }

  @media (max-width: 768px) {
    .call-header {
      flex-direction: column;
      align-items: flex-start;
    }

    .section-header {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
