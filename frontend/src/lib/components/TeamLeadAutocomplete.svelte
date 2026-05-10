<script lang="ts">
  import { untrack } from "svelte";
  import AutocompleteInput from "./AutocompleteInput.svelte";
  import { people } from "$lib/api/client";

  type Props = {
    initialId?: string | null;
    initialLabel?: string | null;
    placeholder?: string;
    onselect: (id: string | null, label: string) => void;
  };

  let {
    initialId = null,
    initialLabel = null,
    placeholder = "Team lead",
    onselect,
  }: Props = $props();

  // Tracked alongside the input so we can decide whether the typed text
  // still corresponds to a previously-resolved person. If the user edits
  // away from a confirmed name, we clear the id. The $state initializers
  // capture props once at component construction (intentional — internal
  // state owns the input thereafter).
  let inputValue = $state(untrack(() => initialLabel ?? ""));
  let resolvedId = $state(untrack(() => initialId));
  let resolvedLabel = $state(untrack(() => initialLabel ?? ""));

  async function fetchOptions(q: string) {
    const matches = await people.list({
      role: "team_leader",
      active: true,
      search: q,
    });
    const items = matches.map((p) => ({
      value: p.id,
      label: `${p.first_name} ${p.last_name}`,
    }));
    // Auto-substitute on a unique 3-char match: if the prefix narrows to
    // exactly one person, fill the input with their full name and emit
    // the selection without requiring a click. Mirrors the spec.
    if (q.length >= 3 && items.length === 1 && items[0].label !== inputValue) {
      const only = items[0];
      inputValue = only.label;
      resolvedId = only.value;
      resolvedLabel = only.label;
      onselect(only.value, only.label);
    }
    return items;
  }

  function handleSelect(item: { value: string; label: string }) {
    resolvedId = item.value;
    resolvedLabel = item.label;
    onselect(item.value, item.label);
  }

  // If the user edits away from the resolved label, drop the id so we
  // don't ship a stale team_lead_id with a different displayed name.
  $effect(() => {
    if (resolvedId && inputValue !== resolvedLabel) {
      resolvedId = null;
      onselect(null, inputValue);
    }
  });
</script>

<AutocompleteInput
  bind:inputValue
  {placeholder}
  {fetchOptions}
  onselect={handleSelect}
  minChars={3}
/>
