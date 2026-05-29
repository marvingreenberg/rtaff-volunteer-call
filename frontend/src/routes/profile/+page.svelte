<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { people, type PersonUpdate } from '$lib/api/client';
  import { authState } from '$lib/stores/auth.svelte';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { roleLabel, skillLabel } from '$lib/utils/badges';

  const ROLE_COLORS: Record<string, string> = {
    staff: '#6b5b95',
    team_leader: '#d2691e',
    volunteer: '#5aad44',
  };

  let editing = $state(false);
  let saving = $state(false);
  let saveError = $state<string | null>(null);
  let saveSuccess = $state(false);

  let editEmail = $state('');
  let editPhone = $state('');

  let user = $derived(authState.user);

  onMount(() => {
    if (!authState.user && !authState.loading) {
      goto('/login');
    }
  });

  function startEdit() {
    editEmail = user?.email ?? '';
    editPhone = user?.phone ?? '';
    saveError = null;
    saveSuccess = false;
    editing = true;
  }

  function cancelEdit() {
    editing = false;
    saveError = null;
  }

  async function save(e: Event) {
    e.preventDefault();
    if (!user) return;
    saving = true;
    saveError = null;
    saveSuccess = false;
    try {
      const updates: PersonUpdate = {
        email: editEmail || undefined,
        phone: editPhone || undefined,
      };
      const updated = await people.update(user.id, updates);
      authState.user = updated;
      editing = false;
      saveSuccess = true;
      setTimeout(() => { saveSuccess = false; }, 3000);
    } catch (e) {
      saveError = e instanceof Error ? e.message : 'Failed to save profile';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Profile - RT-AFF</title>
</svelte:head>

<Breadcrumb crumbs={[{label: 'Home', href: '/'}, {label: 'Profile'}]} />

{#if authState.loading}
  <p class="loading">Loading...</p>
{:else if !user}
  <p>Not logged in.</p>
{:else}
  <div class="page-sm">
    <PageHeader title="Profile">
      {#snippet actions()}
        {#if !editing}
          <button class="btn btn-secondary btn-sm" onclick={startEdit}>Edit</button>
        {/if}
      {/snippet}
    </PageHeader>

    <form onsubmit={save}>
      <section class="card identity-card">
        <div class="identity-row">
          <div class="profile-avatar">{user.first_name.charAt(0)}{user.last_name.charAt(0)}</div>
          <div class="identity-text">
            <div class="display-name">{user.first_name} {user.last_name}</div>
            <div class="profile-roles">
              {#each user.roles as role (role)}
                <span class="role-badge" style="background-color: {ROLE_COLORS[role] || 'var(--rt-gray-600)'}">{roleLabel(role)}</span>
              {/each}
            </div>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>Contact</h2>
        {#if editing}
          <div class="edit-fields">
            <label class="form-field" for="profile-email">
              Email
              <input id="profile-email" type="email" bind:value={editEmail} placeholder="email@example.com" />
            </label>

            <label class="form-field" for="profile-phone">
              Phone
              <input id="profile-phone" type="tel" bind:value={editPhone} placeholder="703-555-1234" />
            </label>
          </div>
        {:else}
          <div class="field">
            <span class="field-label">Email</span>
            <span class="field-value">{user.email || '—'}</span>
          </div>

          <div class="field">
            <span class="field-label">Phone</span>
            <span class="field-value">{user.phone || '—'}</span>
          </div>
        {/if}
      </section>

      <section class="card">
        <h2>Volunteering</h2>
        <div class="field">
          <span class="field-label">Skills</span>
          <span class="field-value">
            {user.skills.length ? user.skills.map(skillLabel).join(', ') : '—'}
          </span>
        </div>

        <div class="field">
          <span class="field-label">Status</span>
          <span class="field-value">{user.active ? 'Active' : 'Inactive'}</span>
        </div>
      </section>

      {#if saveError}
        <p class="save-error">{saveError}</p>
      {/if}

      {#if saveSuccess}
        <p class="save-success">Profile updated.</p>
      {/if}

      {#if editing}
        <div class="profile-actions">
          <button type="submit" class="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button type="button" class="btn btn-secondary" onclick={cancelEdit} disabled={saving}>Cancel</button>
        </div>
      {/if}
    </form>
  </div>
{/if}

<style>
  .loading {
    color: var(--rt-text-muted);
    padding: var(--sp-5);
  }

  .card + .card {
    margin-top: var(--sp-4);
  }

  .identity-row {
    display: flex;
    align-items: center;
    gap: var(--sp-4);
  }

  .profile-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--rt-blue);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    font-weight: 600;
    flex-shrink: 0;
  }

  .identity-text {
    flex: 1;
    min-width: 0;
  }

  .display-name {
    font-family: var(--font-display);
    font-size: 1.25rem;
    color: var(--rt-dark);
  }

  .profile-roles {
    display: flex;
    flex-wrap: wrap;
    gap: var(--sp-2);
    margin-top: var(--sp-2);
  }

  .role-badge {
    display: inline-block;
    padding: 2px var(--sp-3);
    color: white;
    border-radius: var(--radius-pill);
    font-size: var(--font-size-xs);
    font-weight: 600;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    margin-bottom: var(--sp-3);
  }

  .field:last-child {
    margin-bottom: 0;
  }

  .edit-fields {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
  }

  .field-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--rt-text-muted);
  }

  .field-value {
    color: var(--rt-text);
  }

  .profile-actions {
    display: flex;
    gap: var(--sp-3);
    margin-top: var(--sp-4);
  }

  .save-error {
    color: var(--rt-error);
    margin-top: var(--sp-3);
    font-size: var(--font-size-sm);
  }

  .save-success {
    color: var(--rt-success-text);
    margin-top: var(--sp-3);
    font-size: var(--font-size-sm);
  }
</style>
