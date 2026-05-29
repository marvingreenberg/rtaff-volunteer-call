<script lang="ts">
  import type { ListView } from '$lib/stores/settings.svelte';

  let {
    view,
    onchange,
  }: {
    view: ListView;
    onchange: (view: ListView) => void;
  } = $props();
</script>

<div class="view-toggle" role="group" aria-label="List view mode">
  <button
    type="button"
    class="toggle-btn"
    class:active={view === 'pill'}
    aria-label="Card view"
    aria-pressed={view === 'pill'}
    onclick={() => onchange('pill')}
  >
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="1" y="1" width="6" height="6" rx="1" />
      <rect x="9" y="1" width="6" height="6" rx="1" />
      <rect x="1" y="9" width="6" height="6" rx="1" />
      <rect x="9" y="9" width="6" height="6" rx="1" />
    </svg>
  </button>
  <button
    type="button"
    class="toggle-btn"
    class:active={view === 'table'}
    aria-label="Table view"
    aria-pressed={view === 'table'}
    onclick={() => onchange('table')}
  >
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="1" y="2" width="14" height="2" rx="0.5" />
      <rect x="1" y="7" width="14" height="2" rx="0.5" />
      <rect x="1" y="12" width="14" height="2" rx="0.5" />
    </svg>
  </button>
</div>

<style>
  .view-toggle {
    display: inline-flex;
    gap: 2px;
    background: var(--surface-2);
    padding: 3px;
    border-radius: 8px;
  }

  .toggle-btn {
    appearance: none;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 30px;
    min-height: 28px;
    padding: 5px 12px;
    border: 0;
    background: transparent;
    color: var(--rt-text-muted);
    font: inherit;
    font-size: 0.82rem;
    font-weight: 600;
    border-radius: 6px;
    cursor: pointer;
    transition:
      background 0.15s,
      color 0.15s;
  }

  .toggle-btn:hover {
    color: var(--rt-dark);
  }

  .toggle-btn.active {
    background: var(--surface-1);
    color: var(--rt-dark);
  }

  .toggle-btn svg {
    fill: currentColor;
  }
</style>
