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
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: 6px;
    overflow: hidden;
  }

  .toggle-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 36px;
    min-height: 36px;
    padding: var(--spacing-xs);
    border: none;
    background: var(--rt-white, white);
    cursor: pointer;
    color: var(--rt-text-muted, #777);
    transition: background 0.15s, color 0.15s;
  }

  .toggle-btn:not(:last-child) {
    border-right: 1px solid var(--rt-gray-200, #e4dfda);
  }

  .toggle-btn:hover {
    background: var(--rt-gray-100, #f5f3ef);
  }

  .toggle-btn.active {
    background: var(--color-primary, #3a6db5);
    color: var(--rt-white, white);
  }

  .toggle-btn svg {
    fill: currentColor;
  }
</style>
