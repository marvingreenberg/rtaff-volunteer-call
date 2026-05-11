<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import {
    volunteerCalls,
    people,
    teamAssignments,
    type AssignmentOverviewResponse,
    type TaskOverviewItem,
    type AvailableVolunteer,
    type TaskAssignment,
  } from "$lib/api/client";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import { skillBadgeClass } from "$lib/utils/badges";
  import { formatDate, volunteersLabel } from "$lib/utils/format";
  import {
    ASSIGNMENT_POLICY_LABELS,
    type AssignmentPolicy,
  } from "$lib/api/types";
  import {
    computeCounts,
    countsMessage as computeCountsMessage,
    gateMessage as computeGateMessage,
    canSave as computeCanSave,
  } from "$lib/utils/assignment-policy";

  type TeamLead = { id: string; first_name: string; last_name: string };

  let overview = $state<AssignmentOverviewResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);
  let busyTaskIds = $state<Set<string>>(new Set());
  let teamLeads = $state<TeamLead[]>([]);

  // Policy is in-page state only (per spec). Default: Exact required.
  let policy = $state<AssignmentPolicy>("exact");
  let saving = $state(false);

  let callId = $derived(page.params.id!);

  let totals = $derived.by(() => {
    if (!overview) return { needed: 0, assigned: 0, full: 0, tasks: 0 };
    let needed = 0;
    let assigned = 0;
    let full = 0;
    for (const t of overview.tasks) {
      needed += t.volunteers_needed;
      assigned += t.assignments.length;
      if (t.assignments.length >= t.volunteers_needed) full += 1;
    }
    return { needed, assigned, full, tasks: overview.tasks.length };
  });

  // Counts and gate text are derived from the overview + selected policy.
  // The actual logic lives in $lib/utils/assignment-policy so it can be
  // unit-tested without the SvelteKit route runtime; this component just
  // wires the reactive values through.
  let counts = $derived(overview ? computeCounts(overview.tasks) : { under: 0, over: 0, noLead: 0 });
  let countsMessage = $derived(computeCountsMessage(counts));
  let gateMessage = $derived(computeGateMessage(counts, policy));
  let canSave = $derived(
    !!overview && computeCanSave(overview.tasks, counts, policy),
  );

  onMount(async () => {
    await load();
    try {
      const leads = await people.list({ role: "team_leader", active: true });
      teamLeads = leads.map((p) => ({
        id: p.id,
        first_name: p.first_name,
        last_name: p.last_name,
      }));
    } catch {
      // Non-fatal — the team-lead select will simply be empty.
    }
  });

  async function load() {
    loading = true;
    try {
      overview = await volunteerCalls.assignmentOverview(callId);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load assignments";
    } finally {
      loading = false;
    }
  }

  function setBusy(taskId: string, busy: boolean) {
    const next = new Set(busyTaskIds);
    if (busy) next.add(taskId);
    else next.delete(taskId);
    busyTaskIds = next;
  }

  async function refreshTask(taskId: string) {
    // Refetch the overview and replace the single task slice.
    const fresh = await volunteerCalls.assignmentOverview(callId);
    if (!overview) {
      overview = fresh;
      return;
    }
    const next = fresh.tasks.find((t) => t.task_id === taskId);
    if (!next) return;
    overview = {
      ...overview,
      tasks: overview.tasks.map((t) => (t.task_id === taskId ? next : t)),
    };
  }

  async function assign(taskId: string, candidate: AvailableVolunteer) {
    if (busyTaskIds.has(taskId)) return;
    setBusy(taskId, true);
    error = null;
    try {
      await teamAssignments.create(callId, taskId, {
        person_id: candidate.person_id,
      });
      await refreshTask(taskId);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to assign volunteer";
    } finally {
      setBusy(taskId, false);
    }
  }

  async function unassign(taskId: string, assignment: TaskAssignment) {
    if (busyTaskIds.has(taskId)) return;
    setBusy(taskId, true);
    error = null;
    try {
      await teamAssignments.delete(callId, taskId, assignment.assignment_id);
      await refreshTask(taskId);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to unassign volunteer";
    } finally {
      setBusy(taskId, false);
    }
  }

  async function setTeamLead(taskId: string, leadId: string | null) {
    if (busyTaskIds.has(taskId)) return;
    setBusy(taskId, true);
    error = null;
    try {
      await volunteerCalls.updateTask(callId, taskId, { team_lead_id: leadId });
      await refreshTask(taskId);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to update team lead";
    } finally {
      setBusy(taskId, false);
    }
  }

  function isFull(t: TaskOverviewItem): boolean {
    return t.assignments.length >= t.volunteers_needed;
  }

  async function handleSave() {
    if (!canSave || saving) return;
    saving = true;
    error = null;
    try {
      // Transition WAITING → ASSIGNED. The actual Send Assignments step
      // (which emails volunteers) is a separate row button on the list
      // page; admins explicitly fire it from there once ready.
      await volunteerCalls.doneAssigning(callId);
      await goto("/volunteer-calls");
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to complete assignment";
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>{overview ? `Assign — ${overview.call_title}` : "Assign"} - RT-AFF</title>
</svelte:head>

<div class="assign-page page-md">
  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if loading}
    <p class="loading">Loading…</p>
  {:else if overview}
    <Breadcrumb
      crumbs={[
        { label: "Volunteer Calls", href: "/volunteer-calls" },
        { label: overview.call_title, href: `/volunteer-calls/${callId}` },
        { label: "Assign" },
      ]}
    />
    <h1>Assign — {overview.call_title}</h1>

    <div class="top-bar">
      <div class="counts-col">
        <div class="counts-line">
          {totals.assigned}/{totals.needed} spots filled
        </div>
        <div class="counts-line">
          {totals.full}/{totals.tasks} task{totals.tasks === 1 ? "" : "s"} complete
        </div>
      </div>

      <div class="messages-col">
        <div class="message-area" data-area="counts">{countsMessage}</div>
        <div class="message-area" data-area="gate" class:hidden={!gateMessage}>
          {gateMessage}
        </div>
      </div>

      <div class="actions-col">
        <label class="policy-label">
          <span class="policy-prefix">Completion when:</span>
          <select bind:value={policy} aria-label="Completion policy">
            <option value="exact">{ASSIGNMENT_POLICY_LABELS.exact}</option>
            <option value="over">{ASSIGNMENT_POLICY_LABELS.over}</option>
            <option value="over_under">
              {ASSIGNMENT_POLICY_LABELS.over_under}
            </option>
          </select>
        </label>
        <button
          type="button"
          class="btn btn-primary save-btn"
          disabled={!canSave || saving}
          onclick={handleSave}
          aria-label="Complete assignment"
        >
          {saving ? "Saving..." : "Done Assigning"}
        </button>
      </div>
    </div>

    {#if overview.tasks.length === 0}
      <p class="empty">This call has no tasks.</p>
    {:else}
      <div class="task-cards">
        {#each overview.tasks as task (task.task_id)}
          {@const full = isFull(task)}
          <section class="task-card" class:full>
            <header class="card-header">
              <span class="date">{task.date ? formatDate(task.date) : "—"}</span>
              <span class="counts">
                {volunteersLabel(task.volunteers_needed, task.skilled_needed)}
              </span>
              <span class="city">{task.city ?? ""}</span>
              <span class="description">{task.short_description}</span>
              <span class="progress" class:full>
                {task.assignments.length}/{task.volunteers_needed}
                {#if full}<span class="full-tag">Full</span>{/if}
              </span>
            </header>

            <div class="task-meta">
              <div class="meta-row">
                <span class="meta-label">Team lead</span>
                <div class="meta-value">
                  <select
                    value={task.team_lead_id ?? ""}
                    aria-label="Team lead"
                    disabled={busyTaskIds.has(task.task_id)}
                    onchange={(e) => {
                      const v = (e.currentTarget as HTMLSelectElement).value;
                      setTeamLead(task.task_id, v || null);
                    }}
                  >
                    <option value="">— None —</option>
                    {#each teamLeads as lead (lead.id)}
                      <option value={lead.id}>
                        {lead.first_name} {lead.last_name}
                      </option>
                    {/each}
                  </select>
                </div>
              </div>
              {#if task.notes}
                <div class="meta-row">
                  <span class="meta-label">Notes</span>
                  <span class="meta-value notes">{task.notes}</span>
                </div>
              {/if}
            </div>

            <div class="lists">
              <div class="list-block">
                <h3 class="list-heading">Assigned</h3>
                {#if task.assignments.length === 0}
                  <p class="list-empty">No one assigned yet.</p>
                {:else}
                  <ul class="people">
                    {#each task.assignments as a (a.assignment_id)}
                      <li class="person assigned">
                        <button
                          type="button"
                          class="person-row"
                          aria-label="Unassign {a.person_name}"
                          disabled={busyTaskIds.has(task.task_id)}
                          onclick={() => unassign(task.task_id, a)}
                        >
                          <span class="check" aria-hidden="true">✓</span>
                          <span class="name">{a.person_name}</span>
                          {#each a.skills as s (s)}
                            <span class="badge {skillBadgeClass(s)}">{s}</span>
                          {/each}
                          <span class="action">Remove</span>
                        </button>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </div>

              <div class="list-block">
                <h3 class="list-heading">Available</h3>
                {#if task.available_volunteers.length === 0}
                  <p class="list-empty">No more candidates.</p>
                {:else}
                  <ul class="people">
                    {#each task.available_volunteers as v (v.person_id)}
                      <li class="person available">
                        <button
                          type="button"
                          class="person-row"
                          aria-label="Assign {v.person_name}"
                          disabled={busyTaskIds.has(task.task_id)}
                          onclick={() => assign(task.task_id, v)}
                        >
                          <span class="check empty" aria-hidden="true">☐</span>
                          <span class="name">{v.person_name}</span>
                          {#each v.skills as s (s)}
                            <span class="badge {skillBadgeClass(s)}">{s}</span>
                          {/each}
                          <span class="action">Assign</span>
                        </button>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </div>
            </div>
          </section>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  /* Sticky two-row top bar that pins to the top of the viewport while the
     task cards below scroll. Visually a "separate scroll area" without
     fighting the existing page-md / layout-main flow. */
  .top-bar {
    position: sticky;
    top: 0;
    z-index: 5;
    display: grid;
    grid-template-columns: max-content 1fr max-content;
    grid-template-rows: auto auto;
    gap: var(--spacing-xs) var(--spacing-lg);
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-md);
    margin-bottom: var(--spacing-md);
    background: var(--rt-bg-subtle, #f9f7f2);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
  }

  .counts-col {
    grid-column: 1;
    grid-row: 1 / span 2;
    display: flex;
    flex-direction: column;
    justify-content: center;
    font-size: var(--font-size-sm);
    color: var(--rt-text-light, #555);
    font-variant-numeric: tabular-nums;
  }

  .counts-line {
    line-height: 1.4;
  }

  .messages-col {
    grid-column: 2;
    grid-row: 1 / span 2;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: var(--spacing-xs);
    min-width: 0;
  }

  .message-area {
    font-size: var(--font-size-sm);
    color: var(--rt-text-light, #555);
    line-height: 1.4;
  }

  .message-area[data-area="gate"] {
    color: var(--rt-warning-text, #b35900);
    font-weight: 500;
  }

  .message-area.hidden {
    visibility: hidden;
  }

  .actions-col {
    grid-column: 3;
    grid-row: 1 / span 2;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: var(--spacing-xs);
  }

  .policy-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: var(--font-size-sm);
  }

  .policy-prefix {
    color: var(--rt-text-muted, #777);
  }

  .policy-label select {
    padding: var(--spacing-xs) var(--spacing-sm);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
    font: inherit;
    background: var(--rt-white, #fff);
  }

  .save-btn {
    min-width: 6em;
  }

  @media (max-width: 720px) {
    .top-bar {
      grid-template-columns: 1fr;
      grid-template-rows: auto auto auto;
    }
    .counts-col,
    .messages-col,
    .actions-col {
      grid-column: 1;
      grid-row: auto;
      align-items: flex-start;
    }
  }

  .task-cards {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .task-meta {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--rt-gray-200, #e4dfda);
    margin-bottom: var(--spacing-sm);
  }

  .meta-row {
    display: grid;
    grid-template-columns: 7em minmax(0, 1fr);
    gap: var(--spacing-sm);
    align-items: center;
    font-size: var(--font-size-sm);
  }

  .meta-label {
    color: var(--rt-text-muted, #777);
    font-weight: 500;
  }

  .meta-value {
    min-width: 0;
  }

  .meta-value.notes {
    white-space: pre-wrap;
    color: var(--rt-text-light, #555);
  }

  .task-card {
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    background: var(--rt-white, #ffffff);
    overflow: hidden;
  }

  .task-card.full {
    border-color: var(--rt-success-text, #2f7a45);
    background: var(--rt-success-bg, #e6f4ea);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--rt-gray-200, #e4dfda);
    background: var(--rt-gray-50, #fafaf7);
  }

  .task-card.full .card-header {
    background: transparent;
    border-bottom-color: var(--rt-success-text, #2f7a45);
  }

  .date {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    flex-shrink: 0;
  }

  .counts {
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

  .progress {
    flex-shrink: 0;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--rt-text-muted, #777);
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .progress.full {
    color: var(--rt-success-text, #2f7a45);
  }

  .full-tag {
    font-size: var(--font-size-xs);
    background: var(--rt-success-text, #2f7a45);
    color: var(--rt-white, #fff);
    padding: 1px 6px;
    border-radius: 10px;
    font-weight: 500;
  }

  .lists {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
  }

  .list-heading {
    font-size: var(--font-size-sm);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rt-text-muted, #777);
    margin: 0 0 var(--spacing-xs) 0;
  }

  .list-empty {
    color: var(--rt-text-muted, #777);
    font-style: italic;
    margin: 0;
    font-size: var(--font-size-sm);
  }

  ul.people {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .person-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
    padding: var(--spacing-xs) var(--spacing-sm);
    background: none;
    border: 1px solid transparent;
    border-radius: var(--card-radius);
    cursor: pointer;
    font: inherit;
    color: inherit;
    text-align: left;
  }

  .person-row:hover:not(:disabled) {
    background: var(--rt-gray-100, #f5f3ef);
    border-color: var(--rt-gray-200, #e4dfda);
  }

  .person-row:disabled {
    opacity: 0.5;
    cursor: progress;
  }

  .person.assigned .check {
    color: var(--rt-success-text, #2f7a45);
    font-weight: 700;
  }

  .person.available .check.empty {
    color: var(--rt-text-muted, #777);
  }

  .check {
    flex-shrink: 0;
    width: 1.2em;
    text-align: center;
  }

  .name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .badge {
    flex-shrink: 0;
    font-size: var(--font-size-xs);
    padding: 1px 6px;
    border-radius: 10px;
  }

  .action {
    flex-shrink: 0;
    font-size: var(--font-size-xs);
    color: var(--rt-text-muted, #777);
  }

  .person-row:hover:not(:disabled) .action {
    color: var(--color-primary, #3a6db5);
  }

  @media (max-width: 768px) {
    .lists {
      grid-template-columns: 1fr;
    }
  }
</style>
