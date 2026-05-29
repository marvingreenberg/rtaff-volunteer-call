<script lang="ts">
  let {
    name,
    summary,
    description,
    city,
    date,
    time,
    volunteersNeeded,
    skilledNeeded = 0,
    notes,
    checked = false,
    expanded = false,
    conflict = false,
    conflictTitle = "",
    onToggleChecked,
    onToggleExpanded,
  }: {
    name: string;
    summary: string;
    description?: string;
    city?: string;
    date?: string;
    time?: string;
    volunteersNeeded?: number;
    skilledNeeded?: number;
    notes?: string;
    checked?: boolean;
    expanded?: boolean;
    conflict?: boolean;
    conflictTitle?: string;
    onToggleChecked?: () => void;
    onToggleExpanded?: () => void;
  } = $props();

  function bodyKey(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onToggleExpanded?.();
    }
  }
</script>

<li class="task" class:checked class:expanded>
  <input
    type="checkbox"
    class="task-check"
    {checked}
    onchange={() => onToggleChecked?.()}
    aria-label={`Toggle ${name}`}
  />

  <div
    class="task-body"
    role="button"
    tabindex="0"
    aria-expanded={expanded}
    onclick={() => onToggleExpanded?.()}
    onkeydown={bodyKey}
  >
    <div class="task-name">
      {name}
      {#if conflict}
        <span class="conflict-flag" title={conflictTitle}>⚠ calendar conflict</span>
      {/if}
    </div>
    <div class="task-summary">{summary}</div>
    <div class="task-meta">
      {#if city}{city}{/if}
      {#if city && date} · {/if}
      {#if date}{date}{/if}
    </div>
  </div>

  <button
    type="button"
    class="task-expand"
    aria-label={expanded ? "Collapse" : "Expand"}
    onclick={() => onToggleExpanded?.()}
  >
    <span class="chev" class:open={expanded} aria-hidden="true">▾</span>
  </button>

  <dl class="task-detail">
    {#if description}
      <dd class="task-description">{description}</dd>
    {/if}
    {#if time}<dt>Time</dt>
      <dd>{time}</dd>{/if}
    {#if volunteersNeeded != null}<dt>Volunteers needed</dt>
      <dd>{volunteersNeeded}</dd>{/if}
    {#if skilledNeeded > 0}<dt>Skilled needed</dt>
      <dd>{skilledNeeded}</dd>{/if}
    {#if notes}<dt>Notes</dt>
      <dd>{notes}</dd>{/if}
  </dl>
</li>

<style>
  .task {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: var(--sp-3);
    padding: var(--task-pad-y) var(--task-pad-x);
    border-radius: var(--radius-sm);
    background: var(--surface-2);
    border: 1px solid transparent;
    transition:
      background 0.15s,
      border-color 0.15s,
      transform 0.15s;
  }
  .task:hover {
    background: var(--surface-1);
    border-color: var(--hairline);
  }
  .task.checked {
    background:
      linear-gradient(180deg, var(--tint-green), transparent), var(--surface-1);
    border-color: rgba(90, 173, 68, 0.35);
  }

  .task-check {
    appearance: none;
    -webkit-appearance: none;
    width: var(--check-size);
    height: var(--check-size);
    border-radius: 6px;
    border: 1.5px solid #c5cad2;
    background: var(--surface-1);
    cursor: pointer;
    display: grid;
    place-items: center;
    transition:
      background 0.15s,
      border-color 0.15s;
  }
  .task-check:checked {
    background: linear-gradient(135deg, var(--rt-green), var(--rt-green-dark));
    border-color: var(--rt-green-dark);
  }
  .task-check:checked::after {
    content: "✓";
    color: white;
    font-size: 0.78em;
    font-weight: 800;
  }

  .task-body {
    min-width: 0;
    cursor: pointer;
  }
  .task-name {
    font-weight: 600;
    color: var(--rt-dark);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .task-summary {
    font-size: 0.92em;
    color: var(--rt-text);
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    line-clamp: 1;
    -webkit-box-orient: vertical;
  }
  .task.expanded .task-summary {
    display: none;
  }
  .task-meta {
    font-size: 0.82em;
    color: var(--rt-text-muted);
    margin-top: 2px;
  }
  .conflict-flag {
    font-size: 0.7rem;
    padding: 2px 7px;
    border-radius: 999px;
    background: var(--tint-orange);
    color: #8c5a10;
    font-weight: 600;
  }

  .task-expand {
    appearance: none;
    border: 0;
    background: transparent;
    cursor: pointer;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    color: var(--rt-text-muted);
    display: grid;
    place-items: center;
    transition: background 0.15s;
  }
  .task-expand:hover {
    background: var(--surface-3);
  }
  .chev {
    display: inline-block;
    transition: transform 0.2s;
  }
  .chev.open {
    transform: rotate(180deg);
  }

  .task-detail {
    grid-column: 1 / -1;
    margin: var(--sp-3) 0 0;
    padding: var(--sp-3) 0 0;
    border-top: 1px solid var(--hairline);
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px var(--sp-4);
    font-size: 0.9em;
  }
  .task-detail dt {
    color: var(--rt-text-muted);
    font-weight: 500;
  }
  .task-detail dd {
    margin: 0;
    color: var(--rt-text);
  }
  .task-description {
    grid-column: 1 / -1;
    margin: 0 0 var(--sp-3) 0;
    color: var(--rt-text);
    line-height: 1.55;
    white-space: pre-line;
  }
  .task:not(.expanded) .task-detail {
    display: none;
  }

  /* Density: compact = flat borderless row, inline meta */
  :global([data-density="compact"]) .task {
    background: transparent;
    border-radius: 0;
    border-top: 1px solid var(--hairline);
    padding: 8px 14px;
    grid-template-columns: auto 1fr auto auto;
    align-items: center;
  }
  :global([data-density="compact"]) .task.checked {
    background: rgba(90, 173, 68, 0.08);
  }
  :global([data-density="compact"]) .task-body {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }
  :global([data-density="compact"]) .task-summary {
    display: none;
  }
  :global([data-density="compact"]) .task-meta {
    margin: 0 0 0 auto;
    white-space: nowrap;
  }

  /* Density: large = floating card with shadow halo */
  :global([data-density="large"]) .task {
    background: var(--surface-1);
    border: 1px solid var(--hairline);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 1),
      0 2px 8px -6px rgba(30, 47, 61, 0.15);
  }
  :global([data-density="large"]) .task:hover {
    transform: translateY(-1px);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 1),
      0 6px 18px -10px rgba(30, 47, 61, 0.25);
  }
</style>
