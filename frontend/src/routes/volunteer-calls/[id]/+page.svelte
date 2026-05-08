<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import {
    volunteerCalls,
    type VolunteerCallResponse,
    type TaskCreate,
    type SendInvitesResponse,
    type AssignmentNoticesResponse,
  } from '$lib/api/client';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import TaskEntryForm from '$lib/components/TaskEntryForm.svelte';
  import TaskRow from '$lib/components/TaskRow.svelte';
  import { callStatusBadgeClass } from '$lib/utils/badges';

  let call = $state<VolunteerCallResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);
  let sendingInvites = $state(false);
  let sendInvitesResult: SendInvitesResponse | null = $state(null);
  let sendingNotices = $state(false);
  let assignmentNoticesResult: AssignmentNoticesResponse | null = $state(null);

  // At most one task row is open. Editing a row's fields populates
  // pendingEdit; the row collapsing (or any call-state action) flushes it
  // through handleSaveTask.
  let expandedTaskId: string | null = $state(null);
  let pendingEdit: { taskId: string; value: TaskCreate | null; dirty: boolean } | null = null;

  let callId = $derived(page.params.id!);

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

  // Persist the current pending edit, if any, then collapse the open row.
  // Invalid (null value) or untouched edits are dropped.
  async function flushAndCollapse() {
    const edit = pendingEdit;
    pendingEdit = null;
    if (edit && edit.dirty && edit.value) {
      try {
        await volunteerCalls.updateTask(callId, edit.taskId, edit.value);
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to save task';
      }
    }
    expandedTaskId = null;
  }

  function handleRowChange(taskId: string, value: TaskCreate | null, dirty: boolean) {
    pendingEdit = { taskId, value, dirty };
  }

  async function handleToggleRow(taskId: string) {
    if (expandedTaskId === taskId) {
      await flushAndCollapse();
    } else {
      await flushAndCollapse();
      expandedTaskId = taskId;
    }
    await loadCall();
  }

  async function handleAddTask(data: TaskCreate) {
    error = null;
    try {
      await volunteerCalls.addTask(callId, data);
      await loadCall();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to add task';
      throw e;
    }
  }

  async function handleDeleteTask(taskId: string) {
    error = null;
    try {
      // Drop any pending autosave for the row about to vanish.
      if (pendingEdit?.taskId === taskId) pendingEdit = null;
      if (expandedTaskId === taskId) expandedTaskId = null;
      await volunteerCalls.deleteTask(callId, taskId);
      await loadCall();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete task';
    }
  }

  async function handleSendInvites(confirmReSend = false) {
    if (call?.status === 'open' && !confirmReSend) {
      const ok = window.confirm(
        'Re-send invitations to all subscribed volunteers? They will get the email again.',
      );
      if (!ok) return;
    }
    sendingInvites = true;
    sendInvitesResult = null;
    assignmentNoticesResult = null;
    error = null;
    await flushAndCollapse();
    try {
      sendInvitesResult = await volunteerCalls.sendInvites(callId);
      // Send-invites flips Draft→Open server-side; reload so the badge and
      // button cluster reflect the new status without a manual refresh.
      await loadCall();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to send invites';
    } finally {
      sendingInvites = false;
    }
  }

  async function handleAssignVolunteers() {
    if (!call) return;
    error = null;
    await flushAndCollapse();
    try {
      if (call.status === 'open') {
        call = await volunteerCalls.update(callId, { status: 'closed' });
      }
      await goto(`/volunteer-calls/${callId}/assign`);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to start assigning';
    }
  }

  async function handleSendAssignmentNotices() {
    const ok = window.confirm(
      'Send assignment + thank-you emails to volunteers who responded?',
    );
    if (!ok) return;
    sendingNotices = true;
    assignmentNoticesResult = null;
    sendInvitesResult = null;
    error = null;
    try {
      assignmentNoticesResult =
        await volunteerCalls.sendAssignmentNotices(callId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to send notices';
    } finally {
      sendingNotices = false;
    }
  }

  async function handleReopen() {
    if (!call) return;
    error = null;
    try {
      call = await volunteerCalls.update(callId, { status: 'open' });
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to reopen call';
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

    <div class="status-actions">
      {#if call.status === 'draft'}
        <button
          class="btn btn-primary"
          onclick={() => handleSendInvites(true)}
          disabled={sendingInvites || call.tasks.length === 0}
          title={call.tasks.length === 0 ? 'Add at least one task before sending invites' : ''}
        >
          {sendingInvites ? 'Sending...' : 'Send Volunteer Invites'}
        </button>
      {/if}
      {#if call.status === 'open'}
        <button class="btn btn-primary" onclick={handleAssignVolunteers}>
          Assign Volunteers
        </button>
        <button class="btn btn-secondary" onclick={() => handleSendInvites(false)} disabled={sendingInvites}>
          {sendingInvites ? 'Sending...' : 'Re-send Invites'}
        </button>
      {/if}
      {#if call.status === 'closed'}
        <button class="btn btn-primary" onclick={handleAssignVolunteers}>
          Assign Volunteers
        </button>
        <button
          class="btn btn-secondary"
          onclick={handleSendAssignmentNotices}
          disabled={sendingNotices}
        >
          {sendingNotices ? 'Sending...' : 'Send Assignment Notices'}
        </button>
        <button class="btn btn-secondary" onclick={handleReopen}>
          Reopen
        </button>
      {/if}
    </div>

    {#if sendInvitesResult}
      <div class="result-banner">
        {sendInvitesResult.volunteers_notified} volunteer{sendInvitesResult.volunteers_notified === 1 ? '' : 's'} notified{#if sendInvitesResult.volunteers_skipped > 0}, {sendInvitesResult.volunteers_skipped} skipped (unsubscribed/paused){/if}.
      </div>
    {/if}

    {#if assignmentNoticesResult}
      <div class="result-banner">
        {assignmentNoticesResult.assignment_emails} assignment email{assignmentNoticesResult.assignment_emails === 1 ? '' : 's'} sent
        &middot;
        {assignmentNoticesResult.thanks_emails} thank-you email{assignmentNoticesResult.thanks_emails === 1 ? '' : 's'} sent.
      </div>
    {/if}

    <div class="section">
      <div class="section-header">
        <h2>Tasks ({call.task_count})</h2>
      </div>

      {#if call.tasks.length > 0}
        <div class="task-list">
          {#each call.tasks as task (task.id)}
            <TaskRow
              {task}
              expanded={expandedTaskId === task.id}
              ontoggle={() => handleToggleRow(task.id)}
              onchange={handleRowChange}
              ondelete={handleDeleteTask}
            />
          {/each}
        </div>
      {/if}

      {#if call.status !== 'closed'}
        <div class="card add-form">
          <TaskEntryForm submitLabel="Add" onsubmit={handleAddTask} />
        </div>
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

  .status-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .result-banner {
    padding: var(--spacing-md) var(--spacing-md);
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
    border-radius: var(--card-radius);
    margin-bottom: var(--spacing-lg);
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

  .add-form {
    margin-top: var(--spacing-md);
  }

  .task-list {
    display: flex;
    flex-direction: column;
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
