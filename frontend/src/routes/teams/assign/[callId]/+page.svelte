<script lang="ts">
    import { page } from '$app/state';
    import { volunteerCalls, teamAssignments } from '$lib/api/client';
    import type {
        AssignmentOverviewResponse,
        TaskOverviewItem,
        VolunteerOverviewItem
    } from '$lib/api/types';
    import { formatDateShort } from '$lib/utils/format';
    import Breadcrumb from '$lib/components/Breadcrumb.svelte';

    const callId = page.params.callId as string;

    let overview: AssignmentOverviewResponse | null = $state(null);
    let loading = $state(true);
    let error = $state('');
    let weekStart: Date = $state(new Date());
    let weekEnd: Date = $state(new Date());
    let selectedTaskId: string | null = $state(null);
    let statusMessage = $state('');

    let visibleTasks = $derived.by(() => {
        if (!overview) return [] as TaskOverviewItem[];
        return overview.tasks.filter((t: TaskOverviewItem) => {
            if (!t.date) return false;
            const d = new Date(t.date + 'T00:00:00');
            return d >= weekStart && d <= weekEnd;
        });
    });

    let selectedTask: TaskOverviewItem | undefined = $derived(
        visibleTasks.find((t: TaskOverviewItem) => t.task_id === selectedTaskId)
    );

    let assignedToSelected: Set<string> = $derived(
        new Set(selectedTask?.assignments.map((a: { person_id: string }) => a.person_id) ?? [])
    );

    function weekAssignmentCount(personId: string): number {
        return visibleTasks.reduce(
            (count: number, task: TaskOverviewItem) =>
                count + (task.assignments.some((a: { person_id: string }) => a.person_id === personId) ? 1 : 0),
            0
        );
    }

    function volunteerState(
        vol: VolunteerOverviewItem
    ): 'available' | 'hidden' | 'at-limit' | 'assigned-to-selected' {
        if (!selectedTask) return 'available';
        if (assignedToSelected.has(vol.person_id)) return 'assigned-to-selected';
        if (!vol.available_task_ids.includes(selectedTask.task_id)) return 'hidden';
        const weekCount = weekAssignmentCount(vol.person_id);
        if (vol.max_tasks_per_week < 5 && weekCount >= vol.max_tasks_per_week)
            return 'at-limit';
        return 'available';
    }

    function volTooltip(vol: VolunteerOverviewItem, state: string): string {
        let tip = vol.person_name;
        tip += ` \u00b7 ${vol.skill_category}`;
        if (vol.phone) tip += ` \u00b7 ${vol.phone}`;
        tip += ` \u00b7 ${vol.assignments_this_call} assigned this call`;
        if (state === 'at-limit') tip += ' \u00b7 max tasks reached';
        return tip;
    }

    async function loadOverview() {
        loading = true;
        error = '';
        try {
            overview = await volunteerCalls.assignmentOverview(callId);
            initWeek();
        } catch (e: unknown) {
            error = e instanceof Error && e.message || 'Failed to load';
        } finally {
            loading = false;
        }
    }

    function initWeek() {
        if (!overview) return;
        const dates = overview.tasks
            .map((t: TaskOverviewItem) => t.date)
            .filter((d): d is string => d !== null)
            .sort();
        if (dates.length === 0) return;
        const start = new Date(dates[0] + 'T00:00:00');
        setWeekContaining(start);
    }

    function setWeekContaining(d: Date) {
        const day = d.getDay();
        const monday = new Date(d);
        monday.setDate(d.getDate() - ((day + 6) % 7));
        weekStart = monday;
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        weekEnd = sunday;
    }

    function taskDateRange(): { earliest: Date; latest: Date } | null {
        if (!overview) return null;
        const dates = overview.tasks
            .map((t: TaskOverviewItem) => t.date)
            .filter((d): d is string => d !== null)
            .sort();
        if (dates.length === 0) return null;
        return {
            earliest: new Date(dates[0] + 'T00:00:00'),
            latest: new Date(dates[dates.length - 1] + 'T00:00:00')
        };
    }

    function prevWeek() {
        const range = taskDateRange();
        if (!range) return;
        const prev = new Date(weekStart);
        prev.setDate(prev.getDate() - 7);
        const prevWeekEnd = new Date(prev.getTime() + 6 * 86400000);
        if (prevWeekEnd >= range.earliest) {
            setWeekContaining(prev);
        }
    }

    function nextWeek() {
        const range = taskDateRange();
        if (!range) return;
        const next = new Date(weekStart);
        next.setDate(next.getDate() + 7);
        if (next <= range.latest) {
            setWeekContaining(next);
        }
    }

    function selectTask(taskId: string) {
        if (selectedTaskId === taskId) {
            selectedTaskId = null;
            statusMessage = '';
        } else {
            selectedTaskId = taskId;
            const task = visibleTasks.find((t: TaskOverviewItem) => t.task_id === taskId);
            if (task) {
                const isFull = task.assignments.length >= task.volunteers_needed;
                statusMessage = isFull
                    ? `Add volunteers to fully staffed "${task.short_description}"`
                    : `Assign volunteers to "${task.short_description}"`;
            }
        }
    }

    async function assign(personId: string) {
        if (!selectedTaskId) return;
        try {
            await teamAssignments.create(callId, selectedTaskId, { person_id: personId });
            const prevTaskId = selectedTaskId;
            await loadOverview();
            const updatedTask = overview?.tasks.find((t: TaskOverviewItem) => t.task_id === prevTaskId);
            if (updatedTask && updatedTask.assignments.length >= updatedTask.volunteers_needed) {
                selectedTaskId = null;
                statusMessage = `"${updatedTask.short_description}" \u2014 fully staffed`;
            } else {
                selectedTaskId = prevTaskId;
            }
        } catch (e: unknown) {
            error = e instanceof Error && e.message || 'Failed to assign';
        }
    }

    async function unassign(taskId: string, assignmentId: string) {
        try {
            await teamAssignments.delete(callId, taskId, assignmentId);
            await loadOverview();
        } catch (e: unknown) {
            error = e instanceof Error && e.message || 'Failed to unassign';
        }
    }

    $effect(() => {
        loadOverview();
    });
