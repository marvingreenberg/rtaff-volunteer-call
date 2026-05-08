<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { people, type PersonResponse, type PersonUpdate } from '$lib/api/client';
  import { authState } from '$lib/stores/auth.svelte';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
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

  async function save() {
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
  <div class="profile-card card">
    <div class="profile-header">
      <div class="profile-name-row">
        <div class="profile-avatar">{user.first_name.charAt(0)}{user.last_name.charAt(0)}</div>
        <div class="profile-name">
          <h1>{user.first_name} {user.last_name}</h1>
          <div class="profile-roles">
            {#each user.roles as role (role)}
              <span class="role-badge" style="background-color: {ROLE_COLORS[role] || 'var(--rt-gray-600)'}">{roleLabel(role)}</span>
            {/each}
          </div>
        </div>
        {#if !editing}
          <button class="edit-btn" onclick={startEdit} aria-label="Edit profile">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
          </button>
        {/if}
      </div>
    </div>

    <div class="profile-fields">
      <div class="field">
        <label for="profile-email">Email</label>
        {#if editing}
          <input id="profile-email" type="email" bind:value={editEmail} class="field-input" placeholder="email@example.com" />
        {:else}
          <span id="profile-email" class="field-value">{user.email || '---'}</span>
        {/if}
      </div>

      <div class="field">
        <label for="profile-phone">Phone</label>
        {#if editing}
          <input id="profile-phone" type="tel" bind:value={editPhone} class="field-input" placeholder="703-555-1234" />
        {:else}
          <span id="profile-phone" class="field-value">{user.phone || '---'}</span>
        {/if}
      </div>

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
    </div>

    {#if saveError}
      <p class="save-error">{saveError}</p>
    {/if}

    {#if saveSuccess}
      <p class="save-success">Profile updated.</p>
    {/if}

    {#if editing}
      <div class="profile-actions">
        <button class="btn btn-primary" onclick={save} disabled={saving}>
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button class="btn btn-secondary" onclick={cancelEdit} disabled={saving}>Cancel</button>
      </div>
    {/if}
  </div>
{/if}

<style>
  .loading {
    color: var(--rt-text-muted);
    padding: var(--spacing-xl);
  }

  .profile-card {
    max-width: 600px;
    margin: 0 auto;
  }

  .profile-header {
    margin-bottom: var(--spacing-lg);
  }

  .profile-name-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .profile-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--color-primary, #3a6db5);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--btn-font-size);
    font-weight: 600;
    flex-shrink: 0;
  }

  .profile-name {
    flex: 1;
  }

  .profile-name h1 {
    margin: 0;
    font-size: 1.5rem;
    line-height: 1.2;
  }

  .profile-roles {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
    margin-top: var(--spacing-xs);
  }

  .role-badge {
    display: inline-block;
    padding: 2px var(--spacing-sm);
    color: white;
    border-radius: var(--spacing-xs);
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .edit-btn {
    background: transparent;
    border: 1px solid var(--rt-gray-300, #ccc);
    border-radius: var(--spacing-xs);
    padding: var(--spacing-sm);
    cursor: pointer;
    color: var(--rt-text-light, #666);
    min-width: var(--btn-min-height);
    min-height: var(--btn-min-height);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .edit-btn:hover {
    background: var(--rt-gray-100, #f5f5f5);
    color: var(--color-primary, #3a6db5);
  }

  .profile-fields {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .field label,
  .field-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--rt-text-muted, #777);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .field-value {
    font-size: var(--btn-font-size);
    color: var(--rt-dark, #333);
  }

  .field-input {
    font-size: var(--btn-font-size);
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--rt-gray-300, #ccc);
    border-radius: var(--spacing-xs);
    min-height: var(--btn-min-height);
    width: 100%;
    box-sizing: border-box;
  }

  .field-input:focus {
    outline: none;
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.15);
  }

  .profile-actions {
    display: flex;
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
  }

  .profile-actions .btn {
    min-height: var(--btn-min-height);
    padding: var(--spacing-sm) var(--spacing-lg);
    border-radius: var(--spacing-xs);
    font-size: var(--btn-font-size);
    font-weight: 500;
    cursor: pointer;
    border: none;
  }

  .btn-primary {
    background: var(--color-primary, #3a6db5);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: var(--rt-gray-200, #e5e5e5);
    color: var(--rt-dark, #333);
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--rt-gray-300, #ccc);
  }

  .save-error {
    color: var(--color-danger, #d32f2f);
    margin-top: var(--spacing-md);
    font-size: var(--font-size-sm);
  }

  .save-success {
    color: var(--color-success, #388e3c);
    margin-top: var(--spacing-md);
    font-size: var(--font-size-sm);
  }
</style>
