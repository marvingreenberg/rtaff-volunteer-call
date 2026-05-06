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
  <div class="verify-card">
    {#if status === 'loading'}
      <div class="spinner"></div>
      <p>Verifying your login...</p>
    {:else}
      <div class="alert alert-error">
        <h1>Login Failed</h1>
        <p>{error}</p>
        <a href="/login" class="btn btn-primary mt-4">Try Again</a>
      </div>
    {/if}
  </div>
</div>

<style>
  .verify-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 80vh;
    padding: var(--spacing-md);
  }

  .verify-card {
    text-align: center;
  }

  .spinner {
    width: var(--btn-min-height);
    height: var(--btn-min-height);
    border: 4px solid var(--rt-gray-200);
    border-top: 4px solid var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto var(--spacing-md) auto;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .alert-error h1 {
    font-size: 1.5rem;
    color: #9b2c2c;
    margin-bottom: var(--spacing-md);
  }

  .mt-4 {
    margin-top: var(--spacing-lg);
    display: inline-block;
  }
</style>
