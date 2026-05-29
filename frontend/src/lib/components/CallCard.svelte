<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    meta,
    controls,
    body,
    footer,
  }: {
    title: string;
    meta?: string;
    controls?: Snippet;
    body: Snippet;
    footer?: Snippet;
  } = $props();
</script>

<article class="call">
  <header class="call-head">
    <span class="call-title">{title}</span>
    {#if meta}<span class="call-meta">{meta}</span>{/if}
  </header>
  {#if controls}
    <div class="call-controls">{@render controls()}</div>
  {/if}
  <div class="call-body">{@render body()}</div>
  {#if footer}
    <div class="call-footer">{@render footer()}</div>
  {/if}
</article>

<style>
  .call {
    background: var(--surface-1);
    border-radius: var(--radius);
    border: 1px solid var(--hairline);
    box-shadow: 0 2px 12px -8px rgba(30, 47, 61, 0.15);
    overflow: hidden;
    margin-bottom: var(--sp-4);
  }
  .call-head {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    padding: var(--card-pad-y) var(--card-pad-x);
    background: linear-gradient(180deg, var(--tint-blue), transparent);
    border-bottom: 1px solid var(--hairline);
  }
  .call-title {
    font-family: var(--font-display);
    font-size: 1.18rem;
    color: var(--rt-dark);
    font-weight: var(--heading-weight);
  }
  .call-meta {
    margin-left: auto;
    font-size: 0.78rem;
    color: var(--rt-text-muted);
    background: var(--surface-3);
    padding: 4px 10px;
    border-radius: 999px;
    font-weight: 600;
  }
  .call-controls {
    display: flex;
    align-items: center;
    gap: var(--sp-4);
    padding: var(--sp-3) var(--card-pad-x);
    border-bottom: 1px solid var(--hairline);
    flex-wrap: wrap;
  }
  .call-footer {
    padding: var(--sp-4) var(--card-pad-x) var(--card-pad-y);
    border-top: 1px solid var(--hairline);
    display: flex;
    gap: var(--sp-3);
    justify-content: flex-end;
  }
</style>
