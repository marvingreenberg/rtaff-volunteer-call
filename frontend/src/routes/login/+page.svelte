<script lang="ts">
  import { goto } from '$app/navigation';
  import { login } from '$lib/stores/auth.svelte';

  let email = $state('');
  let status = $state<'idle' | 'loading' | 'success' | 'error'>('idle');
  let message = $state('');
  let error = $state('');

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (!email) return;

    status = 'loading';
    error = '';
    try {
      const result = await login(email);
      if (result.demoToken) {
        // DEMO_MODE: backend returned the access token directly. Skip the
        // "check your email" step and go straight to verify.
        await goto(`/verify?token=${encodeURIComponent(result.demoToken)}`);
        return;
      }
      message = result.message;
      status = 'success';
    } catch (e) {
      status = 'error';
      error = e instanceof Error ? e.message : 'An error occurred';
    }
  }
</script>

<svelte:head>
  <title>Login - RT-AFF</title>
</svelte:head>

<div class="login-container">
  <div class="login-card">
    <div class="logo-wrap">
      <img src="/images/rt-aff-logo.png" alt="RT-AFF Logo" class="logo" />
    </div>

    <h1>Login</h1>
    <p class="subtitle">Enter your email to receive a login link.</p>

    {#if status === 'success'}
      <div class="alert alert-success">
        {message}
      </div>
      <p class="hint">Check your email (or the backend console in dev mode) for the link.</p>
    {:else}
      <form onsubmit={handleSubmit}>
        <div class="form-group">
          <label for="email">Email Address</label>
          <input
            type="email"
            id="email"
            bind:value={email}
            placeholder="you@example.com"
            required
            disabled={status === 'loading'}
          />
        </div>

        {#if status === 'error'}
          <div class="alert alert-error">
            {error}
          </div>
        {/if}

        <button type="submit" class="btn btn-primary btn-block" disabled={status === 'loading'}>
          {status === 'loading' ? 'Sending...' : 'Send Login Link'}
        </button>
      </form>
    {/if}
  </div>
</div>

<style>
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 80vh;
    padding: var(--spacing-md);
  }

  .login-card {
    background: var(--rt-white);
    padding: var(--spacing-xl);
    border-radius: var(--card-radius);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    width: 100%;
    max-width: 400px;
    text-align: center;
  }

  .logo-wrap {
    margin-bottom: var(--spacing-lg);
  }

  .logo {
    height: 60px;
    width: auto;
  }

  h1 {
    margin: 0 0 var(--spacing-sm) 0;
    font-size: 1.75rem;
    color: var(--rt-dark);
  }

  .subtitle {
    color: var(--rt-text-light);
    margin-bottom: var(--spacing-xl);
  }

  .form-group {
    text-align: left;
    margin-bottom: var(--spacing-lg);
  }

  label {
    display: block;
    margin-bottom: var(--spacing-sm);
    font-weight: 500;
    font-size: var(--font-size-sm);
  }

  input {
    width: 100%;
    padding: var(--spacing-md);
    border: 1px solid var(--rt-gray-200);
    border-radius: var(--card-radius);
    font-size: var(--btn-font-size);
    transition: border-color 0.2s;
  }

  input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .btn-block {
    width: 100%;
    padding: var(--spacing-md);
    font-size: var(--btn-font-size);
  }

  .alert {
    padding: var(--spacing-md);
    border-radius: var(--card-radius);
    margin-bottom: var(--spacing-lg);
    font-size: var(--font-size-sm);
    text-align: left;
  }

  .alert-success {
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
    border: 1px solid var(--rt-success);
  }

  .alert-error {
    background: var(--rt-error-bg);
    color: var(--rt-error-text);
    border: 1px solid var(--rt-error);
  }

  .hint {
    margin-top: var(--spacing-lg);
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
  }
</style>
