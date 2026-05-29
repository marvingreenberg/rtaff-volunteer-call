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
  <div class="card login-card">
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
        <label class="form-field" for="email">
          Email Address
          <input
            type="email"
            id="email"
            bind:value={email}
            placeholder="you@example.com"
            required
            disabled={status === 'loading'}
          />
        </label>

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
    padding: var(--sp-4);
  }

  .login-card {
    width: 100%;
    max-width: 400px;
    text-align: center;
    padding: var(--sp-6);
  }

  .logo-wrap {
    margin-bottom: var(--sp-5);
  }

  .logo {
    height: 60px;
    width: auto;
  }

  h1 {
    margin: 0 0 var(--sp-3) 0;
    font-size: 1.75rem;
    color: var(--rt-dark);
  }

  .subtitle {
    color: var(--rt-text-muted);
    margin-bottom: var(--sp-5);
  }

  .form-field {
    text-align: left;
    margin-bottom: var(--sp-5);
  }

  .btn-block {
    width: 100%;
  }

  .alert {
    padding: var(--sp-3) var(--sp-4);
    border-radius: var(--radius-sm);
    margin-bottom: var(--sp-4);
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
    margin-top: var(--sp-4);
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
  }
</style>
