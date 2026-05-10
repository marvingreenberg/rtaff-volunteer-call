<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { volunteerCalls, type VolunteerCallListResponse, type VolunteerCallCreate, type Program, type TaskCreate } from '$lib/api/client';
  import { ALL_PROGRAMS, PROGRAM_LABELS, SINGLE_TASK_PROGRAMS, suggestCallTitle } from '$lib/api/types';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import TaskEntryForm from '$lib/components/TaskEntryForm.svelte';
  import { callStatusBadgeClass, programLabel } from '$lib/utils/badges';
  import { formatDate } from '$lib/utils/format';

  let calls: VolunteerCallListResponse[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let showAddForm = $state(false);
  let saving = $state(false);
  let statusFilter = $state('');

  let newCall: VolunteerCallCreate = $state({ title: '', program: 'RTX' });
  let newCallTask: TaskCreate | null = $state(null);
  // Track whether the user has hand-edited the title; once they have, we
  // stop overwriting it from the program/date suggestion. Without this, a
  // user typing a custom name would lose it when picking a date.
  let titleManuallyEdited = $state(false);

  let isSingleTaskProgram = $derived(SINGLE_TASK_PROGRAMS.has(newCall.program));

  // Auto-suggest a default title when the user hasn't typed one yet. RTX
  // needs a task date; single-task programs use a fixed phrase.
  $effect(() => {
    if (titleManuallyEdited) return;
    const suggested = suggestCallTitle(newCall.program, newCallTask?.date ?? null);
    if (suggested && newCall.title !== suggested) {
      newCall = { ...newCall, title: suggested };
    }
  });

  function handleTitleInput(e: Event) {
    const v = (e.currentTarget as HTMLInputElement).value;
    titleManuallyEdited = true;
    newCall = { ...newCall, title: v };
  }

  onMount(loadCalls);

  async function loadCalls() {
    loading = true;
    error = null;
    try {
      const params: Record<string, string> = {};
      if (statusFilter) params.status = statusFilter;
      calls = await volunteerCalls.list(params);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load volunteer calls';
    } finally {
      loading = false;
    }
  }

  async function handleAdd() {
    saving = true;
    error = null;
    try {
      const payload: VolunteerCallCreate = {
        ...newCall,
        // For single-task programs, send the captured initial_task with the
        // create call so the user doesn't bounce to the detail page to add
        // it. RTX leaves initial_task null and adds tasks on the detail page.
        initial_task: isSingleTaskProgram ? newCallTask : null,
      };
      const created = await volunteerCalls.create(payload);
      newCall = { title: '', program: 'RTX' };
      newCallTask = null;
      titleManuallyEdited = false;
      showAddForm = false;
      // Single-task programs jump straight to the detail page so the user
      // can review the auto-created task; RTX keeps the list view.
      if (isSingleTaskProgram) {
        goto(`/volunteer-calls/${created.id}`);
        return;
      }
      await loadCalls();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create call';
    } finally {
      saving = false;
    }
  }

  function handleProgramChange(program: Program) {
    newCall = { ...newCall, program };
    if (!SINGLE_TASK_PROGRAMS.has(program)) newCallTask = null;
  }

  function handleFilterChange() {
    loadCalls();
  }
</script>

<svelte:head>
  <title>Volunteer Calls - RT-AFF</title>
</svelte:head>

<div class="calls-page page-md">
  <Breadcrumb crumbs={[{label: 'Volunteer Calls'}]} />
  <div class="page-header">
    <h1>Volunteer Calls</h1>
    <button class="btn btn-primary" onclick={() => showAddForm = !showAddForm}>
      {showAddForm ? 'Cancel' : 'New Call'}
    </button>
  </div>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if showAddForm}
    <div class="card add-form">
      <h2>New Volunteer Call</h2>
      <form onsubmit={(e) => { e.preventDefault(); handleAdd(); }}>
        <div class="form-row program-row">
          <span class="form-label">Program</span>
          <div class="program-options">
            {#each ALL_PROGRAMS as p (p)}
              <label class="radio-label">
                <input
                  type="radio"
                  name="program"
                  value={p}
                  checked={newCall.program === p}
                  onchange={() => handleProgramChange(p)}
                />
                {PROGRAM_LABELS[p]}
              </label>
            {/each}
          </div>
        </div>
        <div class="form-row">
          <label class="form-field">
            Title *
            <input
              type="text"
              value={newCall.title}
              oninput={handleTitleInput}
              required
              placeholder="e.g., Spring NRD 2026"
            />
          </label>
        </div>
        <div class="form-row">
          <label class="form-field">
            Notes
            <textarea bind:value={newCall.notes} placeholder="Optional notes about this call"></textarea>
          </label>
        </div>

        {#if isSingleTaskProgram}
          <div class="single-task-block">
            <h3>Task details</h3>
            <p class="hint">
              {programLabel(newCall.program)} calls have a single task — fill it in here.
            </p>
            <TaskEntryForm
              submitLabel=""
              onsubmit={() => undefined}
              onchange={(value) => (newCallTask = value)}
            />
          </div>
        {/if}

        <button type="submit" class="btn btn-primary" disabled={saving}>
          {saving ? 'Creating...' : 'Create Call'}
        </button>
      </form>
    </div>
  {/if}

  <div class="filters">
    <select bind:value={statusFilter} onchange={handleFilterChange}>
      <option value="">All Statuses</option>
      <option value="draft">Draft</option>
      <option value="open">Open</option>
      <option value="closed">Closed</option>
    </select>
  </div>

  {#if loading}
    <p class="loading">Loading calls...</p>
  {:else if calls.length === 0}
    <p class="empty">No volunteer calls found.</p>
  {:else}
    <table class="data-table">
      <thead>
        <tr>
          <th>Title</th>
          <th>Program</th>
          <th>Tasks</th>
          <th>Status</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {#each calls as call (call.id)}
          <tr>
            <td>
              <a href="/volunteer-calls/{call.id}" class="row-link">{call.title}</a>
            </td>
            <td>{programLabel(call.program)}</td>
            <td>{call.task_count}</td>
            <td>
              <span class="badge {callStatusBadgeClass(call.status)}">{call.status}</span>
            </td>
            <td>{formatDate(call.created_at)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>

<style>
  .add-form {
    margin-bottom: var(--spacing-lg);
  }

  .add-form h2 {
    margin-top: 0;
  }

  .form-row {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .program-row {
    align-items: center;
  }

  .form-label {
    font-weight: 500;
    color: var(--rt-gray-600);
    margin-right: var(--spacing-sm);
  }

  .program-options {
    display: flex;
    gap: var(--spacing-md);
    flex-wrap: wrap;
  }

  .radio-label {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    cursor: pointer;
  }

  .single-task-block {
    margin: var(--spacing-md) 0;
    padding: var(--spacing-md);
    background: var(--rt-bg-subtle, #f9f7f2);
    border: 1px solid var(--rt-gray-200);
    border-radius: var(--card-radius);
  }

  .single-task-block h3 {
    margin: 0 0 var(--spacing-xs) 0;
    font-size: var(--btn-font-size);
  }

  .hint {
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
    margin: 0 0 var(--spacing-sm) 0;
  }

  .filters {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .filters select {
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: var(--btn-min-height);
    border: 1px solid var(--rt-gray-200);
    border-radius: var(--card-radius);
    font-size: var(--btn-font-size);
    font-family: inherit;
  }

  .row-link {
    font-weight: 600;
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

  @media (max-width: 768px) {
    .form-row {
      flex-direction: column;
    }
  }
</style>
