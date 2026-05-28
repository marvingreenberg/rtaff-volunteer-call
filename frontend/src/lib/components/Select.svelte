<script lang="ts">
  /**
   * Custom-rendered combobox.
   *
   * Renders its own trigger + popup option list so the open dropdown
   * matches the rest of the app's chrome instead of falling back to
   * the OS-native popup that a plain ``<select>`` exposes.
   *
   * Accessibility:
   * - Trigger is a real ``<button>`` with aria-haspopup="listbox" and
   *   aria-expanded; aria-activedescendant points at the highlighted
   *   row while the popup is open.
   * - Popup is role="listbox"; rows are role="option" with
   *   aria-selected.
   * - Keyboard: ↑/↓ navigate, Home/End jump, Enter/Space commit,
   *   Escape closes without committing, Tab closes (focus moves on).
   * - Typing a printable character jumps to the first option whose
   *   label starts with the typed prefix (Windows-style type-ahead).
   */
  import { tick } from "svelte";

  // null is allowed so callers like the team-lead picker can model
  // "no team lead" without smuggling an empty-string sentinel.
  type Primitive = string | number | null;
  interface Option {
    value: Primitive;
    label: string;
  }

  let {
    value = $bindable<Primitive>(),
    options,
    ariaLabel,
    disabled = false,
    onchange,
    placeholder,
  }: {
    value: Primitive;
    options: Option[];
    ariaLabel?: string;
    disabled?: boolean;
    onchange?: (value: Primitive) => void;
    /**
     * Label shown on the trigger when ``value`` doesn't match any
     * option (e.g. when the bound value is null/"" and no option
     * carries that sentinel). The popup itself is unaffected.
     */
    placeholder?: string;
  } = $props();

  let open = $state(false);
  let highlightIdx = $state(0);
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let listEl = $state<HTMLUListElement | null>(null);

  // Stable id prefix per instance for ARIA wiring. Only needs DOM
  // uniqueness, so Math.random is fine.
  const idPrefix = `app-select-${Math.random().toString(36).slice(2, 9)}`;
  const listId = `${idPrefix}-list`;

  let typeBuffer = "";
  let typeBufferTimer: ReturnType<typeof setTimeout> | null = null;

  // -1 when the current value doesn't match any option — used to drive
  // the placeholder fallback rather than silently snapping to the
  // first option's label.
  let selectedIdx = $derived(options.findIndex((o) => o.value === value));

  let selectedLabel = $derived(
    selectedIdx >= 0 ? options[selectedIdx].label : (placeholder ?? ""),
  );

  let isPlaceholderShown = $derived(selectedIdx < 0 && !!placeholder);

  async function openPopup() {
    if (disabled || open) return;
    open = true;
    highlightIdx = selectedIdx >= 0 ? selectedIdx : 0;
    await tick();
    scrollHighlightIntoView();
  }

  function closePopup() {
    open = false;
  }

  function commit(idx: number) {
    const opt = options[idx];
    if (!opt) return;
    value = opt.value;
    onchange?.(opt.value);
    closePopup();
    triggerEl?.focus();
  }

  function scrollHighlightIntoView() {
    if (!listEl) return;
    const row = listEl.querySelector<HTMLElement>(
      `[data-idx="${highlightIdx}"]`,
    );
    // scrollIntoView is missing in JSDOM (test env) — guard so tests
    // don't blow up with an uncaught TypeError.
    if (row && typeof row.scrollIntoView === "function") {
      row.scrollIntoView({ block: "nearest" });
    }
  }

  function move(delta: number) {
    if (options.length === 0) return;
    highlightIdx = (highlightIdx + delta + options.length) % options.length;
    scrollHighlightIntoView();
  }

  function jumpToTyped(ch: string) {
    if (typeBufferTimer) clearTimeout(typeBufferTimer);
    typeBuffer = (typeBuffer + ch).toLowerCase();
    const match = options.findIndex((o) =>
      o.label.toLowerCase().startsWith(typeBuffer),
    );
    if (match >= 0) {
      highlightIdx = match;
      scrollHighlightIntoView();
    }
    typeBufferTimer = setTimeout(() => (typeBuffer = ""), 600);
  }

  function handleTriggerKey(e: KeyboardEvent) {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPopup();
    }
  }

  function handleListKey(e: KeyboardEvent) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        move(1);
        return;
      case "ArrowUp":
        e.preventDefault();
        move(-1);
        return;
      case "Home":
        e.preventDefault();
        highlightIdx = 0;
        scrollHighlightIntoView();
        return;
      case "End":
        e.preventDefault();
        highlightIdx = options.length - 1;
        scrollHighlightIntoView();
        return;
      case "Enter":
      case " ":
        e.preventDefault();
        commit(highlightIdx);
        return;
      case "Escape":
        e.preventDefault();
        closePopup();
        triggerEl?.focus();
        return;
      case "Tab":
        closePopup();
        return;
    }
    if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {
      e.preventDefault();
      jumpToTyped(e.key);
    }
  }

  function handleWindowKey(e: KeyboardEvent) {
    // Popup never receives focus on its own (the trigger keeps focus
    // through the open lifecycle) so route keys at the window level.
    if (!open) return;
    handleListKey(e);
  }

  function handleDocumentClick(e: MouseEvent) {
    if (!open) return;
    const target = e.target as Node | null;
    if (!target) return;
    if (triggerEl?.contains(target)) return;
    if (listEl?.contains(target)) return;
    closePopup();
  }
