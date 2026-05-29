<script lang="ts">
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
    <div class="avatar-drawer" role="menu" aria-label="User menu">
      <!--
        Layout follows the design reference: muted email line at top,
        icon+label rows separated into groups by 1px dividers, Log out
        at the bottom. Icons are lucide-style outline SVGs at 18px,
        stroke 1.6, inheriting currentColor so they match the row text.
      -->
      {#if user.email}
        <div class="drawer-email" title={user.email}>{user.email}</div>
      {/if}

      <div class="drawer-group">
        <a href="/settings" class="drawer-row" onclick={navigate} role="menuitem">
          <svg class="row-icon" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span class="row-label">Settings</span>
        </a>

        <a href="/inbox" class="drawer-row" onclick={navigate} role="menuitem">
          <svg class="row-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M22 12h-6l-2 3h-4l-2-3H2" />
            <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
          </svg>
          <span class="row-label">Inbox</span>
          {#if unreadCount > 0}
            <span class="row-badge">{unreadCount}</span>
          {/if}
        </a>
      </div>

      {#if isStaff}
        <div class="drawer-divider"></div>
        <div class="drawer-group">
          <a href="/people" class="drawer-row" onclick={navigate} role="menuitem">
            <svg class="row-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span class="row-label">People</span>
          </a>
        </div>
      {/if}

      <div class="drawer-divider"></div>

      <button class="drawer-row drawer-logout" onclick={onlogout} role="menuitem">
        <svg class="row-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
        <span class="row-label">Log out</span>
      </button>
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
    padding: var(--spacing-sm) 0;
    min-width: 260px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    z-index: 100;
  }

  .drawer-email {
    padding: var(--spacing-sm) var(--spacing-lg, 1.25rem) var(--spacing-md);
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .drawer-group {
    display: flex;
    flex-direction: column;
  }

  .drawer-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-md, 0.75rem);
    padding: 10px var(--spacing-lg, 1.25rem);
    color: var(--rt-dark, #222);
    background: none;
    border: none;
    text-decoration: none;
    font: inherit;
    font-size: var(--btn-font-size, 0.95rem);
    cursor: pointer;
    text-align: left;
    min-height: 40px;
    width: 100%;
    transition: background-color 0.12s;
  }

  .drawer-row:hover,
  .drawer-row:focus-visible {
    background: var(--rt-gray-100, #f5f3ef);
    text-decoration: none;
    outline: none;
  }

  .row-icon {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    stroke: currentColor;
    stroke-width: 1.6;
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .row-label {
    flex: 1;
    line-height: 1.2;
  }

  .row-badge {
    background: var(--rt-error, #c0392b);
    color: white;
    font-size: var(--font-size-xs);
    font-weight: 700;
    border-radius: 10px;
    padding: 2px 8px;
    min-width: 20px;
    text-align: center;
    line-height: 1.2;
  }

  .drawer-divider {
    height: 1px;
    background: var(--rt-gray-200, #e4dfda);
    margin: var(--spacing-sm) 0;
  }

  .drawer-logout {
    color: var(--rt-dark, #222);
  }
</style>
