<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { page } from '$app/state';
  import { authState, consumeInvitedCallId, initFromToken } from '$lib/stores/auth.svelte';
  import {
    volunteering,
    volunteerCalls,
    volunteerAvailability,
    type MyAssignment,
    type VolunteerCallListResponse,
    type JobListItem,
    type AvailabilityResponse,
    type AvailabilityCreate,
    type TaskConflicts,
    type CallStatus,
  } from '$lib/api/client';
  import { formatDate } from '$lib/utils/format';
  import {
    googleCalendarUrl,
    downloadIcs,
    type CalendarEvent,
  } from '$lib/utils/add-to-calendar';
  import { tasksSpanMultipleWeeks } from '$lib/utils/task-weeks';
  import ItemCard from '$lib/components/ItemCard.svelte';
  import ListViewToggle from '$lib/components/ListViewToggle.svelte';
  import DataTable from '$lib/components/DataTable.svelte';
  import { settingsState, setListView } from '$lib/stores/settings.svelte';
  import { truncateText } from '$lib/components/data-table';
  import type { Column, SortDir } from '$lib/components/data-table';

  // Per-week task-cap options. 1-5 with no "Any" pseudo-value — the
  // pulldown is short enough to scan without a special case.
  const MAX_WEEK_OPTIONS = [1, 2, 3, 4, 5];
  const DEFAULT_MAX_PER_WEEK = 2;

  let assignments = $state<MyAssignment[]>([]);
  let openCalls = $state<VolunteerCallListResponse[]>([]);
  let loading = $state(true);
  let error = $state('');

  // Per-call state keyed by call ID
  let callJobs = $state<Record<string, JobListItem[]>>({});
  // Availability keyed by callId -> taskId -> AvailabilityResponse
  let callAvail = $state<Record<string, Record<string, AvailabilityResponse>>>({});
  // Call-level availability (task_id is null) for max_tasks_per_week
  let callLevelAvail = $state<Record<string, AvailabilityResponse | null>>({});
  let checkedTasks = $state<Record<string, Set<string>>>({});
  let maxPerWeek = $state<Record<string, number>>({});
  let maxPerWeek2 = $state<Record<string, number>>({});
  let expandedTasks = $state<Set<string>>(new Set());
  let saving = $state<Record<string, boolean>>({});
  let saveMessage = $state<Record<string, string>>({});
  let loadingCalls = $state<Set<string>>(new Set());

  // Calendar conflicts: {callId: {taskId: TaskConflicts}}. Empty if the
  // user hasn't connected a calendar.
  let callConflicts = $state<Record<string, Record<string, TaskConflicts>>>({});

  function formatTime(t: string | null): string {
    if (!t) return '';
    // Handle HH:MM or HH:MM:SS formats
    const parts = t.split(':');
    if (parts.length < 2) return t;
    const hour = parseInt(parts[0], 10);
    const minute = parts[1];
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const display = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${display}:${minute} ${ampm}`;
  }

  function formatTimeRange(start: string | null, end: string | null): string {
    if (!start && !end) return '';
    if (start && end) return `${formatTime(start)} - ${formatTime(end)}`;
    return formatTime(start) || formatTime(end);
  }

  // The call this user was deep-linked to from an invite email. Pulled
  // off the auth store once at mount; consumed (cleared) so it doesn't
  // re-fire on subsequent navigations within the SPA.
  let deepLinkCallId = $state<string | null>(null);

  onMount(async () => {
    const token = page.url.searchParams.get('token');
    await initFromToken(token);
    if (!authState.user) return;

    deepLinkCallId = consumeInvitedCallId();

    try {
      const [a, c] = await Promise.all([
        volunteering.myAssignments(),
        // Volunteer-facing visibility: a call is in `waiting` once admin
        // has sent invites (OPEN → WAITING) and stays visible until Done
        // Assigning flips it to ASSIGNED.
        volunteerCalls.list({ status: 'waiting' }),
      ]);
      assignments = a;
      openCalls = c;

      // If the user followed an invite link for a call that is no longer
      // WAITING (typically ASSIGNED, occasionally ARCHIVED), it won't be
      // in the list above — fetch it explicitly so we can still show it
      // with the appropriate banner.
      if (deepLinkCallId && !openCalls.some((c) => c.id === deepLinkCallId)) {
        try {
          const linked = await volunteerCalls.get(deepLinkCallId);
          openCalls = [
            {
              id: linked.id,
              title: linked.title,
              program: linked.program,
              status: linked.status,
              task_count: 0,
              created_at: linked.created_at,
              updated_at: linked.updated_at,
            } as VolunteerCallListResponse,
            ...openCalls,
          ];
        } catch {
          // Token verified ok but call lookup failed — surface nothing;
          // the page still loads the user's normal calls below.
        }
      }

      await Promise.all(openCalls.map((call) => loadCallData(call.id)));

      // After render, scroll the deep-linked call into view.
      if (deepLinkCallId) {
        await tick();
        const el = document.getElementById(`call-${deepLinkCallId}`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load';
    } finally {
      loading = false;
    }
  });

  function canSubmitAvailability(status: CallStatus): boolean {
    return status === 'waiting' || status === 'assigned';
  }

  function bannerFor(status: CallStatus): { tone: 'amber' | 'gray'; text: string } | null {
    if (status === 'assigned') {
      return {
        tone: 'amber',
        text:
          'This call has already been assigned. You can still indicate availability ' +
          'in case volunteer needs change.',
      };
    }
    if (status === 'archived' || status === 'open') {
      return { tone: 'gray', text: 'This call is closed.' };
    }
    return null;
  }

  async function loadCallData(callId: string) {
    loadingCalls.add(callId);
    loadingCalls = loadingCalls;
    try {
      const [jobList, availList, conflicts] = await Promise.all([
        volunteerCalls.listJobs(callId),
        volunteerAvailability.list(callId),
        // Conflicts are best-effort — a backend hiccup or an unreachable
        // calendar provider must not break the page.
        volunteerCalls.calendarConflicts(callId).catch(() => [] as TaskConflicts[]),
      ]);
      callJobs[callId] = jobList;
      const byTask: Record<string, TaskConflicts> = {};
      for (const c of conflicts) byTask[c.task_id] = c;
      callConflicts[callId] = byTask;

      // Filter to current user's availability records
      const myAvails = authState.user
        ? availList.filter((a) => a.person_id === authState.user!.id)
        : [];

      // Build task-level map and find call-level record
      const taskMap: Record<string, AvailabilityResponse> = {};
      let callLevel: AvailabilityResponse | null = null;
      for (const avail of myAvails) {
        if (avail.task_id) {
          taskMap[avail.task_id] = avail;
        } else {
          callLevel = avail;
        }
      }
      callAvail[callId] = taskMap;
      callLevelAvail[callId] = callLevel;

      // Build checked set from task-level availability where available === true
      const checked = new Set<string>();
      for (const [taskId, avail] of Object.entries(taskMap)) {
        if (avail.available) {
          checked.add(taskId);
        }
      }
      checkedTasks[callId] = checked;

      // Per-week caps. Use the call-level availability when present,
      // else any task-level record, else the default. Both values are
      // always saved on submit even when the Week 2 pulldown is hidden,
      // so a stored value can survive a re-render that drops Week 2.
      const mpw =
        callLevel?.max_tasks_per_week
        ?? myAvails.find((a) => a.max_tasks_per_week !== null)?.max_tasks_per_week
        ?? DEFAULT_MAX_PER_WEEK;
      const mpw2 =
        callLevel?.max_tasks_per_week_2
        ?? myAvails.find((a) => a.max_tasks_per_week_2 !== null)?.max_tasks_per_week_2
        ?? DEFAULT_MAX_PER_WEEK;
      maxPerWeek[callId] = mpw;
      maxPerWeek2[callId] = mpw2;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load call data';
    } finally {
      loadingCalls.delete(callId);
      loadingCalls = loadingCalls;
    }
  }

  function toggleTask(callId: string, taskId: string) {
    const set = checkedTasks[callId] || new Set();
    if (set.has(taskId)) {
      set.delete(taskId);
    } else {
      set.add(taskId);
    }
    checkedTasks[callId] = new Set(set);
    saveMessage[callId] = '';
  }

  function toggleExpand(taskId: string) {
    if (expandedTasks.has(taskId)) {
      expandedTasks.delete(taskId);
    } else {
      expandedTasks.add(taskId);
    }
    expandedTasks = new Set(expandedTasks);
  }

  function setMaxPerWeek(callId: string, value: number) {
    maxPerWeek[callId] = value;
    saveMessage[callId] = '';
  }

  function setMaxPerWeek2(callId: string, value: number) {
    maxPerWeek2[callId] = value;
    saveMessage[callId] = '';
  }

  async function submitAvailability(callId: string) {
    if (!authState.user) return;
    saving[callId] = true;
    saving = saving;
    error = '';
    saveMessage[callId] = '';

    const jobs = callJobs[callId] || [];
    const selected = checkedTasks[callId] || new Set();
    const existingAvails = callAvail[callId] || {};
    const mpw = maxPerWeek[callId] ?? DEFAULT_MAX_PER_WEEK;
    // Always persist Week 2 even when the UI hides it (no week-2 tasks in
    // the call). Hiding is a display decision; the stored value is the
    // volunteer's preference and shouldn't be lost on a re-render.
    const mpw2 = maxPerWeek2[callId] ?? DEFAULT_MAX_PER_WEEK;

    try {
      // Submit or update per-task availability
      const promises: Promise<AvailabilityResponse>[] = [];

      for (const job of jobs) {
        const isAvailable = selected.has(job.task_id);
        const existing = existingAvails[job.task_id];

        if (existing) {
          // Update existing availability if the state changed
          if (
            existing.available !== isAvailable ||
            existing.max_tasks_per_week !== mpw ||
            existing.max_tasks_per_week_2 !== mpw2
          ) {
            promises.push(
              volunteerAvailability.update(callId, existing.id, {
                available: isAvailable,
                max_tasks_per_week: mpw,
                max_tasks_per_week_2: mpw2,
              }),
            );
          }
        } else if (isAvailable) {
          // Only create records for tasks marked available
          const data: AvailabilityCreate = {
            person_id: authState.user!.id,
            task_id: job.task_id,
            available: true,
            max_tasks_per_week: mpw,
            max_tasks_per_week_2: mpw2,
          };
          promises.push(volunteerAvailability.submit(callId, data));
        }
      }

      // If no per-task records but we need to save max_tasks_per_week at call level
      const existingCallLevel = callLevelAvail[callId];
      if (existingCallLevel) {
        if (
          existingCallLevel.max_tasks_per_week !== mpw ||
          existingCallLevel.max_tasks_per_week_2 !== mpw2
        ) {
          promises.push(
            volunteerAvailability.update(callId, existingCallLevel.id, {
              max_tasks_per_week: mpw,
              max_tasks_per_week_2: mpw2,
            }),
          );
        }
      } else if (promises.length === 0) {
        // Submit a call-level record if no tasks are selected
        promises.push(
          volunteerAvailability.submit(callId, {
            person_id: authState.user!.id,
            available: false,
            max_tasks_per_week: mpw,
            max_tasks_per_week_2: mpw2,
          }),
        );
      }

      await Promise.all(promises);
      saveMessage[callId] = 'Availability saved!';
      await loadCallData(callId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save availability';
    } finally {
      saving[callId] = false;
      saving = saving;
    }
  }

  const jobColumns: Column[] = [
    { key: 'checkbox', label: '', getValue: () => '', sortable: false },
    {
      key: 'short_description',
      label: 'Task',
      getValue: (item) => item.short_description as string,
      truncate: 40,
      sortable: false,
    },
    { key: 'city', label: 'City', getValue: (item) => (item.city as string) || '' },
    {
      key: 'date',
      label: 'Date',
      getValue: (item) => {
        const d = item.date as string | null;
        return d ? formatDate(d) : 'Unscheduled';
      },
    },
    {
      key: 'time',
      label: 'Time',
      getValue: (item) => formatTimeRange(item.time_start as string | null, item.time_end as string | null),
      hideOnNarrow: true,
    },
  ];

  let jobSortKey = $state('');
  let jobSortDir = $state<SortDir>('asc');

  function handleJobSort(key: string, dir: SortDir) {
    jobSortKey = key;
    jobSortDir = dir;
  }

  function calendarEventFor(a: MyAssignment): CalendarEvent | null {
    if (!a.date) return null;
    return {
      date: a.date,
      time_start: a.time_start,
      time_end: a.time_end,
      title: `RT-AFF Volunteer - ${a.task_description}`,
      location: a.address ?? null,
      description: `Volunteer call: ${a.call_title}`,
    };
  }

  function googleUrlFor(a: MyAssignment): string | null {
    const e = calendarEventFor(a);
    return e ? googleCalendarUrl(e) : null;
  }

  function downloadIcsFor(a: MyAssignment): void {
    const e = calendarEventFor(a);
    if (e) downloadIcs(e);
  }

  function hasExistingAvailability(callId: string): boolean {
    const taskAvails = callAvail[callId];
    if (taskAvails && Object.keys(taskAvails).length > 0) return true;
    return callLevelAvail[callId] !== null && callLevelAvail[callId] !== undefined;
  }

</script>

<svelte:head>
  <title>Volunteering - RT-AFF</title>
</svelte:head>

<div class="page-md">
  <h1>Volunteering</h1>

  {#if loading}
    <p class="loading-text">Loading...</p>
  {:else if error}
    <div class="alert alert-error">{error}</div>
  {:else}
    <section class="section">
      <h2>Volunteer Calls <em class="section-sub">waiting for volunteers</em></h2>
      {#if authState.user && !authState.user.calendar_connected}
        <p class="settings-hint">
          See <a href="/settings">Settings</a> to connect your calendar and detect conflicts.
        </p>
      {/if}
      {#if openCalls.length === 0}
        <p class="empty-text">No volunteer calls are looking for volunteers right now.</p>
      {:else}
        {#each openCalls as call (call.id)}
          {@const banner = bannerFor(call.status)}
          {@const canSubmit = canSubmitAvailability(call.status)}
          <div
            class="call-section"
            class:call-section-deeplink={deepLinkCallId === call.id}
            id={`call-${call.id}`}
          >
            <div class="call-header">
              <span class="call-title">{call.title}</span>
              <span class="call-meta">{call.task_count} task{call.task_count === 1 ? '' : 's'}</span>
            </div>

            {#if banner}
              <div class="call-banner call-banner-{banner.tone}" role="status">
                {banner.text}
              </div>
            {/if}

            {#if !canSubmit}
              <!-- Archived/open: banner says enough; suppress task list & controls. -->
            {:else if loadingCalls.has(call.id)}
              <p class="loading-text">Loading tasks...</p>
            {:else}
              {@const jobs = callJobs[call.id] || []}
              {@const selected = checkedTasks[call.id] || new Set()}
              {@const mpw = maxPerWeek[call.id] ?? DEFAULT_MAX_PER_WEEK}
              {@const mpw2 = maxPerWeek2[call.id] ?? DEFAULT_MAX_PER_WEEK}
              {@const showWeek2 = tasksSpanMultipleWeeks(jobs)}

              {#if jobs.length === 0}
                <p class="empty-text">No tasks posted yet for this call.</p>
              {:else}
                <div class="max-week-row">
                  <span class="max-week-label">Maximum tasks:</span>
                  <label class="week-pick">
                    <span class="week-pick-label">{showWeek2 ? 'Week 1' : 'per week'}</span>
                    <select
                      value={mpw}
                      onchange={(e) => setMaxPerWeek(call.id, parseInt((e.currentTarget as HTMLSelectElement).value, 10))}
                      aria-label={showWeek2 ? 'Maximum tasks, week 1' : 'Maximum tasks per week'}
                    >
                      {#each MAX_WEEK_OPTIONS as n (n)}
                        <option value={n}>{n}</option>
                      {/each}
                    </select>
                  </label>
                  {#if showWeek2}
                    <label class="week-pick">
                      <span class="week-pick-label">Week 2</span>
                      <select
                        value={mpw2}
                        onchange={(e) => setMaxPerWeek2(call.id, parseInt((e.currentTarget as HTMLSelectElement).value, 10))}
                        aria-label="Maximum tasks, week 2"
                      >
                        {#each MAX_WEEK_OPTIONS as n (n)}
                          <option value={n}>{n}</option>
                        {/each}
                      </select>
                    </label>
                  {/if}
                </div>

                <div class="list-header-row">
                  <ListViewToggle view={settingsState.listView} onchange={setListView} />
                </div>

                {#if settingsState.listView === 'table'}
                  <DataTable
                    items={jobs}
                    columns={jobColumns}
                    sortKey={jobSortKey}
                    sortDir={jobSortDir}
                    onsort={handleJobSort}
                  >
                    {#snippet rowSnippet(item)}
                      {@const job = item as unknown as JobListItem}
                      {@const isChecked = selected.has(job.task_id)}
                      <tr class:table-row-checked={isChecked}>
                        <td class="check-cell">
                          <label class="task-check">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onchange={() => toggleTask(call.id, job.task_id)}
                            />
                          </label>
                        </td>
                        <td title={job.short_description.length > 40 ? job.short_description : undefined}>
                          {truncateText(job.short_description, 40)}
                        </td>
                        <td>{job.city || ''}</td>
                        <td>{job.date ? formatDate(job.date) : 'Unscheduled'}</td>
                        <td class="hide-narrow">{formatTimeRange(job.time_start, job.time_end)}</td>
                      </tr>
                    {/snippet}
                  </DataTable>
                {:else}
                  <div class="task-list">
                    {#each jobs as job (job.task_id)}
                      {@const expanded = expandedTasks.has(job.task_id)}
                      {@const checked = selected.has(job.task_id)}
                      {@const conflict = callConflicts[call.id]?.[job.task_id]}
                      <ItemCard {checked}>
                        <div class="task-row">
                          <label class="task-check">
                            <input
                              type="checkbox"
                              checked={checked}
                              onchange={() => toggleTask(call.id, job.task_id)}
                            />
                          </label>
                          <div class="task-info" role="button" tabindex="0"
                            onclick={() => toggleExpand(job.task_id)}
                            onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(job.task_id); } }}
                          >
                            <span class="task-name">
                              {job.short_description}
                              {#if conflict?.has_conflict}
                                <span class="conflict-flag" title={conflict.conflicts.map(c => c.summary ?? 'Calendar event').join('; ')}>
                                  ⚠ calendar conflict
                                </span>
                              {/if}
                            </span>
                            <span class="task-meta">
                              {#if job.city}{job.city} &middot; {/if}{job.date ? formatDate(job.date) : 'Unscheduled'}
                            </span>
                          </div>
                          <button
                            type="button"
                            class="expand-btn"
                            aria-label={expanded ? 'Collapse' : 'Expand'}
                            onclick={() => toggleExpand(job.task_id)}
                          >
                            <span class="chevron" class:open={expanded}>&#9660;</span>
                          </button>
                        </div>

                        {#if expanded}
                          <div class="task-details">
                            {#if job.time_start || job.time_end}
                              <div class="detail-row">
                                <span class="detail-label">Time:</span>
                                <span>{formatTimeRange(job.time_start, job.time_end)}</span>
                              </div>
                            {/if}
                            <div class="detail-row">
                              <span class="detail-label">Volunteers needed:</span>
                              <span>{job.volunteers_needed}</span>
                            </div>
                            {#if job.skilled_needed > 0}
                              <div class="detail-row">
                                <span class="detail-label">Skilled needed:</span>
                                <span>{job.skilled_needed}</span>
                              </div>
                            {/if}
                            {#if job.notes}
                              <div class="detail-row notes-row">
                                <span class="detail-label">Notes:</span>
                                <span>{job.notes}</span>
                              </div>
                            {/if}
                          </div>
                        {/if}
                      </ItemCard>
                    {/each}
                  </div>
                {/if}

                {#if saveMessage[call.id]}
                  <div class="success-banner">{saveMessage[call.id]}</div>
                {/if}

                {#if canSubmit}
                  <button
                    class="btn btn-primary submit-btn"
                    onclick={() => submitAvailability(call.id)}
                    disabled={saving[call.id]}
                  >
                    {#if saving[call.id]}
                      Saving...
                    {:else if hasExistingAvailability(call.id)}
                      Update Availability
                    {:else}
                      Submit Availability
                    {/if}
                  </button>
                {/if}
              {/if}
            {/if}
          </div>
        {/each}
      {/if}
    </section>

    <section class="section">
      <h2>My Assignments</h2>
      {#if assignments.length === 0}
        <p class="empty-text">No assignments yet. Sign up for a volunteer call above!</p>
      {:else}
        <div class="assignment-list">
          {#each assignments as a (a.assignment_id)}
            <ItemCard>
              <div class="assignment-header">
                <span class="assignment-name">{a.task_description}</span>
                <span class="assignment-role badge badge-{a.role}">{a.role === 'team_leader' ? 'Team Leader' : 'Volunteer'}</span>
              </div>
              {#if a.address || a.city}
                <div class="assignment-detail">
                  <span>{[a.address, a.city].filter(Boolean).join(', ')}</span>
                </div>
              {/if}
              <div class="assignment-detail">
                <span>{a.date ? formatDate(a.date) : 'Date TBD'}</span>
                {#if a.time_start || a.time_end}
                  <span>{formatTimeRange(a.time_start, a.time_end)}</span>
                {/if}
              </div>
              <div class="assignment-actions">
                <span class="confirmed-badge" class:confirmed={a.confirmed}>
                  {a.confirmed ? 'Confirmed' : 'Pending'}
                </span>
                {#if a.date}
                  {@const gUrl = googleUrlFor(a)}
                  {#if gUrl}
                    <a class="btn btn-sm btn-outline" href={gUrl} target="_blank" rel="noopener noreferrer" title="Open in Google Calendar">
                      Add to Google Calendar
                    </a>
                  {/if}
                  <button class="btn btn-sm btn-link" title="Download .ics for Apple/Outlook" onclick={() => downloadIcsFor(a)}>
                    .ics
                  </button>
                {/if}
              </div>
            </ItemCard>
          {/each}
        </div>
      {/if}
    </section>
  {/if}
</div>

<style>
  .section {
    margin-bottom: var(--spacing-xl, 2rem);
  }

  .section h2 {
    font-size: 1.25rem;
    margin-bottom: var(--spacing-md, 1rem);
    border-bottom: 1px solid var(--rt-gray-200, #e4dfda);
    padding-bottom: var(--spacing-sm);
  }

  .section-sub {
    font-style: italic;
    font-weight: 400;
    color: var(--rt-text-muted, #777);
    font-size: 0.95rem;
  }

  .loading-text, .empty-text {
    color: var(--rt-text-muted, #777);
    font-style: italic;
  }

  /* Call section */
  .call-section {
    margin-bottom: var(--spacing-xl);
    padding: var(--spacing-md);
    background: var(--rt-gray-50, #f8f6f3);
    border-radius: var(--card-radius, 8px);
    border: 1px solid var(--rt-gray-200, #e4dfda);
  }

  .call-section-deeplink {
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.12);
  }

  .call-banner {
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--card-radius, 8px);
    margin-bottom: var(--spacing-md);
    font-size: var(--font-size-sm);
    line-height: 1.4;
  }

  .call-banner-amber {
    background: var(--rt-warning-bg, #fff5e6);
    color: var(--rt-warning-text, #b35900);
    border: 1px solid #f0c476;
  }

  .call-banner-gray {
    background: var(--rt-gray-100, #f0ece8);
    color: var(--rt-text-light, #555);
    border: 1px solid var(--rt-gray-200, #e4dfda);
  }

  .call-header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .call-title {
    font-weight: 600;
    font-size: 1.1rem;
    color: var(--color-primary, #3a6db5);
  }

  .call-meta {
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
  }

  /* Maximum-tasks row: a compact single-line picker with per-week
     pulldowns. Week 2 is appended only when the call's tasks actually
     span into a second ISO week. */
  .max-week-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm) var(--spacing-md);
    margin-bottom: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .max-week-label {
    font-weight: 600;
    font-size: var(--font-size-sm);
  }

  .week-pick {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: var(--font-size-sm);
  }

  .week-pick-label {
    color: var(--rt-text-muted, #777);
  }

  .week-pick select {
    padding: 2px var(--spacing-sm);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
    font: inherit;
    background: var(--rt-white, #fff);
    min-height: 28px;
  }

  .list-header-row {
    display: flex;
    justify-content: flex-end;
    margin-bottom: var(--spacing-sm);
  }

  .check-cell {
    width: 44px;
    text-align: center;
  }

  .table-row-checked {
    background: var(--rt-checked-bg, #f0f7f2);
  }

  .align-right {
    text-align: right;
  }

  @media (max-width: 600px) {
    .hide-narrow {
      display: none;
    }
  }

  /* Task cards */
  .task-list {
    display: grid;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .task-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-md) var(--spacing-md);
    min-height: 56px;
  }

  .task-check {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .task-check input[type=checkbox] {
    width: 22px;
    height: 22px;
    cursor: pointer;
    accent-color: var(--rt-green, #4a7c59);
  }

  .task-info {
    flex: 1;
    min-width: 0;
    cursor: pointer;
  }

  .task-name {
    display: block;
    font-weight: 600;
    font-size: var(--btn-font-size);
  }

  .task-meta {
    display: block;
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
    margin-top: 0.125rem;
  }

  .conflict-flag {
    display: inline-block;
    margin-left: var(--spacing-sm);
    padding: 1px 6px;
    background: var(--rt-warning-bg, #fff5e6);
    color: var(--rt-warning-text, #b35900);
    border-radius: 10px;
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .expand-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: var(--spacing-sm);
    min-width: 44px;
    min-height: var(--btn-min-height);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .chevron {
    display: inline-block;
    font-size: var(--font-size-xs);
    color: var(--rt-text-muted, #777);
    transition: transform 0.2s;
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .task-details {
    padding: var(--spacing-xs) var(--spacing-md) var(--spacing-md) 3.5rem;
  }

  .detail-row {
    font-size: var(--font-size-sm);
    color: var(--rt-text-light, #555);
    padding: 0.125rem 0;
  }

  .detail-label {
    font-weight: 500;
    margin-right: var(--spacing-xs);
  }

  .notes-row {
    white-space: pre-wrap;
  }

  .success-banner {
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
    padding: var(--spacing-md) var(--spacing-md, 1rem);
    border-radius: var(--card-radius);
    margin-bottom: var(--spacing-md);
  }

  .submit-btn {
    min-height: 48px;
    font-size: var(--btn-font-size);
    width: 100%;
    max-width: 300px;
  }

  /* Assignment cards */
  .assignment-list {
    display: grid;
    gap: var(--spacing-md);
  }

  .assignment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .assignment-name {
    font-weight: 600;
    font-size: var(--btn-font-size);
  }

  .assignment-role {
    font-size: var(--font-size-sm);
    padding: 2px var(--spacing-sm);
    border-radius: 4px;
    background: var(--rt-gray-100, #f0ece8);
  }

  .assignment-detail {
    display: flex;
    gap: var(--spacing-md);
    font-size: var(--font-size-sm);
    color: var(--rt-text-light, #555);
  }

  .assignment-actions {
    display: flex;
    gap: var(--spacing-md);
    align-items: center;
    margin-top: var(--spacing-xs);
  }

  .confirmed-badge {
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
  }

  .confirmed-badge.confirmed {
    color: var(--rt-green, #4a7c59);
    font-weight: 500;
  }

  .btn-sm {
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: var(--font-size-sm);
  }

  .btn-outline {
    background: transparent;
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: 4px;
    cursor: pointer;
    color: inherit;
  }

  .btn-outline:hover {
    border-color: var(--color-primary, #3a6db5);
    color: var(--color-primary, #3a6db5);
  }
</style>
