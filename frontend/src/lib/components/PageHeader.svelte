<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    meta,
  }: {
    title: string;
    meta?: Snippet;
  } = $props();
</script>

<header class="page-header">
  <div class="title-row">
    <span class="accent" aria-hidden="true"></span>
    <h1>{title}</h1>
  </div>
  {#if meta}
    <div class="page-header-meta">{@render meta()}</div>
  {/if}
</header>

<style>
  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: var(--sp-4);
    margin-bottom: var(--sp-5);
  }
  .title-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }
  .accent {
    display: inline-block;
    width: 22px;
    height: 4px;
    border-radius: 2px;
    background: var(--rt-green);
    margin-bottom: 6px;
  }
  h1 {
    margin: 0;
    font-size: var(--fz-h1);
  }
  .page-header-meta {
    color: var(--rt-text-muted);
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
  }
</style>
