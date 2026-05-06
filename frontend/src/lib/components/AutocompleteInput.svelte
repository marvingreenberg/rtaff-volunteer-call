<script lang="ts">
  import { Combobox } from 'bits-ui';

  interface Item {
    value: string;
    label: string;
    description?: string;
  }

  let {
    fetchOptions,
    placeholder = '',
    inputValue = $bindable(''),
    onselect,
    minChars = 3,
  }: {
    fetchOptions: (query: string) => Promise<Item[]>;
    placeholder?: string;
    inputValue?: string;
    onselect?: (item: Item) => void;
    minChars?: number;
  } = $props();

  let inputText = $state('');
  let cachedOptions: Item[] = $state([]);
  let cachedQuery = $state('');
  let dropdownOpen = $state(false);
  let highlightedValue = $state('');
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  let displayedItems = $derived(
    cachedQuery
      ? cachedOptions.filter((item) => item.label.toLowerCase().includes(inputText.toLowerCase()))
      : []
  );

  // Sync inputText when parent clears inputValue externally
  $effect(() => {
    if (inputValue !== inputText) {
      inputText = inputValue;
    }
  });

  async function handleInput(e: Event) {
    const target = e.currentTarget as HTMLInputElement;
    inputText = target.value;
    inputValue = inputText;

    if (debounceTimer !== null) { clearTimeout(debounceTimer); debounceTimer = null; }

    if (inputText.length < minChars) {
      cachedQuery = '';
      cachedOptions = [];
      dropdownOpen = false;
      return;
    }

    // Current input extends cached query — filter client-side, no fetch needed
    if (cachedQuery && inputText.startsWith(cachedQuery)) {
      dropdownOpen = displayedItems.length > 0;
      return;
    }

    const prefixQuery = inputText.slice(0, minChars);

    if (inputText.length === minChars) {
      // Exactly at threshold — fetch immediately, no debounce
      const results = await fetchOptions(prefixQuery);
      cachedQuery = prefixQuery;
      cachedOptions = results;
      dropdownOpen = results.length > 0;
    } else {
      // Typed past threshold before debounce fired — short catch-up debounce
      debounceTimer = setTimeout(async () => {
        if (cachedQuery) return;
        const results = await fetchOptions(prefixQuery);
        cachedQuery = prefixQuery;
        cachedOptions = results;
        dropdownOpen = displayedItems.length > 0;
      }, 150);
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && dropdownOpen && displayedItems.length > 0 && !highlightedValue) {
      e.preventDefault();
      handleSelect(displayedItems[0].value);
    }
  }

  function handleSelect(value: string) {
    const item = cachedOptions.find((i) => i.value === value);
    if (!item) return;
    inputText = item.label;
    inputValue = item.label;
    dropdownOpen = false;
    highlightedValue = '';
    onselect?.(item);
  }
</script>

<div class="autocomplete-wrapper">
  <Combobox.Root
    type="single"
    onValueChange={handleSelect}
    open={dropdownOpen}
    inputValue={inputText}
  >
    <Combobox.Input
      class="autocomplete-input"
      {placeholder}
      oninput={handleInput}
      onkeydown={handleKeydown}
    />
    {#if dropdownOpen && displayedItems.length > 0}
      <Combobox.ContentStatic class="autocomplete-dropdown">
        {#each displayedItems as item (item.value)}
          <Combobox.Item
            value={item.value}
            label={item.label}
            class="autocomplete-item"
            onHighlight={() => { highlightedValue = item.value; }}
            onUnhighlight={() => { if (highlightedValue === item.value) highlightedValue = ''; }}
          >
            {#snippet children({ selected: _ })}
              <span class="item-label">{item.label}</span>
              {#if item.description}
                <span class="item-description">{item.description}</span>
              {/if}
            {/snippet}
          </Combobox.Item>
        {/each}
      </Combobox.ContentStatic>
    {/if}
  </Combobox.Root>
</div>

<style>
  .autocomplete-wrapper {
    position: relative;
    width: 100%;
  }

  :global(.autocomplete-input) {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: var(--btn-min-height);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    font-size: var(--btn-font-size);
    font-family: var(--font-body, sans-serif);
    background: var(--rt-white, #ffffff);
    color: var(--color-text, #3b3b3b);
    box-sizing: border-box;
  }

  :global(.autocomplete-input:focus) {
    outline: none;
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.2);
  }

  :global(.autocomplete-dropdown) {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    margin: 2px 0 0;
    padding: 0;
    list-style: none;
    background: var(--rt-white, #ffffff);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    z-index: 100;
    max-height: 280px;
    overflow-y: auto;
  }

  :global(.autocomplete-item) {
    display: flex;
    flex-direction: column;
    padding: var(--spacing-sm) var(--spacing-md);
    cursor: pointer;
    border-bottom: 1px solid var(--rt-gray-100, #f5f3ef);
    min-height: var(--btn-min-height);
    justify-content: center;
  }

  :global(.autocomplete-item:last-child) {
    border-bottom: none;
  }

  :global(.autocomplete-item:hover) {
    background: var(--rt-gray-100, #f5f3ef);
  }

  .item-label {
    font-weight: 600;
    color: var(--rt-text, #3b3b3b);
  }

  .item-description {
    font-size: var(--font-size-sm, 0.85rem);
    color: var(--rt-text-muted, #777777);
    margin-top: 1px;
  }
</style>
