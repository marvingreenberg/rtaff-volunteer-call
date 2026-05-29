<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { verify } from '$lib/stores/auth.svelte';

  let status = $state<'loading' | 'error'>('loading');
  let error = $state('');

  onMount(async () => {
    const token = page.url.searchParams.get('token');
    if (!token) {
      status = 'error';
      error = 'No login token found in URL.';
      return;
    }

    try {
      await verify(token);
      // Redirect to home or saved return path
      const redirectTo = page.url.searchParams.get('returnTo') || '/';
      goto(redirectTo);
    } catch (e) {
      status = 'error';
      error = e instanceof Error ? e.message : 'Invalid or expired login link.';
    }
  });
</script>

<div class="verify-container">
  <div class="card verify-card">
    {#if status === 'loading'}
      <div class="spinner"></div>
      <p>Verifying your login...</p>
    {:else}
      <h1>Login Failed</h1>
      <p class="error-msg">{error}</p>
      <a href="/login" class="btn btn-primary">Try Again</a>
    {/if}
  </div>
</div>

<style>
  .verify-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 80vh;
    padding: var(--sp-4);
  }

  .verify-card {
    text-align: center;
    max-width: 400px;
    width: 100%;
    padding: var(--sp-6);
  }

  .spinner {
    width: var(--btn-h);
    height: var(--btn-h);
    border: 4px solid var(--surface-3);
    border-top: 4px solid var(--rt-blue);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto var(--sp-4) auto;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  h1 {
    font-size: 1.5rem;
    color: var(--rt-error);
    margin: 0 0 var(--sp-3) 0;
  }

  .error-msg {
    color: var(--rt-text-muted);
    margin: 0 0 var(--sp-5) 0;
  }
</style>
