<script lang="ts">
  let { crumbs }: { crumbs: Array<{ label: string; href?: string }> } = $props();
</script>

<nav class="breadcrumb" aria-label="Breadcrumb">
  <ol>
    {#each crumbs as crumb, i (i)}
      <li>
        {#if crumb.href && i < crumbs.length - 1}
          <a href={crumb.href}>{crumb.label}</a>
        {:else}
          <span aria-current={i === crumbs.length - 1 ? 'page' : undefined}>{crumb.label}</span>
        {/if}
      </li>
    {/each}
  </ol>
</nav>

<style>
  .breadcrumb {
    margin-bottom: var(--spacing-md, 1rem);
    font-size: var(--font-size-sm, 0.875rem);
  }

  ol {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-xs);
    list-style: none;
    margin: 0;
    padding: 0;
  }

  li:not(:last-child)::after {
    content: '/';
    margin-left: var(--spacing-xs);
    color: var(--rt-text-muted, #777);
  }

  a {
    color: var(--color-primary, #3a6db5);
    text-decoration: none;
  }

  a:hover {
    text-decoration: underline;
  }

  span[aria-current='page'] {
    color: var(--rt-text-muted, #777);
  }
</style>
