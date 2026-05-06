<script lang="ts">
  import type { Snippet } from 'svelte';
  import { type Column, type SortDir, sortItems, nextSortState, truncateText } from './data-table';

  /* eslint-disable @typescript-eslint/no-explicit-any */
  let {
    items,
    columns,
    sortKey = '',
    sortDir = 'asc' as SortDir,
    onsort,
    rowHref,
    rowSnippet,
  }: {
    items: any[];
    columns: Column[];
    sortKey?: string;
    sortDir?: SortDir;
    onsort?: (key: string, dir: SortDir) => void;
    rowHref?: (item: any) => string;
    rowSnippet?: Snippet<[any]>;
  } = $props();

  let sortedItems = $derived(
    sortKey ? sortItems(items, columns, sortKey, sortDir) : items
  );

  function handleHeaderClick(col: Column) {
    if (col.sortable === false || !onsort) return;
    const next = nextSortState(sortKey, sortDir, col.key);
    if (next) {
      onsort(next.key, next.dir);
    } else {
      onsort('', 'asc');
    }
  }

  function sortIndicator(col: Column): string {
    if (col.sortable === false) return '';
    if (sortKey !== col.key) return '';
    return sortDir === 'asc' ? '\u25B2' : '\u25BC';
  }

  function cellValue(col: Column, item: any): string {
    const raw = col.getValue(item);
    return String(raw);
  }

  function displayValue(col: Column, item: any): string {
    const val = cellValue(col, item);
    if (col.truncate && val.length > col.truncate) {
      return truncateText(val, col.truncate);
    }
    return val;
  }
</script>

<div class="data-table-wrapper">
  <table class="data-table">
    <thead>
      <tr>
        {#each columns as col (col.key)}
          <th
            class:sortable={col.sortable !== false}
            class:sorted={sortKey === col.key}
            class:align-right={col.align === 'right'}
            class:hide-narrow={col.hideOnNarrow}
          >
            {#if col.sortable !== false}
              <button type="button" class="header-btn" onclick={() => handleHeaderClick(col)}>
                <span>{col.label}</span>
                {#if sortIndicator(col)}
                  <span class="sort-arrow" aria-hidden="true">{sortIndicator(col)}</span>
                {/if}
              </button>
            {:else}
              <span>{col.label}</span>
            {/if}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each sortedItems as item, i (i)}
        {#if rowSnippet}
          {@render rowSnippet(item)}
        {:else if rowHref}
          <tr class="clickable" onclick={() => { window.location.href = rowHref!(item); }}>
            {#each columns as col (col.key)}
              <td
                class:align-right={col.align === 'right'}
                class:hide-narrow={col.hideOnNarrow}
                title={col.truncate && cellValue(col, item).length > col.truncate ? cellValue(col, item) : undefined}
              >
                {#if col.badgeClass}
                  <span class="badge {col.badgeClass(item)}">{displayValue(col, item)}</span>
                {:else}
                  {displayValue(col, item)}
                {/if}
              </td>
            {/each}
          </tr>
        {:else}
          <tr>
            {#each columns as col (col.key)}
              <td
                class:align-right={col.align === 'right'}
                class:hide-narrow={col.hideOnNarrow}
                title={col.truncate && cellValue(col, item).length > col.truncate ? cellValue(col, item) : undefined}
              >
                {#if col.badgeClass}
                  <span class="badge {col.badgeClass(item)}">{displayValue(col, item)}</span>
                {:else}
                  {displayValue(col, item)}
                {/if}
              </td>
            {/each}
          </tr>
        {/if}
      {/each}
    </tbody>
  </table>
</div>

<style>
  .data-table-wrapper {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm);
  }

  thead tr {
    background: var(--rt-bg-subtle, #f4f1ec);
  }

  th {
    text-align: left;
    padding: var(--spacing-sm) var(--spacing-md);
    font-weight: 600;
    font-size: var(--font-size-sm);
    color: var(--rt-text-light, #555);
    border-bottom: 2px solid var(--rt-gray-200, #e4dfda);
    white-space: nowrap;
    user-select: none;
  }

  .header-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: none;
    border: none;
    padding: 0;
    margin: 0;
    font: inherit;
    font-weight: 600;
    color: inherit;
    cursor: pointer;
    white-space: nowrap;
  }

  .header-btn:hover {
    color: var(--color-primary, #3a6db5);
  }

  .sort-arrow {
    font-size: 0.625rem;
  }

  td {
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--rt-gray-200, #e4dfda);
    color: var(--rt-text, #333);
    vertical-align: middle;
  }

  tr.clickable {
    cursor: pointer;
  }

  tbody tr:hover {
    background: var(--rt-gray-100, #f5f3ef);
  }

  .align-right {
    text-align: right;
  }

  @media (max-width: 600px) {
    .hide-narrow {
      display: none;
    }
  }
</style>