</script>

<div class="page-lg">
    <Breadcrumb
        crumbs={[
            { label: 'Teams', href: '/teams' },
            { label: overview?.call_title ?? 'Assign', href: `/volunteer-calls/${callId}` },
            { label: 'Assign' }
        ]}
    />

    {#if loading}
        <p>Loading...</p>
    {:else if error}
        <p class="error-text">{error}</p>
    {:else if overview}
        <div class="week-nav">
            <button class="btn btn-secondary btn-sm" onclick={prevWeek}>&#9664; prev week</button>
            <span class="week-label">
                Week of {formatDateShort(weekStart.toISOString().slice(0, 10))}
                &ndash; {formatDateShort(weekEnd.toISOString().slice(0, 10))}
            </span>
            <button class="btn btn-secondary btn-sm" onclick={nextWeek}>next week &#9654;</button>
        </div>

        {#if statusMessage}
            <p class="status-message">{statusMessage}</p>
        {/if}

        <div class="assign-layout">
            <div class="pane projects-pane">
                <h3>Tasks</h3>
                {#if visibleTasks.length === 0}
                    <p class="text-muted">No tasks scheduled this week</p>
                {:else}
                    {#each visibleTasks as task (task.task_id)}
                        {@const isFull = task.assignments.length >= task.volunteers_needed}
                        {@const isSelected = selectedTaskId === task.task_id}
                        <button
                            class="project-pill"
                            class:selected={isSelected}
                            class:fully-staffed={isFull && !isSelected}
                            onclick={() => selectTask(task.task_id)}
                        >
                            <div class="pill-header">
                                <strong>{task.short_description}</strong>
                            </div>
                            <div class="pill-meta">
                                {task.city} &middot; {formatDateShort(task.date)}
                            </div>
                            <div class="pill-meta">
                                {task.assignments.length}/{task.volunteers_needed} assigned
                            </div>
                            {#if task.assignments.length > 0}
                                <div class="pill-assigned">
                                    {#each task.assignments as a (a.assignment_id)}
                                        <span
                                            class="vol-circle small"
                                            class:skilled={a.skill_category === 'skilled'}
                                            role="button"
                                            tabindex="0"
                                            title="{a.person_name} \u2014 tap to unassign"
                                            onclick={(e: MouseEvent) => { e.stopPropagation(); unassign(task.task_id, a.assignment_id); }}
                                            onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') { e.stopPropagation(); unassign(task.task_id, a.assignment_id); } }}
                                        >{a.initials}</span>
                                    {/each}
                                </div>
                            {:else}
                                <div class="pill-assigned empty">no volunteers assigned</div>
                            {/if}
                        </button>
                    {/each}
                {/if}
            </div>
            <div class="pane volunteers-pane">
                <h3>Volunteers</h3>
                <div class="vol-grid">
                    {#each overview.volunteers as vol (vol.person_id)}
                        {@const state = volunteerState(vol)}
                        {#if state !== 'assigned-to-selected'}
                            <button
                                class="vol-circle-wrapper"
                                class:hidden-vol={state === 'hidden'}
                                class:at-limit={state === 'at-limit'}
                                disabled={state !== 'available' || !selectedTaskId}
                                title={volTooltip(vol, state)}
                                onclick={() => assign(vol.person_id)}
                            >
                                <span
                                    class="vol-circle"
                                    class:skilled={vol.skill_category === 'skilled'}
                                >{vol.initials}</span>
                                <span class="vol-count">
                                    {weekAssignmentCount(vol.person_id)}/{vol.max_tasks_per_week >= 5 ? 'Any' : vol.max_tasks_per_week}
                                </span>
                            </button>
                        {/if}
                    {/each}
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    .week-nav {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: var(--spacing-md);
        margin-bottom: var(--spacing-md);
    }
    .week-label {
        font-weight: 600;
        font-size: 1.1rem;
    }
    .status-message {
        text-align: center;
        font-style: italic;
        color: var(--rt-text-light);
        margin-bottom: var(--spacing-sm);
    }
    .assign-layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: var(--spacing-lg);
    }
    @media (max-width: 900px) {
        .assign-layout {
            grid-template-columns: 1fr;
        }
    }
    .pane h3 {
        margin-bottom: var(--spacing-sm);
        font-family: var(--font-heading);
    }
    .project-pill {
        display: block;
        width: 100%;
        text-align: left;
        background: var(--rt-white);
        border: 2px solid var(--rt-gray-200);
        border-radius: var(--card-radius);
        padding: var(--spacing-sm) var(--spacing-md);
        margin-bottom: var(--spacing-sm);
        cursor: pointer;
        transition: border-color 0.15s;
    }
    .project-pill:hover {
        border-color: var(--rt-blue);
    }
    .project-pill.selected {
        border-color: var(--rt-blue);
        background: color-mix(in srgb, var(--rt-blue) 8%, var(--rt-white));
    }
    .project-pill.fully-staffed {
        border-color: var(--rt-green);
    }
    .pill-header {
        font-size: var(--btn-font-size);
    }
    .pill-meta {
        font-size: var(--font-size-sm);
        color: var(--rt-text-light);
    }
    .pill-assigned {
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
        margin-top: var(--spacing-xs);
    }
    .pill-assigned.empty {
        font-size: var(--font-size-xs);
        color: var(--rt-text-muted);
        font-style: italic;
    }
    .vol-grid {
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-md);
        justify-content: flex-start;
    }
    .vol-circle-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: var(--spacing-xs);
        background: none;
        border: none;
        cursor: pointer;
        padding: var(--spacing-xs);
        border-radius: var(--card-radius);
        transition: opacity 0.15s;
    }
    .vol-circle-wrapper:hover:not(:disabled) {
        background: var(--rt-gray-100);
    }
    .vol-circle-wrapper:disabled {
        cursor: default;
    }
    .vol-circle-wrapper.hidden-vol {
        visibility: hidden;
    }
    .vol-circle-wrapper.at-limit {
        opacity: 0.4;
    }
    .vol-circle {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: var(--font-size-sm);
        background: var(--rt-gray-200);
        color: var(--rt-text);
        border: 3px solid var(--rt-gray-300);
    }
    .vol-circle.skilled {
        border-color: var(--rt-green);
    }
    .vol-circle.small {
        width: 32px;
        height: 32px;
        font-size: var(--font-size-xs);
        border-width: 2px;
    }
    .vol-count {
        font-size: var(--font-size-xs);
        color: var(--rt-text-muted);
    }
</style>
