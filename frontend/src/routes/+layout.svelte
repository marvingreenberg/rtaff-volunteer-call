<script lang="ts">
  import "../app.css";
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import type { Snippet } from 'svelte';
  import { loadSettings } from '$lib/stores/settings.svelte';
  import { authState, initFromToken, logout } from '$lib/stores/auth.svelte';
  import AvatarMenu from '$lib/components/AvatarMenu.svelte';

  let { children }: { children: Snippet } = $props();

  // Cloud Run warmth heartbeat. While the user is authenticated, ping
  // /warm every 4 minutes — well under Cloud Run's ~15-minute idle
  // eviction so the container they're already using doesn't cold-start
  // mid-session. Off the auth pages because there's no value in keeping
  // an idle browser tab warming the backend.
  const HEARTBEAT_MS = 4 * 60 * 1000;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  function startHeartbeat() {
    if (heartbeatTimer !== null) return;
    heartbeatTimer = setInterval(() => {
      // Fire-and-forget; a failed warm ping isn't worth surfacing.
      fetch('/warm', { credentials: 'include' }).catch(() => {});
    }, HEARTBEAT_MS);
  }

  function stopHeartbeat() {
    if (heartbeatTimer !== null) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  $effect(() => {
    if (authState.user && !isAuthPage) startHeartbeat();
    else stopHeartbeat();
  });

  onDestroy(() => stopHeartbeat());

  onMount(async () => {
    loadSettings();
    await initFromToken(page.url.searchParams.get('token'));
    if (authState.user) {
      if (isAuthPage || currentPath === '/verify') {
        const roles = authState.user.roles;
        const isVolunteerOnly = roles.length === 1 && roles[0] === 'volunteer';
        goto(isVolunteerOnly ? '/volunteering' : '/volunteer-calls');
      }
    } else if (!isPublicPage) {
      goto('/login');
    }
  });

  let currentPath = $derived(page.url.pathname);
  let isAuthPage = $derived(currentPath === '/login' || currentPath === '/verify');
  let isPublicPage = $derived(isAuthPage);
  let isAuthenticated = $derived(!!authState.user);
  let showNav = $derived(isAuthenticated && !isAuthPage);

  function isActive(href: string): boolean {
    if (href === '/') return currentPath === '/';
    return currentPath.startsWith(href);
  }

  async function handleLogout() {
    await logout();
    goto('/login');
  }

  const allNavItems = [
    { href: '/volunteer-calls', label: 'Calls', icon: '\u{1F4E2}', minRole: 'team_leader' },
    { href: '/volunteering', label: 'Volunteering', icon: '\u{1F91D}', minRole: 'volunteer' },
    { href: '/people', label: 'People', icon: '\u{1F464}', minRole: 'staff' },
  ];

  function userCanSee(minRole: string, roles: string[]): boolean {
    if (minRole === 'volunteer') return true;
    if (minRole === 'team_leader') return roles.includes('staff') || roles.includes('team_leader');
    if (minRole === 'staff') return roles.includes('staff');
    return false;
  }

  let visibleNavItems = $derived(
    authState.user
      ? allNavItems.filter(item => userCanSee(item.minRole, authState.user!.roles))
      : []
  );
</script>

<div class="app">
  <header>
    <a href="/" class="logo">
      <img src="/images/rt-aff-logo.png" alt="Rebuilding Together Arlington/Fairfax/Falls Church" />
    </a>

    {#if showNav}
      <nav>
        {#each visibleNavItems as item (item.href)}
          <a href={item.href} class:active={isActive(item.href)} title={item.label}>
            <span class="nav-icon" aria-hidden="true">{item.icon}</span>
            <span class="nav-label">{item.label}</span>
          </a>
        {/each}
      </nav>
    {/if}

    <div class="user-auth">
      {#if authState.loading}
        <span class="auth-loading">Checking auth...</span>
      {:else if authState.user}
        <AvatarMenu user={authState.user} onlogout={handleLogout} />
      {:else if !isAuthPage}
        <a href="/login" class="login-link">Login</a>
      {/if}
    </div>
  </header>

  <main>
    {@render children?.()}
  </main>
</div>

<style>
  .user-auth {
    flex: 0 0 auto;
    margin-left: auto;
    display: flex;
    align-items: center;
  }

  .auth-loading {
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
  }

  .login-link {
    font-weight: 500;
    color: var(--color-primary);
    text-decoration: none;
    font-size: var(--font-size-sm);
  }

  .login-link:hover {
    text-decoration: underline;
  }
</style>
