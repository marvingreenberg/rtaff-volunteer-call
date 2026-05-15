<script lang="ts">
  import { untrack } from "svelte";
  import { CITIES } from "$lib/constants/cities";
  import type { TaskCreate } from "$lib/api/client";

  // Structural shape — accepts both TaskCreate and TaskResponse.
  type InitialTask = {
    short_description?: string;
    date?: string | null;
    time_start?: string | null;
    address?: string | null;
    city?: string | null;
    volunteers_needed?: number;
    skilled_needed?: number;
    notes?: string | null;
    team_lead_id?: string | null;
    team_lead_name?: string | null;
  };

  type TeamLead = { id: string; first_name: string; last_name: string };

  type Props = {
    initial?: InitialTask;
    mode?: "add" | "edit";
    teamLeads?: TeamLead[];
    onchange?: (value: TaskCreate | null, dirty: boolean) => void;
  };

  let {
    initial,
    mode: _mode = "add",
    teamLeads = [],
    onchange,
  }: Props = $props();

  const DEFAULT_TIME_DISPLAY = "9:00 AM";
  const DEFAULT_VOLUNTEERS = 4;
  const DEFAULT_SKILLED = 0;

  // Parse free-form time entry. Accepts:
  //   - "9am", "9 am", "9:30am", "9:30 PM"  (12-hour with am/pm)
  //   - "9:00", "13:30"                      (24-hour, colon required)
  function parseTime(text: string): string | null {
    const t = text.trim().toLowerCase();
    if (!t) return null;
    const m = t.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/);
    if (!m) return null;
    let h = parseInt(m[1], 10);
    const min = m[2] ? parseInt(m[2], 10) : 0;
    const ampm = m[3];
    if (min > 59) return null;
    if (ampm) {
      if (h < 1 || h > 12) return null;
      if (ampm === "pm" && h < 12) h += 12;
      if (ampm === "am" && h === 12) h = 0;
    } else {
      if (m[2] === undefined) return null;
      if (h > 23) return null;
    }
    return `${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}`;
  }

  function formatTime12(hhmm: string | null | undefined): string {
    if (!hhmm) return "";
    const m = hhmm.match(/^(\d{2}):(\d{2})$/);
    if (!m) return "";
    const hh = parseInt(m[1], 10);
    const mm = parseInt(m[2], 10);
    const ampm = hh >= 12 ? "PM" : "AM";
    const h12 = hh === 0 ? 12 : hh > 12 ? hh - 12 : hh;
    return `${h12}:${String(mm).padStart(2, "0")} ${ampm}`;
  }

  function isoToMonthDay(iso: string | null | undefined): string {
    if (!iso) return "";
    const m = iso.match(/^\d{4}-(\d{2})-(\d{2})$/);
    return m ? `${m[1]}/${m[2]}` : "";
  }

  function parseMonthDay(text: string): { mm: string; dd: string } | null {
    const m = text.trim().match(/^(\d{1,2})[/\-.](\d{1,2})$/);
    if (!m) return null;
    const month = parseInt(m[1], 10);
    const day = parseInt(m[2], 10);
    if (month < 1 || month > 12 || day < 1 || day > 31) return null;
    return {
      mm: String(month).padStart(2, "0"),
      dd: String(day).padStart(2, "0"),
    };
  }

  function smartYear(mm: string, dd: string): number {
    const now = new Date();
    const yearTry = now.getFullYear();
    const candidate = new Date(yearTry, parseInt(mm, 10) - 1, parseInt(dd, 10));
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return candidate < today ? yearTry + 1 : yearTry;
  }

  // Capture initial values once at construction; subsequent prop changes
  // don't reset the form (intentional — internal state owns the fields).
  const initialIsoDate = untrack(() => initial?.date ?? null);
  let dateText = $state(untrack(() => isoToMonthDay(initial?.date)));
  let timeText = $state(
    untrack(() => formatTime12(initial?.time_start) || DEFAULT_TIME_DISPLAY),
  );
  let address = $state(untrack(() => initial?.address ?? ""));
  let city = $state(untrack(() => initial?.city ?? ""));
  let volunteersNeeded = $state<number | null>(
    untrack(() => initial?.volunteers_needed ?? DEFAULT_VOLUNTEERS),
  );
  let skilledNeeded = $state<number | null>(
    untrack(() => initial?.skilled_needed ?? DEFAULT_SKILLED),
  );
  let shortDescription = $state(
    untrack(() => initial?.short_description ?? ""),
  );
  let notes = $state(untrack(() => initial?.notes ?? ""));
  let teamLeadId = $state<string | null>(
    untrack(() => initial?.team_lead_id ?? null),
  );

  let parsedDate = $derived.by(() => {
    const md = parseMonthDay(dateText);
    if (!md) return null;
    if (
      initialIsoDate &&
      isoToMonthDay(initialIsoDate) === `${md.mm}/${md.dd}`
    ) {
      return initialIsoDate;
    }
    return `${smartYear(md.mm, md.dd)}-${md.mm}-${md.dd}`;
  });

  let parsedTime = $derived(parseTime(timeText));

  let dateMissing = $derived(!parsedDate);
  let addressMissing = $derived(!address.trim());
  let cityMissing = $derived(!city.trim());
  let descriptionMissing = $derived(!shortDescription.trim());

  let valid = $derived(
    !dateMissing && !addressMissing && !cityMissing && !descriptionMissing,
  );

  const initialRaw = untrack(() => ({
    dateText,
    timeText,
    address,
    city,
    volunteersNeeded,
    skilledNeeded,
    shortDescription,
    notes,
    teamLeadId,
  }));

  let dirty = $derived(
    dateText !== initialRaw.dateText ||
      timeText !== initialRaw.timeText ||
      address !== initialRaw.address ||
      city !== initialRaw.city ||
      volunteersNeeded !== initialRaw.volunteersNeeded ||
      skilledNeeded !== initialRaw.skilledNeeded ||
      shortDescription !== initialRaw.shortDescription ||
      notes !== initialRaw.notes ||
      teamLeadId !== initialRaw.teamLeadId,
  );

  let currentPayload = $derived<TaskCreate | null>(
    valid
      ? {
          short_description: shortDescription.trim(),
          date: parsedDate,
          time_start: parsedTime,
          time_end: null,
          address: address.trim() || null,
          city: city.trim() || null,
          volunteers_needed: volunteersNeeded ?? DEFAULT_VOLUNTEERS,
          skilled_needed: skilledNeeded ?? DEFAULT_SKILLED,
          notes: notes.trim() || null,
          team_lead_id: teamLeadId,
        }
      : null,
  );

  $effect(() => {
    onchange?.(currentPayload, dirty);
  });

  // Auto-insert "/" once the user has typed a third digit into MM/DD with
  // no separator yet. Only fires on direct keystrokes (insertText) so paste
  // and deletion leave the buffer alone.
  function handleDateInput(e: Event) {
    const evt = e as InputEvent;
    if (evt.inputType !== "insertText") return;
    if (!evt.data || !/^\d$/.test(evt.data)) return;
    const m = dateText.match(/^(\d{2})(\d+)$/);
    if (m) dateText = `${m[1]}/${m[2]}`;
  }
