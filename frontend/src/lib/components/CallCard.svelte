<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    titleHref,
    meta,
    controls,
    body,
    footer,
  }: {
    title: string;
    titleHref?: string;
    meta?: string;
    controls?: Snippet;
    body?: Snippet;
    footer?: Snippet;
  } = $props();
</script>

<article class="call">
  <header class="call-head">
    {#if titleHref}
      <a class="call-title call-title-link" href={titleHref}>{title}</a>
    {:else}
      <span class="call-title">{title}</span>
    {/if}
    {#if meta}<span class="call-meta">{meta}</span>{/if}
  </header>
  {#if controls}
    <div class="call-controls">{@render controls()}</div>
  {/if}
  {#if body}
    <div class="call-body">{@render body()}</div>
  {/if}
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
  .call-head:last-child,
  .call-controls:last-child {
    border-bottom: 0;
  }
  .call-title {
    font-family: var(--font-display);
    font-size: var(--fz-h2);
    color: var(--rt-dark);
    font-weight: var(--heading-weight);
  }
  .call-title-link {
    text-decoration: none;
    color: inherit;
    transition: color 0.15s;
  }
  .call-title-link:hover {
    color: var(--rt-blue);
    text-decoration: none;
  }
  .call-meta {
    margin-left: auto;
    font-size: var(--font-size-xs);
    color: var(--rt-text-muted);
    background: var(--surface-3);
    padding: 4px 10px;
    border-radius: var(--radius-pill);
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
