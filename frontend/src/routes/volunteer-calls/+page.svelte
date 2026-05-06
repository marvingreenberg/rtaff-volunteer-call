<script lang="ts">
  import { onMount } from 'svelte';
  import { volunteerCalls, type VolunteerCallListResponse, type VolunteerCallCreate } from '$lib/api/client';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import { callStatusBadgeClass } from '$lib/utils/badges';
  import { formatDate } from '$lib/utils/format';

  let calls: VolunteerCallListResponse[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let showAddForm = $state(false);
  let saving = $state(false);
  let statusFilter = $state('');

  let newCall: VolunteerCallCreate = $state({ title: '' });

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
      await volunteerCalls.create(newCall);
      newCall = { title: '' };
      showAddForm = false;
      await loadCalls();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create call';
    } finally {
      saving = false;
    }
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
        <div class="form-row">
          <label class="form-field">
            Title *
            <input type="text" bind:value={newCall.title} required placeholder="e.g., Spring NRD 2026" />
          </label>
        </div>
        <div class="form-row">
          <label class="form-field">
            Notes
            <textarea bind:value={newCall.notes} placeholder="Optional notes about this call"></textarea>
          </label>
        </div>
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