</script>

<div class="task-entry-form">
  <div class="form-row">
    <div class="field icon-field">
      <span class="leading-icon" aria-hidden="true">
        <!-- Calendar -->
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M3 9h18" />
          <path d="M8 3v4M16 3v4" />
        </svg>
      </span>
      <input
        type="text"
        data-testid="task-date"
        bind:value={dateText}
        oninput={handleDateInput}
        placeholder="MM/DD"
        title="Task date (year inferred — past dates roll into next year)"
        aria-label="Task date, MM slash DD"
        inputmode="numeric"
        autocomplete="off"
        data-empty={!dateText.trim()}
        class:invalid={dateMissing}
        aria-invalid={dateMissing}
      />
    </div>
    <div class="field icon-field">
      <span class="leading-icon" aria-hidden="true">
        <!-- Clock -->
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </svg>
      </span>
      <input
        type="text"
        bind:value={timeText}
        placeholder={DEFAULT_TIME_DISPLAY}
        title="Start time — e.g. 9am, 9:30am, 1pm, or 13:30"
        aria-label="Start time"
        autocomplete="off"
        data-empty={!timeText.trim() || timeText === DEFAULT_TIME_DISPLAY}
      />
    </div>
  </div>

  <div class="form-row">
    <div class="field icon-field">
      <span class="leading-icon" aria-hidden="true">
        <!-- Home -->
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M3 12 12 3l9 9" />
          <path d="M5 10v10h4v-6h6v6h4V10" />
        </svg>
      </span>
      <input
        type="text"
        data-testid="task-address"
        bind:value={address}
        placeholder="Address"
        title="Street address"
        aria-label="Street address"
        class:invalid={addressMissing}
        aria-invalid={addressMissing}
      />
    </div>
    <div class="field icon-field">
      <span class="leading-icon" aria-hidden="true">
        <!-- Buildings -->
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="3" y="10" width="6" height="11" />
          <rect x="9" y="3" width="6" height="18" />
          <rect x="15" y="13" width="6" height="8" />
        </svg>
      </span>
      <select
        data-testid="task-city"
        bind:value={city}
        aria-label="City"
        class:invalid={cityMissing}
        aria-invalid={cityMissing}
        data-empty={!city}
      >
        <option value="">City</option>
        {#each CITIES as c (c)}
          <option value={c}>{c}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="form-row inline-row">
    <label class="inline-num" title="Number of volunteers needed">
      <span># Volunteers</span>
      <input
        type="number"
        min="1"
        bind:value={volunteersNeeded}
        data-default={volunteersNeeded === DEFAULT_VOLUNTEERS}
      />
    </label>
    <label class="inline-num" title="Number of skilled volunteers needed">
      <span># Skilled</span>
      <input
        type="number"
        min="0"
        bind:value={skilledNeeded}
        data-default={skilledNeeded === DEFAULT_SKILLED}
      />
    </label>
  </div>

  <div class="form-row">
    <textarea
      class="description"
      data-testid="task-description"
      bind:value={shortDescription}
      placeholder="e.g., Install two lights, repair drywall, grab bars in upstairs bathroom"
      title="What needs to be done"
      aria-label="Task description"
      rows="2"
      class:invalid={descriptionMissing}
      aria-invalid={descriptionMissing}
    ></textarea>
  </div>

  <div class="form-row">
    <div class="field">
      <select
        bind:value={teamLeadId}
        aria-label="Team lead"
        data-empty={teamLeadId === null}
      >
        <option value={null}>Team lead (optional)</option>
        {#each teamLeads as lead (lead.id)}
          <option value={lead.id}>{lead.first_name} {lead.last_name}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="form-row">
    <textarea
      class="description notes"
      bind:value={notes}
      placeholder="Notes for the team (parking, what to bring, access info)"
      title="Notes shown to assigned volunteers and the team lead"
      aria-label="Task notes"
      rows="2"
    ></textarea>
  </div>
</div>

<style>
  .task-entry-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .form-row {
    display: flex;
    gap: var(--spacing-md);
  }

  .field {
    flex: 1;
    min-width: 0;
  }

  .field input,
  .field select {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: var(--btn-min-height);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    font-size: inherit;
    font-family: var(--font-body);
    background: var(--rt-white);
    color: var(--color-text);
    box-sizing: border-box;
  }

  .field input:focus,
  .field select:focus {
    outline: none;
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.2);
  }

  /* Empty/default-value inputs render in muted gray so a still-default
     value is visually distinct from one the user has actively confirmed. */
  .field input[data-empty="true"],
  .field select[data-empty="true"] {
    color: var(--rt-text-muted, #777);
  }
  .inline-num input[data-default="true"] {
    color: var(--rt-text-muted, #777);
  }

  /* Inputs with a leading icon — pad the text away from the glyph. */
  .icon-field {
    position: relative;
  }

  .leading-icon {
    position: absolute;
    left: var(--spacing-sm);
    top: 50%;
    transform: translateY(-50%);
    width: 18px;
    height: 18px;
    color: var(--rt-text-muted, #777);
    pointer-events: none;
    z-index: 1;
  }

  .leading-icon svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  .icon-field input,
  .icon-field select {
    padding-left: calc(var(--spacing-sm) * 2 + 18px);
  }

  .inline-row {
    align-items: center;
    gap: var(--spacing-lg);
  }

  .inline-num {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: var(--font-size-sm);
    color: var(--rt-gray-600, #555);
    font-weight: 500;
  }

  .inline-num input {
    width: 5em;
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: var(--btn-min-height);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    font-size: inherit;
    font-family: var(--font-body);
    background: var(--rt-white);
    color: var(--color-text);
    box-sizing: border-box;
  }

  .inline-num input:focus {
    outline: none;
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.2);
  }

  .description {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    font-size: inherit;
    font-family: var(--font-body);
    background: var(--rt-white);
    color: var(--color-text);
    box-sizing: border-box;
    resize: vertical;
    field-sizing: content;
    min-height: calc(var(--btn-min-height) + 0.5em);
  }

  .description:focus {
    outline: none;
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.2);
  }

  input.invalid,
  select.invalid,
  textarea.invalid {
    border-color: var(--rt-error, #c53030);
  }

  @media (max-width: 600px) {
    .form-row {
      flex-direction: column;
    }
    .inline-row {
      flex-direction: row;
      flex-wrap: wrap;
    }
  }
</style>
