<script lang="ts">
  import { onMount } from 'svelte';
  import { people, type PersonListResponse, type Skill, type RoleType } from '$lib/api/client';
  import { ALL_SKILLS } from '$lib/api/types';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import Select from '$lib/components/Select.svelte';
  import { roleLabel, skillLabel } from '$lib/utils/badges';

  let personList: PersonListResponse[] = $state([]);
  let total = $state(0);
  let pageStart = $state(0);
  const PAGE_SIZE = 25;
  let loading = $state(true);
  let error: string | null = $state(null);

  let searchQuery = $state('');
  let roleFilter = $state('');
  let showAddForm = $state(false);

  let newFirstName = $state('');
  let newLastName = $state('');
  let newEmail = $state('');
  let newPhone = $state('');
  let newSkills: Skill[] = $state([]);
  let newRoles: RoleType[] = $state([]);
  let saving = $state(false);

  const ROLES: { value: RoleType; label: string }[] = [
    { value: 'staff', label: 'Staff' },
    { value: 'team_leader', label: 'Team Leader' },
    { value: 'volunteer', label: 'Volunteer' },
  ];

  const ROLE_COLORS: Record<string, string> = {
    staff: '#6b5b95',
    team_leader: '#d2691e',
    volunteer: '#5aad44',
  };

  // Label for the count in the header. One count per query — the
  // filter dictates the noun. Singular when total === 1.
  let headerLabel = $derived.by(() => {
    const n = total;
    const plural = (s: string) => (n === 1 ? s : `${s}s`);
    if (!roleFilter) return plural('person').replace('persons', 'people');
    if (roleFilter === 'staff') return plural('staff member');
    if (roleFilter === 'team_leader') return plural('team leader');
    if (roleFilter === 'volunteer') return plural('volunteer');
    return plural('person').replace('persons', 'people');
  });

  let pageEnd = $derived(Math.min(pageStart + personList.length, total));
  let canPrev = $derived(pageStart > 0);
  let canNext = $derived(pageStart + personList.length < total);

  onMount(() => loadPeople());

  async function loadPeople() {
    loading = true;
    error = null;
    try {
      const resp = await people.list({
        search: searchQuery || undefined,
        role: roleFilter || undefined,
        start: pageStart,
        count: PAGE_SIZE,
      });
      personList = resp.items;
      total = resp.total;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load people';
    } finally {
      loading = false;
    }
  }

  function handleSearch() {
    // Resetting to start=0 keeps the user from getting stuck on an
    // out-of-range page when the filter narrows results.
    pageStart = 0;
    loadPeople();
  }

  function nextPage() {
    if (!canNext) return;
    pageStart += PAGE_SIZE;
    loadPeople();
  }

  function prevPage() {
    if (!canPrev) return;
    pageStart = Math.max(0, pageStart - PAGE_SIZE);
    loadPeople();
  }

  function toggleRole(role: RoleType) {
    if (newRoles.includes(role)) {
      newRoles = newRoles.filter(r => r !== role);
    } else {
      newRoles = [...newRoles, role];
    }
  }

  function toggleSkill(skill: Skill) {
    if (newSkills.includes(skill)) {
      newSkills = newSkills.filter(s => s !== skill);
    } else {
      newSkills = [...newSkills, skill];
    }
  }

  async function handleAdd() {
    if (!newFirstName.trim() || !newLastName.trim()) return;
    saving = true;
    error = null;
    try {
      await people.create({
        first_name: newFirstName.trim(),
        last_name: newLastName.trim(),
        email: newEmail.trim() || undefined,
        phone: newPhone.trim() || undefined,
        skills: newSkills,
        roles: newRoles,
      });
      newFirstName = '';
      newLastName = '';
      newEmail = '';
      newPhone = '';
      newSkills = [];
      newRoles = [];
      showAddForm = false;
      await loadPeople();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create person';
    } finally {
      saving = false;
    }
  }

  function getInitials(first: string, last: string): string {
    return (first.charAt(0) + last.charAt(0)).toUpperCase();
  }

  function getInitialColor(name: string): string {
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    const colors = ['#5aad44', '#3a6db5', '#d2691e', '#6b5b95', '#2e86ab', '#c0784b'];
    return colors[Math.abs(hash) % colors.length];
  }
</script>

<svelte:head>
  <title>People - RT-AFF</title>
</svelte:head>

