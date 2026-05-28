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
  import AssignmentSpreadsheet from "$lib/components/AssignmentSpreadsheet.svelte";
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
  import {
    buildFairnessContext,
    partitionAvailable,
    badgesFor,
  } from "$lib/utils/assignment-fairness";
  import { truncateVolunteerName } from "$lib/utils/volunteer-name";

  type TeamLead = { id: string; first_name: string; last_name: string };

  let overview = $state<AssignmentOverviewResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);
  let busyTaskIds = $state<Set<string>>(new Set());
  let teamLeads = $state<TeamLead[]>([]);

  // Policy is in-page state only (per spec). Default: Exact required.
  let policy = $state<AssignmentPolicy>("exact");
  let saving = $state(false);

  // View toggle: task-card view (default) or spreadsheet matrix. Persisted
  // per-browser via localStorage so admins stay in their preferred view.
  // The matrix needs horizontal real estate — we only allow it at ≥1024px.
  const VIEW_PREF_KEY = "assign.view";
  let viewMode = $state<"task" | "spreadsheet">("task");
  let viewportWide = $state(true);

  function loadViewPref() {
    if (typeof window === "undefined") return;
    try {
      const stored = window.localStorage.getItem(VIEW_PREF_KEY);
      if (stored === "spreadsheet" || stored === "task") {
        viewMode = stored;
      }
    } catch {
      /* localStorage blocked — fall through with default */
    }
  }

  function setViewMode(next: "task" | "spreadsheet") {
    viewMode = next;
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(VIEW_PREF_KEY, next);
    } catch {
      /* localStorage blocked — preference doesn't persist this session */
    }
  }

  function checkViewport() {
    if (typeof window === "undefined") return;
    viewportWide = window.innerWidth >= 1024;
  }

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
  // Per-call fairness context drives the badges + sort. Rebuilds whenever
  // the overview changes — including after an assign/unassign round-trip,
  // which is what gives us live re-ranking on other task-cards.
  let fairness = $derived(
    overview
      ? buildFairnessContext(overview.volunteers, overview.tasks)
      : null,
  );
  let expandedConflicts = $state<Set<string>>(new Set());

  function toggleConflicts(taskId: string) {
    const next = new Set(expandedConflicts);
    if (next.has(taskId)) next.delete(taskId);
    else next.add(taskId);
    expandedConflicts = next;
  }

  onMount(() => {
    loadViewPref();
    checkViewport();
    window.addEventListener("resize", checkViewport);

    // Kick off the load + team-lead fetch but don't return a Promise from
    // onMount — Svelte 5 expects either void or a cleanup function.
    (async () => {
      await load();
      try {
        const leads = await people.list({ role: "team_leader", active: true });
        teamLeads = leads.items.map((p) => ({
          id: p.id,
          first_name: p.first_name,
          last_name: p.last_name,
        }));
      } catch {
        // Non-fatal — the team-lead select will simply be empty.
      }
    })();

    return () => window.removeEventListener("resize", checkViewport);
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

  async function refreshTask(_taskId: string) {
    // Full overview refresh — needed for live re-rank on OTHER task-cards
    // (assigning Bryan to task 1 bumps Bryan down in task 2's list because
    // his assignments_this_call goes up). The _taskId arg is unused but
    // kept for callsite readability.
    overview = await volunteerCalls.assignmentOverview(callId);
  }

  async function assign(
    taskId: string,
    candidate: AvailableVolunteer,
    isConflictOverride = false,
  ) {
    if (busyTaskIds.has(taskId)) return;
    if (isConflictOverride) {
      const ok = confirm(
        `${candidate.person_name} is already assigned to another task on this date. Assign anyway?`,
      );
      if (!ok) return;
    }
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

  function fillState(t: TaskOverviewItem): "under" | "full" | "over" {
    if (t.assignments.length > t.volunteers_needed) return "over";
    if (t.assignments.length === t.volunteers_needed) return "full";
    return "under";
  }

  // Re-entry mode: when admin landed here via "Update Assignments" on
  // an already-ASSIGNED call, the call's state machine has already moved
  // past WAITING — done-assigning would error. In that case the button
  // is a plain "Done" that just returns to the list (per-click assigns
  // are already persisted live).
  let isAlreadyAssigned = $derived(overview?.call_status === "assigned");
  let saveButtonLabel = $derived(
    saving
      ? "Saving..."
      : isAlreadyAssigned
        ? "Done"
        : "Done Assigning",
  );

  let autoLeadsBusy = $state(false);

  // True when the call has at least one task missing a team lead — drives
  // the visibility/enabled state of the "Auto-assign Team Leads" button.
  let needsLeadCount = $derived(
    overview ? overview.tasks.filter((t) => t.team_lead_id == null).length : 0,
  );

  async function autoAssignLeads() {
    if (autoLeadsBusy) return;
    autoLeadsBusy = true;
    error = null;
    try {
      const result = await volunteerCalls.autoAssignTeamLeads(callId);
      // Reload the overview so the team-lead selects + counts reflect
      // the new state — same pattern as assign/unassign.
      overview = await volunteerCalls.assignmentOverview(callId);
      if (result.tasks_skipped > 0 && result.tasks_updated === 0) {
        error = `No eligible team leads found for ${result.tasks_skipped} task(s).`;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to auto-assign team leads";
    } finally {
      autoLeadsBusy = false;
    }
  }

  async function handleSave() {
    if (saving) return;
    // Re-entry case: no API call needed; assignments persisted on each
    // assign/unassign click. The button is just an explicit "back to list".
    if (!canSave) return;
    if (isAlreadyAssigned) {
      await goto("/volunteer-calls");
      return;
    }
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

<div class="assign-page page-full">
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
          {#if gateMessage}<span class="gate-icon" aria-hidden="true">⚠️</span>{/if}
          {gateMessage}
        </div>
      </div>

      <div class="actions-col">
        <label class="policy-label">
          <span class="policy-prefix">Desired</span>
          <select bind:value={policy} aria-label="Desired">
            <option value="exact">{ASSIGNMENT_POLICY_LABELS.exact}</option>
            <option value="over">{ASSIGNMENT_POLICY_LABELS.over}</option>
            <option value="over_under">
              {ASSIGNMENT_POLICY_LABELS.over_under}
            </option>
          </select>
        </label>
        <div class="action-buttons">
          {#if needsLeadCount > 0}
            <button
              type="button"
              class="btn btn-secondary auto-leads-btn"
              disabled={autoLeadsBusy}
              onclick={autoAssignLeads}
              title="Pick the least-recently-assigned team lead for each unstaffed task"
            >
              {autoLeadsBusy
                ? "Picking…"
                : `Auto-pick Team Leads (${needsLeadCount})`}
            </button>
          {/if}
          <button
            type="button"
            class="btn btn-primary save-btn"
            disabled={saving || !canSave}
            onclick={handleSave}
            aria-label={isAlreadyAssigned ? "Back to calls" : "Complete assignment"}
          >
            {saveButtonLabel}
          </button>
        </div>
      </div>
    </div>

    <div class="view-tabs" role="tablist" aria-label="Assignment view">
      <button
        type="button"
        role="tab"
        aria-selected={viewMode === "task"}
        class="view-tab"
        class:active={viewMode === "task"}
        onclick={() => setViewMode("task")}
      >
        Task View
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={viewMode === "spreadsheet"}
        class="view-tab"
        class:active={viewMode === "spreadsheet"}
        disabled={!viewportWide}
        title={viewportWide ? "" : "Spreadsheet view requires a wider screen"}
        onclick={() => setViewMode("spreadsheet")}
      >
        Spreadsheet View
      </button>
    </div>

    {#if overview.tasks.length === 0}
      <p class="empty">This call has no tasks.</p>
    {:else if viewMode === "spreadsheet" && viewportWide}
      <AssignmentSpreadsheet
        {overview}
        busyTaskIds={busyTaskIds}
        onAssign={assign}
        onUnassign={unassign}
      />
    {:else}
      {#if viewMode === "spreadsheet" && !viewportWide}
        <p class="empty">
          Spreadsheet view needs at least a 1024px-wide screen. Switch to
          Task View on this device.
        </p>
      {/if}
      <div class="task-cards">
        {#each overview.tasks as task (task.task_id)}
          {@const full = isFull(task)}
          {@const state = fillState(task)}
          <section class="task-card" class:full>
            <header class="card-header">
              <span class="date">{task.date ? formatDate(task.date) : "—"}</span>
              <span class="counts">
                {volunteersLabel(task.volunteers_needed, task.skilled_needed)}
              </span>
              <span class="city">{task.city ?? ""}</span>
              <span class="description">{task.short_description}</span>
              <span class="progress" class:full={state !== "under"}>
                {task.assignments.length}/{task.volunteers_needed}
                {#if state === "full"}<span class="full-tag">Full</span>{/if}
                {#if state === "over"}<span class="extra-tag">Extra!</span>{/if}
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
              <div class="list-block assigned-block">
                <h3 class="list-heading">Assigned</h3>
                {#if task.assignments.length === 0}
                  <p class="list-empty">No one assigned yet.</p>
                {:else}
                  <ul class="people">
                    {#each task.assignments as a (a.assignment_id)}
                      {@const b = fairness ? badgesFor(a.person_id, task, fairness) : null}
                      <li class="person assigned">
                        <button
                          type="button"
                          class="person-row"
                          aria-label="Unassign {a.person_name}"
                          disabled={busyTaskIds.has(task.task_id)}
                          onclick={() => unassign(task.task_id, a)}
                        >
                          <span class="check checked" aria-hidden="true"></span>
                          <span class="name">{truncateVolunteerName(a.person_name)}</span>
                          {#if b}
                            {#if b.fullyBookedWeeks.length}<span class="fairness-badge" title={b.fullyBookedReason}>💯</span>{/if}
                            {#if b.exhausted}<span class="fairness-badge" title={b.exhaustedReason}>🥵</span>{/if}
                            {#if b.idle}<span class="fairness-badge" title="Hasn't been assigned recently">😴</span>{/if}
                            {#if b.skilled}<span class="fairness-badge" title="Skilled volunteer">🛠️</span>{/if}
                          {/if}
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

              <div class="separator" aria-hidden="true"></div>
              <div class="list-block available-block">
                <h3 class="list-heading">Available</h3>
                {#if task.available_volunteers.length === 0}
                  <p class="list-empty">No more candidates.</p>
                {:else if fairness}
                  {@const part = partitionAvailable(task, fairness)}
                  {#if part.visible.length === 0 && part.hidden.length > 0}
                    <p class="list-empty">All {part.hidden.length} candidate{part.hidden.length === 1 ? "" : "s"} are already booked this day.</p>
                  {:else if part.visible.length === 0}
                    <p class="list-empty">No more candidates.</p>
                  {:else}
                    <ul class="people">
                      {#each part.visible as v (v.person_id)}
                        {@const b = badgesFor(v.person_id, task, fairness)}
                        <li class="person available">
                          <button
                            type="button"
                            class="person-row"
                            aria-label="Assign {v.person_name}"
                            disabled={busyTaskIds.has(task.task_id)}
                            onclick={() => assign(task.task_id, v)}
                          >
                            <span class="check" aria-hidden="true"></span>
                            <span class="name">{truncateVolunteerName(v.person_name)}</span>
                            {#if b.fullyBookedWeeks.length}<span class="fairness-badge" title={b.fullyBookedReason}>💯</span>{/if}
                            {#if b.exhausted}<span class="fairness-badge" title={b.exhaustedReason}>🥵</span>{/if}
                            {#if b.idle}<span class="fairness-badge" title="Hasn't been assigned recently">😴</span>{/if}
                            {#if b.skilled}<span class="fairness-badge" title="Skilled volunteer">🛠️</span>{/if}
                            {#each v.skills as s (s)}
                              <span class="badge {skillBadgeClass(s)}">{s}</span>
                            {/each}
                            <span class="action">Assign</span>
                          </button>
                        </li>
                      {/each}
                    </ul>
                  {/if}
                  {#if part.hidden.length > 0}
                    <button
                      type="button"
                      class="conflicts-toggle"
                      onclick={() => toggleConflicts(task.task_id)}
                    >
                      {expandedConflicts.has(task.task_id) ? "Hide" : "Show"}
                      {part.hidden.length}
                      already booked this day
                    </button>
                    {#if expandedConflicts.has(task.task_id)}
                      <ul class="people conflicts">
                        {#each part.hidden as v (v.person_id)}
                          {@const b = badgesFor(v.person_id, task, fairness)}
                          <li class="person available conflict">
                            <button
                              type="button"
                              class="person-row"
                              aria-label="Assign {v.person_name} (already booked this day)"
                              disabled={busyTaskIds.has(task.task_id)}
                              onclick={() => assign(task.task_id, v, true)}
                              title="Already assigned to another task on this date"
                            >
                              <span class="check" aria-hidden="true"></span>
                              <span class="name">{truncateVolunteerName(v.person_name)}</span>
                              <span class="fairness-badge" title="Same-day conflict">‼️</span>
                              {#if b.fullyBookedWeeks.length}<span class="fairness-badge" title={b.fullyBookedReason}>💯</span>{/if}
                              {#if b.exhausted}<span class="fairness-badge" title={b.exhaustedReason}>🥵</span>{/if}
                              {#if b.skilled}<span class="fairness-badge" title="Skilled volunteer">🛠️</span>{/if}
                              <span class="action">Override</span>
                            </button>
                          </li>
                        {/each}
                      </ul>
                    {/if}
                  {/if}
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
  /* The page itself is full-viewport so the spreadsheet view can use all
     horizontal real estate, but the page header (title, top-bar, view
     tabs) and the task-card stack don't benefit from being wider than the
     cards themselves — keep them aligned to the same left-aligned 1400px
     frame so the chrome doesn't sprawl on ultrawide monitors. */
  .assign-page > h1,
  .assign-page > :global(.breadcrumb),
  .top-bar,
  .view-tabs,
  .task-cards {
    max-width: 1400px;
    width: 100%;
  }

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
    font-size: calc(var(--font-size-sm) * 1.5);
    font-weight: 700;
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
    font-size: calc(var(--font-size-sm) * 1.6);
    color: var(--rt-text-light, #d81010);
    line-height: 1.3;
  }

  .message-area[data-area="gate"] {
    color: var(--rt-warning-text, #e1b402);
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .gate-icon {
    font-size: 1em;
    line-height: 1;
    flex-shrink: 0;
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
    font-size: calc(var(--font-size-sm) * 1.5);
    font-weight: 700;
  }

  .policy-prefix {
    color: var(--color-text);
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

  .action-buttons {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .auto-leads-btn {
    white-space: nowrap;
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

  .view-tabs {
    display: flex;
    gap: 2px;
    margin-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--rt-gray-200, #e4dfda);
  }

  .view-tab {
    padding: var(--spacing-xs) var(--spacing-md);
    background: transparent;
    border: 0;
    border-bottom: 2px solid transparent;
    color: var(--rt-text-muted, #777);
    cursor: pointer;
    font: inherit;
    font-weight: 500;
    margin-bottom: -1px;
  }

  .view-tab.active {
    color: var(--color-primary, #3a6db5);
    border-bottom-color: var(--color-primary, #3a6db5);
  }

  .view-tab:hover:not(:disabled):not(.active) {
    color: var(--color-text);
  }

  .view-tab:disabled {
    cursor: not-allowed;
    opacity: 0.4;
  }

  .task-cards {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    /* The page itself is full-viewport (so the spreadsheet view can use
       all the horizontal real estate), but the task cards don't benefit
       from being arbitrarily wide — cap so each card has comfortable
       room for two volunteer columns at any density without growing to
       fill an ultrawide monitor. */
    max-width: 1400px;
    width: 100%;
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
    font-weight: 800;
  }

  .full-tag,
  .extra-tag {
    font-size: var(--font-size-xs);
    color: var(--rt-white, #fff);
    padding: 1px 6px;
    border-radius: 10px;
    font-weight: 500;
  }

  .full-tag {
    background: var(--rt-success-text, #2f7a45);
  }

  .extra-tag {
    background: var(--rt-warning-text, #b35900);
  }

  .lists {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 1px minmax(0, 1fr);
    /* Don't stretch the shorter column to match the taller one — keeps
       both lists visually anchored at the top once one column scrolls. */
    align-items: start;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
  }

  .list-block {
    min-width: 0;
  }

  .lists .separator {
    align-self: stretch;
    width: 1px;
    background: var(--rt-gray-200, #e4dfda);
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
    /* Grid (not flex) so stray whitespace text nodes inside {#each} don't
       become flex items that consume vertical leading. Single column by
       default; two columns when the card has room (see media query). */
    display: grid;
    grid-template-columns: 1fr;
    grid-auto-rows: max-content;
    /* `align-content: start` keeps the rows from being spread when the ul
       has extra vertical space (e.g. when its sibling list-block is taller
       and grid `align-items` stretches the list-block). `align-items:
       start` keeps each <li> hugging the top of its row instead of
       stretching to fill it. */
    align-content: start;
    align-items: start;
    gap: 2px 12px;
    /* When many volunteers respond, the Available column can dwarf the
       Assigned column — bound both at the same height and let the longer
       one scroll. Roughly six rows tall. */
    max-height: 16em;
    overflow-y: auto;
  }

  /* Reset default <li>/button box model so the row's height is exactly
     the button's content + padding. Without these, browser/UA quirks
     (margin on <li>, min-height inherited via flow root, etc.) leave a
     tall blank slot below each name in the Available column. */
  ul.people > li.person {
    margin: 0;
    padding: 0;
    min-height: 0;
  }

  @media (min-width: 900px) {
    ul.people {
      grid-template-columns: 1fr 1fr;
      grid-auto-flow: row;
    }
  }

  .person-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
    margin: 0;
    /* Explicit min-height: 0 overrides anything inherited (the global
       .btn rule sets min-height: 44px and some browsers' UA button
       stylesheet adds its own) so the button's height is just padding +
       content. */
    min-height: 0;
    padding: 2px var(--spacing-sm);
    line-height: 1.5;
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

  .check {
    flex-shrink: 0;
    box-sizing: border-box;
    display: inline-block;
    position: relative;
    width: 14px;
    height: 14px;
    border: 1.5px solid var(--rt-gray-400, #b3aea7);
    border-radius: 3px;
    background: #fff;
  }

  .check.checked {
    background: var(--rt-success-text, #2f7a45);
    border-color: var(--rt-success-text, #2f7a45);
  }

  .check.checked::after {
    content: "";
    position: absolute;
    left: 3px;
    top: 0;
    width: 4px;
    height: 8px;
    border: solid #fff;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }

  .name {
    flex: 1;
    min-width: 0;
    /* Width budget is computed from --volunteer-name-display-max so the
       two-column Available/Assigned grid lines up at every density. The
       truncateVolunteerName() helper trims the text first, so the
       text-overflow ellipsis is a defensive secondary clip only. */
    max-width: var(--volunteer-name-max-width);
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

  .fairness-badge {
    flex-shrink: 0;
    font-size: 0.95em;
    line-height: 1;
  }

  .conflicts-toggle {
    margin-top: var(--spacing-xs);
    padding: 4px 8px;
    background: transparent;
    border: 1px dashed var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    color: var(--rt-text-muted, #777);
    font-size: var(--font-size-xs);
    cursor: pointer;
    width: 100%;
    text-align: left;
  }

  .conflicts-toggle:hover {
    background: var(--rt-gray-50, #fafaf7);
    color: var(--color-text);
  }

  ul.people.conflicts {
    opacity: 0.7;
    margin-top: 4px;
  }

  .person.conflict .person-row {
    border-color: var(--rt-warning-text, #b35900);
    background: var(--rt-warning-bg, #fff7e6);
  }

  .person-row:hover:not(:disabled) .action {
    color: var(--color-primary, #3a6db5);
  }

  @media (max-width: 768px) {
    .lists {
      grid-template-columns: 1fr;
    }
    .lists .separator {
      display: none;
    }
    ul.people {
      grid-template-columns: 1fr;
    }
  }
</style>
