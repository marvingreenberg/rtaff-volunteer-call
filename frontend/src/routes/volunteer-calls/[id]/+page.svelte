<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import {
    volunteerCalls,
    people,
    type VolunteerCallResponse,
    type TaskCreate,
  } from '$lib/api/client';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import TaskEntryForm from '$lib/components/TaskEntryForm.svelte';
  import TaskEditorRow from '$lib/components/TaskEditorRow.svelte';
  import { callStatusBadgeClass, programLabel } from '$lib/utils/badges';
  import { SINGLE_TASK_PROGRAMS } from '$lib/api/types';

  type TeamLead = { id: string; first_name: string; last_name: string };

  let call = $state<VolunteerCallResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);
  let teamLeads = $state<TeamLead[]>([]);

  // The currently-open existing-task row (at most one). Collapsing without
  // clicking Update silently discards in-flight edits.
  let expandedTaskId: string | null = $state(null);

  // Whether the "- Add new task -" affordance has been expanded into the
  // entry form. The form is contained in a TaskEditorRow-shaped expando with its
  // own Add + trash buttons in the header strip.
  let addOpen = $state(false);
  let addPayload = $state<TaskCreate | null>(null);
  let addSaving = $state(false);

  let callId = $derived(page.params.id!);
  let isSingleTaskProgram = $derived(call ? SINGLE_TASK_PROGRAMS.has(call.program) : false);

  onMount(async () => {
    await loadCall();
    // Fetch team-lead candidates once for the whole page; pass into every
    // TaskEditorRow + the new-task form rather than re-fetching per row.
    try {
      const leads = await people.list({ role: 'team_leader', active: true });
      teamLeads = leads.items.map((p) => ({
        id: p.id,
        first_name: p.first_name,
        last_name: p.last_name,
      }));
    } catch {
      // Non-fatal — the team-lead select will simply be empty.
    }
  });

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

  function handleAddChange(value: TaskCreate | null) {
    addPayload = value;
  }

  async function handleAddSubmit() {
    if (!addPayload || addSaving) return;
    addSaving = true;
    error = null;
    try {
      await volunteerCalls.addTask(callId, addPayload);
      addOpen = false;
      addPayload = null;
      await loadCall();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to add task';
    } finally {
      addSaving = false;
    }
  }

  function handleAddCancel() {
    addOpen = false;
    addPayload = null;
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

  function handleNoMore() {
    goto('/volunteer-calls');
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
    {@const headerCall = call}
    <PageHeader title={headerCall.title}>
      {#snippet meta()}
        <span class="program-tag">{programLabel(headerCall.program)}</span>
        <span class="badge {callStatusBadgeClass(headerCall.status)}">{headerCall.status}</span>
      {/snippet}
    </PageHeader>

    {#if call.notes}
      <section class="card call-info">
        <h2>Notes</h2>
        <p class="notes-body">{call.notes}</p>
      </section>
    {/if}

    <section class="card task-section">
      <div class="section-header">
        <h2>{isSingleTaskProgram ? `Task (${programLabel(call.program)})` : `Tasks (${call.task_count})`}</h2>
      </div>

      {#if call.tasks.length > 0}
        <div class="task-list">
          {#each call.tasks as task (task.id)}
            <TaskEditorRow
              {task}
              {teamLeads}
              expanded={expandedTaskId === task.id}
              ontoggle={() => handleToggleRow(task.id)}
              onupdate={handleRowUpdate}
              ondelete={handleDeleteTask}
            />
          {/each}
        </div>
      {/if}

      {#if (call.status === 'open' || call.status === 'waiting') && !isSingleTaskProgram}
        {#if addOpen}
          <div class="task-row task-row-add expanded">
            <div class="summary-row">
              <span class="new-task-label">New task</span>
              <button
                type="button"
                class="action-btn"
                data-testid="task-add-submit"
                disabled={!addPayload || addSaving}
                onclick={handleAddSubmit}
              >
                {addSaving ? 'Saving...' : 'Add'}
              </button>
              <button
                type="button"
                class="trash-btn"
                onclick={handleAddCancel}
                aria-label="Discard new task"
                title="Discard new task"
              >
                🗑️
              </button>
            </div>
            <div class="form-wrapper">
              <TaskEntryForm {teamLeads} onchange={handleAddChange} />
            </div>
          </div>
        {/if}

        <div class="task-links">
          <button type="button" class="task-link" data-testid="task-add-open" onclick={() => (addOpen = true)} disabled={addOpen}>
            - Add new task -
          </button>
          {#if call.tasks.length > 0}
            <button type="button" class="task-link done-link" onclick={handleNoMore}>
              - No more Tasks/Updates -
            </button>
          {/if}
        </div>
      {:else if call.tasks.length === 0}
        <p class="empty">No tasks yet.</p>
      {/if}
    </section>
  {/if}

</div>

<style>
  .program-tag {
    padding: 2px var(--sp-3);
    background: var(--surface-3);
    color: var(--rt-text-muted);
    border: 1px solid var(--hairline);
    border-radius: 999px;
    font-size: var(--font-size-sm);
    font-weight: 500;
    margin-right: var(--sp-2);
  }

  .call-info {
    margin-bottom: var(--sp-4);
  }

  .notes-body {
    margin: 0;
    color: var(--rt-text);
    white-space: pre-wrap;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--sp-3);
    margin-bottom: var(--sp-4);
  }

  .section-header h2 {
    margin: 0;
  }

  .task-list {
    display: flex;
    flex-direction: column;
  }

  /* New-task affordance: visual shell matches TaskEditorRow.expanded. The
     header strip mirrors TaskEditorRow's summary-row layout so the Add +
     trash buttons line up where the Update + trash live for existing rows. */
  .task-row-add {
    border: 1px solid var(--rt-success-text);
    border-radius: var(--radius);
    background: var(--rt-success-bg);
    margin-top: var(--sp-4);
    margin-bottom: var(--sp-3);
    overflow: hidden;
  }

  .summary-row {
    display: flex;
    align-items: stretch;
    padding: var(--sp-3) var(--sp-4);
  }

  .new-task-label {
    flex: 1;
    min-width: 0;
    align-self: center;
    font-weight: 600;
    color: var(--rt-text-muted);
    font-style: italic;
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
    padding: 0 var(--sp-3);
    font-size: 1.2em;
    line-height: 1;
    cursor: pointer;
    flex-shrink: 0;
    color: var(--rt-text-muted);
    align-self: center;
    border-radius: var(--radius-sm);
  }

  .trash-btn:hover {
    background: var(--rt-error-bg);
  }

  .form-wrapper {
    padding: var(--sp-4);
  }

  /* "- Add new task -" / "- No more Tasks/Updates -" link pair. */
  .task-links {
    display: flex;
    flex-wrap: wrap;
    gap: var(--sp-5);
    margin-top: var(--sp-4);
  }

  .task-link {
    background: none;
    border: none;
    color: var(--rt-success-text);
    font: inherit;
    font-style: italic;
    font-weight: 600;
    text-decoration: underline;
    cursor: pointer;
    padding: var(--sp-3) var(--sp-4);
    text-align: left;
  }

  .task-link:disabled {
    color: var(--rt-text-muted);
    cursor: default;
  }

  .task-link:not(:disabled):hover {
    color: var(--color-primary);
  }

  /* Status badges. callStatusBadgeClass maps call lifecycle states to
     these palette buckets: open→draft, waiting→open, assigned→full,
     archived→cancelled. */
  .badge-draft {
    background: var(--rt-gray-100);
    color: var(--rt-text-muted);
  }

  .badge-open {
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
  }

  .badge-full {
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
  }

  .badge-cancelled {
    background: var(--rt-error-bg);
    color: var(--rt-error);
  }

  @media (max-width: 768px) {
    .section-header {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