<div class="people-page page-md">
  <Breadcrumb crumbs={[{label: 'People'}]} />
  <PageHeader title="People">
    {#snippet meta()}
      {#if !loading}
        <span class="header-count">{total} {headerLabel}</span>
      {/if}
    {/snippet}
    {#snippet actions()}
      <button class="btn btn-primary btn-sm" onclick={() => showAddForm = !showAddForm}>
        {showAddForm ? 'Cancel' : '+ Add Person'}
      </button>
    {/snippet}
  </PageHeader>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if showAddForm}
    <section class="card add-form">
      <h2>Add Person</h2>
      <form onsubmit={(e) => { e.preventDefault(); handleAdd(); }}>
        <div class="form-row">
          <div class="form-field">
            <label for="first-name">First Name</label>
            <input id="first-name" type="text" bind:value={newFirstName} required />
          </div>
          <div class="form-field">
            <label for="last-name">Last Name</label>
            <input id="last-name" type="text" bind:value={newLastName} required />
          </div>
        </div>
        <div class="form-row">
          <div class="form-field">
            <label for="email">Email</label>
            <input id="email" type="email" bind:value={newEmail} />
          </div>
          <div class="form-field">
            <label for="phone">Phone</label>
            <input id="phone" type="text" bind:value={newPhone} />
          </div>
        </div>
        <div class="form-field">
          <span class="field-label">Skills</span>
          <div class="role-checkboxes">
            {#each ALL_SKILLS as skill (skill)}
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  checked={newSkills.includes(skill)}
                  onchange={() => toggleSkill(skill)}
                />
                {skillLabel(skill)}
              </label>
            {/each}
          </div>
        </div>
        <div class="form-field">
          <span class="field-label">Roles</span>
          <div class="role-checkboxes">
            {#each ROLES as role (role.value)}
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  checked={newRoles.includes(role.value)}
                  onchange={() => toggleRole(role.value)}
                />
                {role.label}
              </label>
            {/each}
          </div>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </section>
  {/if}

  <div class="filters">
    <input
      type="text"
      placeholder="Search by name..."
      bind:value={searchQuery}
      oninput={handleSearch}
      class="search-input"
    />
    <Select
      bind:value={roleFilter}
      options={[
        { value: '', label: 'All Roles' },
        ...ROLES.map((r) => ({ value: r.value, label: r.label })),
      ]}
      ariaLabel="Role filter"
      onchange={handleSearch}
    />
  </div>

  {#if loading}
    <p class="loading">Loading people...</p>
  {:else if personList.length === 0}
    <p class="empty">No people found.</p>
  {:else}
    <ul class="hairline-list people-list">
      {#each personList as person (person.id)}
        <li>
          <a href="/people/{person.id}" class="person-row">
            <span class="avatar" style="background-color: {getInitialColor(person.last_name)}">
              {getInitials(person.first_name, person.last_name)}
            </span>
            <span class="person-name">{person.first_name} {person.last_name}</span>
            <span class="person-skill">{person.skills.length ? person.skills.map(skillLabel).join(', ') : '—'}</span>
            <span class="person-roles">
              {#each person.roles as role (role)}
                <span class="role-badge" style="background-color: {ROLE_COLORS[role] || 'var(--rt-gray-600)'}">{roleLabel(role)}</span>
              {/each}
            </span>
            <span class="person-status">
              <span class="badge" class:badge-active={person.active} class:badge-inactive={!person.active}>
                {person.active ? 'Active' : 'Inactive'}
              </span>
            </span>
          </a>
        </li>
      {/each}
    </ul>

    {#if total > PAGE_SIZE}
      <div class="pagination">
        <span class="page-range">
          Showing {pageStart + 1}–{pageEnd} of {total}
        </span>
        <div class="page-buttons">
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            onclick={prevPage}
            disabled={!canPrev}
          >
            ← Previous
          </button>
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            onclick={nextPage}
            disabled={!canNext}
          >
            Next →
          </button>
        </div>
      </div>
    {/if}
  {/if}

</div>

<style>
  .pagination {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: var(--sp-4);
    padding-top: var(--sp-4);
    border-top: 1px solid var(--hairline);
    font-size: var(--font-size-sm);
  }

  .page-range {
    color: var(--rt-text-muted);
  }

  .page-buttons {
    display: flex;
    gap: var(--sp-3);
  }

  .add-form {
    margin-bottom: var(--sp-5);
  }

  .add-form h2 {
    margin-top: 0;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--sp-4);
    margin-bottom: var(--sp-4);
  }

  .role-checkboxes {
    display: flex;
    gap: var(--sp-4);
    flex-wrap: wrap;
    margin-top: var(--sp-2);
  }

  .field-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--rt-text-muted);
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--sp-2);
    font-weight: normal;
    cursor: pointer;
    min-height: var(--btn-h);
    color: var(--rt-text);
  }

  .checkbox-label input[type="checkbox"] {
    width: 18px;
    height: 18px;
  }

  .form-actions {
    margin-top: var(--sp-4);
    display: flex;
    justify-content: flex-end;
  }

  .filters {
    display: flex;
    gap: var(--sp-4);
    margin-bottom: var(--sp-4);
  }

  .search-input {
    flex: 1;
    padding: 0 var(--sp-4);
    min-height: var(--btn-h);
    border: 1px solid var(--rt-input-border);
    border-radius: var(--radius-sm);
    background: var(--rt-input-bg);
    color: var(--rt-text);
    font-size: var(--fz-body);
    font-family: var(--font-body);
  }

  .search-input:focus {
    outline: none;
    border-color: var(--rt-blue);
    box-shadow: var(--ring-focus);
  }

  /* Row layout for the people list. Hairline-divider container and row
     separators come from the global .hairline-list utility. */
  .person-row {
    display: flex;
    align-items: center;
    gap: var(--sp-4);
    padding: var(--sp-3) var(--card-pad-x);
    min-height: var(--btn-h);
    text-decoration: none;
    color: inherit;
    transition: background-color 0.1s;
  }

  .person-row:hover {
    background: var(--surface-2);
    text-decoration: none;
  }

  .person-row:active {
    background: var(--surface-3);
  }

  .avatar {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    color: white;
    font-size: var(--font-size-sm);
    font-weight: 600;
    flex-shrink: 0;
  }

  .person-name {
    font-weight: 500;
    color: var(--rt-blue);
    min-width: 140px;
  }

  .person-skill {
    color: var(--rt-text-muted);
    font-size: var(--font-size-sm);
    min-width: 80px;
  }

  .person-roles {
    flex: 1;
    display: flex;
    gap: var(--sp-2);
    flex-wrap: wrap;
  }

  .role-badge {
    display: inline-block;
    padding: 2px var(--sp-3);
    color: white;
    border-radius: 10px;
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .badge-active {
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
  }

  .badge-inactive {
    background: var(--rt-gray-200);
    color: var(--rt-text-muted);
  }

  @media (max-width: 768px) {
    .person-row {
      flex-wrap: wrap;
    }

    .person-skill {
      display: none;
    }

    .form-row {
      grid-template-columns: 1fr;
    }

    .filters {
      flex-direction: column;
    }
  }
</style>
