<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import {
    volunteerCalls,
    teamAssignments,
    type AssignmentOverviewResponse,
    type TaskOverviewItem,
    type AvailableVolunteer,
    type TaskAssignment,
  } from "$lib/api/client";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import TeamLeadAutocomplete from "$lib/components/TeamLeadAutocomplete.svelte";
  import { skillBadgeClass } from "$lib/utils/badges";
  import { formatDate, volunteersLabel } from "$lib/utils/format";

  let overview = $state<AssignmentOverviewResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);
  let busyTaskIds = $state<Set<string>>(new Set());

  let callId = $derived(page.params.id!);

  let totals = $derived.by(() => {
    if (!overview) return { needed: 0, assigned: 0, full: 0 };
    let needed = 0;
    let assigned = 0;
    let full = 0;
    for (const t of overview.tasks) {
      needed += t.volunteers_needed;
      assigned += t.assignments.length;
      if (t.assignments.length >= t.volunteers_needed) full += 1;
    }
    return { needed, assigned, full };
  });

  onMount(load);

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
    <p class="subtitle">
      {totals.assigned}/{totals.needed} spots filled
      &middot;
      {totals.full}/{overview.tasks.length} task{overview.tasks.length === 1
        ? ""
        : "s"} full
      &middot;
      {overview.volunteers.length} volunteer{overview.volunteers.length === 1
        ? ""
        : "s"} responded
    </p>

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
                  <TeamLeadAutocomplete
                    initialId={task.team_lead_id}
                    initialLabel={task.team_lead_name}
                    placeholder="Type 3+ chars to find a team lead"
                    onselect={(id) => setTeamLead(task.task_id, id)}
                  />
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
  .subtitle {
    color: var(--rt-text-light, #555);
    margin-bottom: var(--spacing-lg);
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
