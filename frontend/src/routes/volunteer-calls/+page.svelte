<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { volunteerCalls, people, type VolunteerCallListResponse, type VolunteerCallCreate, type Program, type TaskCreate } from '$lib/api/client';
  import { ALL_PROGRAMS, PROGRAM_LABELS, SINGLE_TASK_PROGRAMS, suggestCallTitle } from '$lib/api/types';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import Select from '$lib/components/Select.svelte';
  import TaskEntryForm from '$lib/components/TaskEntryForm.svelte';
  import { callStatusBadgeClass, programLabel } from '$lib/utils/badges';
  import { rowAction, type RowAction } from '$lib/utils/call-row-action';
  import { rowNotes } from '$lib/utils/call-row-notes';

  type TeamLead = { id: string; first_name: string; last_name: string };

  let calls: VolunteerCallListResponse[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let showAddForm = $state(false);
  let saving = $state(false);
  // 'active' = open ∪ waiting ∪ assigned; 'archived' = archived only.
  let statusFilter = $state<'active' | 'archived'>('active');

  let newCall: VolunteerCallCreate = $state({ title: '', program: 'RTX' });
  let newCallTask: TaskCreate | null = $state(null);
  // Track whether the user has hand-edited the title; once they have, we
  // stop overwriting it from the program/date suggestion. Without this, a
  // user typing a custom name would lose it when picking a date.
  let titleManuallyEdited = $state(false);

  // Team-lead candidates for the currently-selected program. Refetched on
  // program change so the embedded TaskEntryForm only sees people who can
  // actually lead a task for *this* program (not all team leaders in the
  // org). Empty until the first fetch resolves.
  let teamLeads = $state<TeamLead[]>([]);
  let teamLeadsForProgram = $state<Program | null>(null);

  let isSingleTaskProgram = $derived(SINGLE_TASK_PROGRAMS.has(newCall.program));

  // Single-task programs preload the task entry; teamLeads must be loaded
  // before the form mounts so the select has the right options. RTX
  // doesn't need them here (tasks are added on the detail page where the
  // per-page fetch already happens), but loading anyway keeps the code
  // path uniform.
  $effect(() => {
    if (teamLeadsForProgram === newCall.program) return;
    const program = newCall.program;
    teamLeadsForProgram = program;
    void (async () => {
      try {
        const list = await people.list({
          role: 'team_leader',
          active: true,
          program,
        });
        if (teamLeadsForProgram !== program) return; // raced past us
        teamLeads = list.items.map((p) => ({
          id: p.id,
          first_name: p.first_name,
          last_name: p.last_name,
        }));
      } catch {
        // Non-fatal — the team-lead select just stays empty.
        teamLeads = [];
      }
    })();
  });

  // Auto-suggest a default title when the user hasn't typed one yet. RTX
  // anchors to the next two-week cycle from today; single-task programs
  // use a fixed phrase.
  $effect(() => {
    if (titleManuallyEdited) return;
    const suggested = suggestCallTitle(newCall.program);
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
      const status =
        statusFilter === 'archived'
          ? ['archived']
          : ['open', 'waiting', 'assigned'];
      calls = await volunteerCalls.list({ status });
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

  // Row-level action state.
  let busyCallIds = $state<Set<string>>(new Set());
  let rowMessage = $state('');

  function setBusy(id: string, busy: boolean) {
    const next = new Set(busyCallIds);
    if (busy) next.add(id);
    else next.delete(id);
    busyCallIds = next;
  }

  async function handleRowAction(
    call: VolunteerCallListResponse,
    action: RowAction,
  ) {
    if (busyCallIds.has(call.id)) return;
    setBusy(call.id, true);
    error = null;
    rowMessage = '';
    try {
      if (action === 'send_invites') {
        const res = await volunteerCalls.sendInvites(call.id);
        rowMessage =
          `Called: ${res.volunteers_notified} notification` +
          (res.volunteers_notified === 1 ? '' : 's') +
          ` sent.`;
      } else if (action === 'assign' || action === 'update_assignments') {
        // Same destination either way — admin re-uses the existing /assign
        // page; in ASSIGNED state it'll just have a 'Done' return button.
        await goto(`/volunteer-calls/${call.id}/assign`);
        return; // navigation; nothing else to do.
      } else if (
        action === 'send_assignments' ||
        action === 'send_changed_assignments'
      ) {
        // Backend decides what to send based on call.last_sent_roster:
        // first send → everyone; subsequent → per-task diff.
        const res = await volunteerCalls.sendAssignmentNotices(call.id);
        const parts: string[] = [];
        if (res.assignment_emails)
          parts.push(`${res.assignment_emails} assignment`);
        if (res.team_lead_emails)
          parts.push(`${res.team_lead_emails} team-lead`);
        if (res.thanks_emails) parts.push(`${res.thanks_emails} thank-you`);
        if (res.removal_emails) parts.push(`${res.removal_emails} removal`);
        const total =
          res.assignment_emails +
          res.team_lead_emails +
          res.thanks_emails +
          res.removal_emails;
        rowMessage =
          parts.length === 0
            ? 'No emails sent (nothing to send).'
            : `${parts.join(' / ')} email${total === 1 ? '' : 's'} sent.`;
      } else if (action === 'archive') {
        await volunteerCalls.archive(call.id);
        rowMessage = `Call "${call.title}" archived.`;
      }
      await loadCalls();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Action failed';
    } finally {
      setBusy(call.id, false);
    }
  }

  async function handleDeleteCall(call: VolunteerCallListResponse) {
    if (busyCallIds.has(call.id)) return;
    const ok = window.confirm(
      `Delete call "${call.title}" and all its tasks? This cannot be undone.`,
    );
    if (!ok) return;
    // Second confirm if the call is past Open — the user already has
    // sent invites or assignments out to volunteers.
    if (call.status !== 'open') {
      const ok2 = window.confirm(
        'Volunteers have already been notified about this call. Are you sure you want to delete it?',
      );
      if (!ok2) return;
    }
    setBusy(call.id, true);
    error = null;
    rowMessage = '';
    try {
      await volunteerCalls.delete(call.id);
      await loadCalls();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete call';
    } finally {
      setBusy(call.id, false);
    }
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
              {teamLeads}
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
    <Select
      bind:value={statusFilter}
      options={[
        { value: 'active', label: 'Active (open · waiting · assigned)' },
        { value: 'archived', label: 'Archived' },
      ]}
      ariaLabel="Call status filter"
      onchange={handleFilterChange}
    />
  </div>

  {#if rowMessage}
    <div class="result-banner">{rowMessage}</div>
  {/if}

  {#if loading}
    <p class="loading">Loading calls...</p>
  {:else if calls.length === 0}
    <p class="empty">No volunteer calls found.</p>
  {:else}
    <table class="data-table calls-table">
      <thead>
        <tr>
          <th class="title-col">Title</th>
          <th>Tasks</th>
          <th>Status</th>
          <th>Action</th>
          <th>Notes</th>
          <th aria-label="Delete"></th>
        </tr>
      </thead>
      <tbody>
        {#each calls as call (call.id)}
          {@const actions = rowAction(call)}
          {@const busy = busyCallIds.has(call.id)}
          {@const notes = rowNotes(call)}
          <tr data-testid="call-row" data-call-id={call.id}>
            <td class="title-col">
              <a href="/volunteer-calls/{call.id}" class="row-link">{call.title}</a>
            </td>
            <td>{call.task_count}</td>
            <td>
              <span class="badge {callStatusBadgeClass(call.status)}">{call.status}</span>
            </td>
            <td class="action-cell">
              {#each actions as action (action.action)}
                <button
                  type="button"
                  class="btn btn-primary action-btn"
                  data-testid="row-action-{action.action}"
                  disabled={busy}
                  onclick={() => handleRowAction(call, action.action)}
                >
                  {busy ? '...' : action.label}
                </button>
              {/each}
            </td>
            <td class="notes-cell">{notes}</td>
            <td class="trash-cell">
              <button
                type="button"
                class="trash-btn"
                onclick={() => handleDeleteCall(call)}
                aria-label="Delete call {call.title}"
                title="Delete call"
              >
                🗑️
              </button>
            </td>
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
    /* Same green palette as an expanded TaskRow + the
       /volunteer-calls/[id] new-task panel (--rt-success-bg /
       --rt-success-text), so single-task program create forms read
       visually as "this is the task you're editing", not a sub-section. */
    margin: var(--spacing-md) 0;
    padding: var(--spacing-md);
    background: var(--rt-success-bg, #e6f4ea);
    border: 1px solid var(--rt-success-text, #2f7a45);
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


  .row-link {
    font-weight: 600;
  }

  .action-cell {
    white-space: nowrap;
    /* Two stacked buttons on Update + Send rows; arrange them side-by-side
       within a single cell. flex-wrap keeps them readable on narrow widths. */
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
    align-items: stretch;
  }

  .action-btn {
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: var(--font-size-sm);
    min-height: 32px;
    /* Button labels carry literal newlines ("Send\nCall") so the words
       stack vertically — narrow columns, taller cells. Centred so the
       two lines read cleanly. */
    white-space: pre-line;
    text-align: center;
    line-height: 1.15;
  }

  .notes-cell {
    color: var(--rt-text-muted, #777);
    font-size: var(--font-size-sm);
    /* Wrap when the available width forces it (the "filled · fully
       assigned" string can be long on narrow viewports). */
    white-space: normal;
    word-break: break-word;
  }

  /* Title gets roughly a third of the available width — call titles
     are the row's anchor and should have visible room. */
  .calls-table .title-col {
    width: 33%;
  }

  .trash-cell {
    width: 44px;
    text-align: right;
  }

  .trash-btn {
    background: none;
    border: none;
    padding: 0 var(--spacing-sm);
    font-size: 1.2em;
    line-height: 1;
    cursor: pointer;
    color: var(--rt-text-muted, #888);
  }

  .trash-btn:hover {
    background: var(--rt-danger-bg, #fdecea);
  }

  .result-banner {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
    border-radius: var(--card-radius);
    margin-bottom: var(--spacing-md);
  }

  /* Status badges. Re-uses the success/error pair already defined for
     draft/open/closed callStatusBadgeClass mapping (now mapped to
     open/waiting/assigned/archived). */
  .badge-draft {
    background: var(--rt-gray-100, #f5f3ef);
    color: var(--rt-text-muted, #777);
  }

  .badge-open {
    background: var(--rt-info-bg, #e7f1fb);
    color: var(--rt-info-text, #2c5aa0);
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
    .form-row {
      flex-direction: column;
    }
  }
</style>
