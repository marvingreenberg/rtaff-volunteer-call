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
    margin-bottom: var(--sp-4, 1rem);
    font-size: 0.85rem;
    color: var(--rt-text-muted);
  }

  ol {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  /* Chevron separator (rotated unicode arrow) replaces the old slash. */
  li:not(:last-child)::after {
    content: '›';
    color: var(--rt-text-muted);
    opacity: 0.5;
  }

  a {
    color: var(--rt-text-muted);
    text-decoration: none;
  }

  a:hover {
    color: var(--rt-blue);
    text-decoration: none;
  }

  span[aria-current='page'] {
    color: var(--rt-dark);
    font-weight: 600;
  }
</style>