</script>

<svelte:document onclick={handleDocumentClick} />
<svelte:window onkeydown={handleWindowKey} />

<span class="app-select" class:open class:disabled>
  <button
    bind:this={triggerEl}
    type="button"
    class="app-select-trigger"
    role="combobox"
    {disabled}
    aria-haspopup="listbox"
    aria-expanded={open}
    aria-controls={listId}
    aria-activedescendant={open ? `${listId}-opt-${highlightIdx}` : undefined}
    aria-label={ariaLabel}
    onclick={() => (open ? closePopup() : openPopup())}
    onkeydown={handleTriggerKey}
  >
    <span class="app-select-label" class:placeholder={isPlaceholderShown}>
      {selectedLabel}
    </span>
    <span class="app-select-chevron" aria-hidden="true">▾</span>
  </button>

  {#if open}
    <ul
      bind:this={listEl}
      id={listId}
      class="app-select-list"
      role="listbox"
      tabindex="-1"
      aria-label={ariaLabel}
    >
      {#each options as opt, i (opt.value)}
        <!--
          Listbox-pattern WAI-ARIA: keyboard handling lives on the
          containing element (we forward via window since the popup
          never holds focus). Rows only need click + hover. The
          a11y_click_events_have_key_events rule doesn't recognize
          this composition, so silence it just here.
        -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <li
          id={`${listId}-opt-${i}`}
          class="app-select-opt"
          class:selected={i === selectedIdx}
          class:highlighted={i === highlightIdx}
          role="option"
          aria-selected={i === selectedIdx}
          data-idx={i}
          onclick={() => commit(i)}
          onmouseenter={() => (highlightIdx = i)}
        >
          {opt.label}
        </li>
      {/each}
    </ul>
  {/if}
</span>

<style>
  .app-select {
    position: relative;
    display: inline-flex;
    align-items: stretch;
  }

  .app-select-trigger {
    appearance: none;
    -webkit-appearance: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px 4px 12px;
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
    background: var(--rt-white, #fff);
    color: inherit;
    font: inherit;
    min-height: 32px;
    cursor: pointer;
    white-space: nowrap;
  }

  .app-select-trigger:focus-visible {
    outline: none;
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.2);
  }

  .app-select.open .app-select-trigger {
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.2);
  }

  .app-select-trigger:disabled {
    background: var(--rt-gray-100, #f5f3ef);
    cursor: not-allowed;
    color: var(--rt-text-muted, #777);
  }

  .app-select-label {
    flex: 1;
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .app-select-label.placeholder {
    color: var(--rt-text-muted, #777);
  }

  .app-select-chevron {
    font-size: 10px;
    color: var(--rt-text-muted, #777);
    line-height: 1;
  }

  .app-select-list {
    position: absolute;
    z-index: 200;
    top: calc(100% + 4px);
    left: 0;
    min-width: 100%;
    max-height: 280px;
    overflow-y: auto;
    margin: 0;
    padding: 4px 0;
    list-style: none;
    background: var(--rt-white, #fff);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  }

  .app-select-opt {
    padding: 6px 12px;
    font: inherit;
    cursor: pointer;
    color: var(--rt-dark, #222);
    white-space: nowrap;
  }

  .app-select-opt.highlighted {
    background: var(--rt-gray-100, #f5f3ef);
  }

  .app-select-opt.selected {
    color: var(--color-primary, #3a6db5);
    font-weight: 600;
  }

  .app-select-opt.selected.highlighted {
    background: rgba(58, 109, 181, 0.12);
  }
</style>
