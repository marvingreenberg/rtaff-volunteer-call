<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    href,
    accentColor,
    checked = false,
    children,
  }: {
    href?: string;
    accentColor?: string;
    checked?: boolean;
    children: Snippet;
  } = $props();
</script>

{#if href}
  <a {href} class="item-card" class:checked class:accented={!!accentColor}
    style:border-left-color={accentColor}>
    {@render children()}
  </a>
{:else}
  <div class="item-card" class:checked class:accented={!!accentColor}
    style:border-left-color={accentColor}>
    {@render children()}
  </div>
{/if}

<style>
  .item-card {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    padding: var(--card-padding-y);
    background: var(--rt-white);
    border: 1px solid var(--rt-gray-200);
    border-radius: var(--card-radius);
    text-decoration: none;
    color: inherit;
    transition: box-shadow 0.15s, border-color 0.15s, background 0.15s;
  }

  a.item-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    text-decoration: none;
  }

  .item-card.accented {
    border-left: 4px solid var(--rt-gray-300);
  }

  .item-card.checked {
    border-color: var(--rt-green);
    background: var(--rt-checked-bg);
  }
</style>
