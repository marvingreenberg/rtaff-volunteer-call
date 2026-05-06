<script lang="ts">
  import { settingsState, applySettings, type Density } from '$lib/stores/settings.svelte';
  import { notifications } from '$lib/api/client';
  import type { PersonResponse } from '$lib/api/types';

  let { user, onlogout }: { user: PersonResponse; onlogout: () => void } = $props();

  let open = $state(false);
  let unreadCount = $state(0);

  async function loadUnreadCount() {
    try {
      const result = await notifications.unreadCount();
      unreadCount = result.count;
    } catch {
      // silently ignore
    }
  }

  $effect(() => {
    loadUnreadCount();
  });

  let initials = $derived(
    (user.first_name?.[0] ?? '') + (user.last_name?.[0] ?? '')
  );

  let roles = $derived(user.roles ?? []);
  let isStaff = $derived(roles.includes('staff'));
  let isStaffOrLead = $derived(roles.includes('staff') || roles.includes('team_leader'));

  function setDensity(d: Density) {
    settingsState.density = d;
    applySettings();
  }

  function toggleTheme() {
    settingsState.theme = settingsState.theme === 'light' ? 'dark' : 'light';
    applySettings();
  }

  function handleClickOutside(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest('.avatar-menu-wrapper')) open = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') open = false;
  }

  function navigate() {
    open = false;
  }

  const densityOptions: { value: Density; label: string }[] = [
    { value: 'large', label: 'Large' },
    { value: 'standard', label: 'Standard' },
    { value: 'compact', label: 'Compact' },
  ];

  const ROLE_LABELS: Record<string, string> = {
    staff: 'Staff',
    team_leader: 'Team Leader',
    volunteer: 'Volunteer',
  };
</script>

<svelte:document onclick={handleClickOutside} onkeydown={handleKeydown} />

<div class="avatar-menu-wrapper">
  <button class="avatar-btn" onclick={() => (open = !open)} aria-label="User menu">
    {initials}
    {#if unreadCount > 0}
      <span class="notification-badge">{unreadCount}</span>
    {/if}
  </button>

  {#if open}
    <div class="avatar-drawer" role="dialog" aria-label="User menu">
      <div class="drawer-user">
        <div class="drawer-name">{user.first_name} {user.last_name}</div>
        <div class="drawer-roles">
          {#each roles as role (role)}
            <span class="role-badge">{ROLE_LABELS[role] ?? role}</span>
          {/each}
        </div>
      </div>

      {#if isStaff || isStaffOrLead}
        <div class="drawer-divider"></div>
        <nav class="drawer-nav">
          {#if isStaff}
            <a href="/people" class="drawer-link" onclick={navigate}>People</a>
          {/if}
          {#if isStaffOrLead}
            <a href="/inventory" class="drawer-link" onclick={navigate}>Inventory</a>
          {/if}
        </nav>
      {/if}

      <div class="drawer-divider"></div>
      <nav class="drawer-nav">
        <a href="/inbox" class="drawer-link" onclick={navigate}>
          Inbox{unreadCount > 0 ? ` (${unreadCount})` : ''}
        </a>
      </nav>

      <div class="drawer-divider"></div>

      <div class="drawer-settings">
        <span class="settings-label">Display</span>
        <div class="density-options" role="radiogroup" aria-label="Display density">
          {#each densityOptions as opt (opt.value)}
            <label class="density-option" class:selected={settingsState.density === opt.value}>
              <input
                type="radio"
                name="density"
                value={opt.value}
                checked={settingsState.density === opt.value}
                onchange={() => setDensity(opt.value)}
              />
              {opt.label}
            </label>
          {/each}
        </div>

        <label class="theme-toggle">
          <input
            type="checkbox"
            aria-label="Dark mode"
            checked={settingsState.theme === 'dark'}
            onchange={toggleTheme}
          />
          <span>Dark mode</span>
        </label>
      </div>

      <div class="drawer-divider"></div>

      <button class="drawer-logout" onclick={onlogout}>Logout</button>
    </div>
  {/if}
</div>

<style>
  .avatar-menu-wrapper {
    position: relative;
  }

  .avatar-btn {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: none;
    background: var(--color-primary, #3a6db5);
    color: white;
    font-size: var(--font-size-sm);
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .notification-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    background: var(--rt-error);
    color: white;
    font-size: var(--font-size-xs);
    font-weight: 700;
    min-width: 18px;
    height: 18px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 4px;
    line-height: 1;
  }

  .avatar-btn:hover {
    opacity: 0.85;
  }

  .avatar-drawer {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    background: var(--rt-white, white);
    border: 1px solid var(--rt-gray-200);
    border-radius: var(--card-radius);
    padding: var(--spacing-md);
    min-width: 240px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    z-index: 100;
  }

  .drawer-user {
    margin-bottom: var(--spacing-xs);
  }

  .drawer-name {
    font-weight: 600;
    font-size: var(--btn-font-size);
    color: var(--rt-dark, #333);
  }

  .drawer-roles {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
    margin-top: var(--spacing-xs);
  }

  .role-badge {
    display: inline-block;
    padding: 2px var(--spacing-sm);
    background: var(--rt-gray-200, #e5e5e5);
    color: var(--rt-dark, #333);
    border-radius: 10px;
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .drawer-divider {
    height: 1px;
    background: var(--rt-gray-200, #e5e5e5);
    margin: var(--spacing-md) 0;
  }

  .drawer-nav {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .drawer-link {
    display: block;
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: var(--btn-min-height);
    display: flex;
    align-items: center;
    border-radius: var(--card-radius);
    text-decoration: none;
    color: var(--rt-dark, #333);
    font-weight: 500;
    font-size: var(--font-size-sm);
    transition: background-color 0.15s;
  }

  .drawer-link:hover {
    background: var(--rt-gray-100, #f5f5f5);
    text-decoration: none;
  }

  .drawer-settings {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .settings-label {
    display: block;
    font-size: var(--font-size-xs);
    font-weight: 600;
    color: var(--rt-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .density-options {
    display: flex;
    border: 1px solid var(--rt-gray-200);
    border-radius: var(--card-radius);
    overflow: hidden;
  }

  .density-option {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: var(--btn-min-height);
    padding: var(--spacing-sm);
    font-size: var(--font-size-sm);
    font-weight: 500;
    cursor: pointer;
    border-right: 1px solid var(--rt-gray-200);
    background: transparent;
    color: var(--rt-text);
    transition: background-color 0.15s;
  }

  .density-option:last-child {
    border-right: none;
  }

  .density-option:hover {
    background: var(--rt-gray-100);
  }

  .density-option.selected {
    background: var(--rt-blue);
    color: white;
  }

  .density-option input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
  }

  .theme-toggle {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    min-height: var(--btn-min-height);
    cursor: pointer;
    font-size: var(--font-size-sm);
    color: var(--rt-text);
  }

  .theme-toggle input {
    width: 18px;
    height: 18px;
    cursor: pointer;
  }

  .drawer-logout {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: var(--btn-min-height);
    border: 1px solid var(--rt-gray-200, #e5e5e5);
    border-radius: var(--card-radius);
    background: transparent;
    color: var(--rt-text-light, #666);
    font-size: var(--font-size-sm);
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
  }

  .drawer-logout:hover {
    background: var(--rt-gray-100, #f5f5f5);
    color: var(--rt-orange, #d35400);
  }
</style>
