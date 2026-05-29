<script lang="ts">
  import { people } from "$lib/api/client";
  import { confirmDialog } from "$lib/stores/confirm.svelte";
  import type { PersonCalendarSummary } from "$lib/api/types";

  type Props = {
    personId: string;
    calendars: PersonCalendarSummary[];
    onChanged: () => void | Promise<void>;
  };

  let { personId, calendars, onChanged }: Props = $props();

  let showAdd = $state(false);
  let urlInput = $state("");
  let labelInput = $state("");
  let providerInput = $state("");
  let saving = $state(false);
  let errorMsg = $state("");
  let activeTab = $state<"general" | "apple" | "google" | "outlook">(
    "general",
  );

  const TABS: { id: typeof activeTab; label: string }[] = [
    { id: "general", label: "General info" },
    { id: "apple", label: "Apple" },
    { id: "google", label: "Google" },
    { id: "outlook", label: "Outlook" },
  ];

  function toggleAdd() {
    showAdd = !showAdd;
    if (!showAdd) errorMsg = "";
  }

  async function handleAdd(e: SubmitEvent) {
    e.preventDefault();
    const url = urlInput.trim();
    if (!url) return;
    saving = true;
    errorMsg = "";
    try {
      await people.addCalendar(personId, {
        calendar_url: url,
        calendar_provider: providerInput.trim() || null,
        label: labelInput.trim() || null,
      });
      urlInput = "";
      labelInput = "";
      providerInput = "";
      showAdd = false;
      await onChanged();
    } catch (err) {
      errorMsg =
        err instanceof Error
          ? err.message
          : "Couldn't connect calendar. Try again.";
    } finally {
      saving = false;
    }
  }

  async function handleRemove(cal: PersonCalendarSummary) {
    const name = cal.label ?? cal.calendar_provider ?? "this calendar";
    const ok = await confirmDialog({
      title: "Disconnect calendar?",
      body: `Disconnect ${name}? Conflict warnings from it will stop.`,
      okLabel: "Disconnect",
      danger: true,
    });
    if (!ok) return;
    saving = true;
    errorMsg = "";
    try {
      await people.removeCalendar(personId, cal.id);
      await onChanged();
    } catch (err) {
      errorMsg =
        err instanceof Error
          ? err.message
          : "Couldn't disconnect calendar. Try again.";
    } finally {
      saving = false;
    }
  }
</script>

<div class="calendar-connect">
  {#if errorMsg}
    <div class="error-banner" role="alert">{errorMsg}</div>
  {/if}

  {#if calendars.length > 0}
    <ul class="cal-list" aria-label="Connected calendars">
      {#each calendars as cal (cal.id)}
        <li class="cal-row">
          <span class="cal-label">{cal.label ?? "Calendar"}</span>
          {#if cal.calendar_provider}
            <span class="cal-provider">{cal.calendar_provider}</span>
          {/if}
          <button
            type="button"
            class="cal-remove"
            aria-label={`Disconnect ${cal.label ?? "calendar"}`}
            onclick={() => handleRemove(cal)}
            disabled={saving}
          >
            ×
          </button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="empty-hint">
      No calendars connected. Add one to see conflicts on assignment dates.
    </p>
  {/if}

  <button
    type="button"
    class="add-toggle"
    aria-expanded={showAdd}
    onclick={toggleAdd}
  >
    {showAdd ? "Cancel" : "Add a calendar"}
  </button>

  {#if showAdd}
    <form onsubmit={handleAdd} class="connect-form">
      <label class="field">
        <span class="field-label">Label (optional)</span>
        <input
          type="text"
          bind:value={labelInput}
          placeholder="Personal, Work…"
          autocomplete="off"
        />
      </label>
      <label class="field">
        <span class="field-label">Shared calendar URL</span>
        <input
          type="url"
          bind:value={urlInput}
          placeholder="https://..."
          required
          autocomplete="off"
          spellcheck="false"
        />
      </label>
      <label class="field">
        <span class="field-label">Provider (optional)</span>
        <input
          type="text"
          bind:value={providerInput}
          placeholder="Google, Apple, Outlook…"
          autocomplete="off"
        />
      </label>
      <button
        type="submit"
        class="btn btn-primary"
        disabled={saving || !urlInput.trim()}
      >
        {saving ? "Connecting…" : "Connect"}
      </button>
    </form>

    <details class="help">
      <summary>Help &mdash; getting your calendar URL</summary>
      <div class="help-body">
        <div class="tabs" role="tablist">
          {#each TABS as t (t.id)}
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === t.id}
              class="tab"
              class:active={activeTab === t.id}
              onclick={() => (activeTab = t.id)}
            >
              {t.label}
            </button>
          {/each}
        </div>

        <div class="tab-panel" role="tabpanel">
          {#if activeTab === "general"}
            <p>
              A "calendar URL" is a private subscription link that lets us read
              the busy/free times on your calendar. You publish it once from your
              calendar app, paste the URL here, and we'll flag any volunteer
              task that overlaps an existing event.
            </p>
            <p>
              Treat the URL as a secret &mdash; anyone with it could read your
              calendar. We never display it back to you and never share it.
            </p>
            <p>
              You can connect multiple calendars (e.g. personal + work);
              conflicts from all of them are merged on each task.
            </p>
          {:else if activeTab === "apple"}
            <ol>
              <li>Open Apple Calendar and right-click the calendar you want to share.</li>
              <li>Choose <em>Share Calendar</em> and turn on <em>Public Calendar</em>.</li>
              <li>Copy the <code>webcal://</code> link and paste it above.</li>
            </ol>
            <img
              src="/screenshots/apple-calendar.png"
              alt="Apple Calendar share dialog with Public Calendar enabled and the link visible"
            />
          {:else if activeTab === "google"}
            <ol>
              <li>
                Open Google Calendar &raquo; <em>Settings</em> &raquo;
                <em>Settings for my calendars</em> and pick your calendar.
              </li>
              <li>
                Under <em>Access permissions for events</em> check
                <em>Make available to public</em> (free/busy is enough).
              </li>
              <li>
                Click <em>Get shareable link</em> and paste it above.
              </li>
            </ol>
            <img
              src="/screenshots/google-calendar.png"
              alt="Google Calendar access permissions screen with public availability enabled"
            />
          {:else if activeTab === "outlook"}
            <ol>
              <li>
                Open Outlook on the web &raquo; <em>Settings</em> &raquo;
                <em>Calendar</em> &raquo; <em>Shared calendars</em>.
              </li>
              <li>
                Under <em>Publish a calendar</em>, choose your calendar and
                permission level, then click <em>Publish</em>.
              </li>
              <li>Copy the <em>ICS</em> link and paste it above.</li>
            </ol>
            <img
              src="/screenshots/outlook-calendar-publish.png"
              alt="Outlook Publish a calendar dialog with calendar and permission selectors"
            />
            <img
              src="/screenshots/outlook-calendar-link.png"
              alt="Outlook ICS link shown after publishing"
            />
          {/if}
        </div>
      </div>
    </details>
  {/if}
</div>

<style>
  .calendar-connect {
    margin: var(--sp-3) 0 var(--sp-4);
  }

  .cal-list {
    list-style: none;
    margin: 0 0 var(--sp-3) 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--sp-2, 0.25rem);
  }

  .cal-row {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    padding: var(--sp-3) var(--sp-4);
    background: var(--rt-gray-100, #f5f3ef);
    border-radius: var(--radius, 8px);
  }

  .cal-label {
    font-weight: 600;
  }

  .cal-provider {
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
  }

  .cal-remove {
    margin-left: auto;
    width: 28px;
    height: 28px;
    border: none;
    background: transparent;
    border-radius: 50%;
    cursor: pointer;
    font-size: 18px;
    line-height: 1;
    color: var(--rt-text-muted, #777);
  }

  .cal-remove:hover {
    background: var(--rt-gray-200, #e4dfda);
    color: var(--rt-danger-text, #b00020);
  }

  .cal-remove:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .empty-hint {
    color: var(--rt-text-muted, #777);
    font-size: var(--font-size-sm);
    margin: 0 0 var(--sp-3) 0;
  }

  .add-toggle {
    background: var(--rt-white, #fff);
    color: var(--rt-blue, #3a6db5);
    border: 1px solid var(--rt-blue, #3a6db5);
    border-radius: var(--radius, 8px);
    padding: var(--sp-3) var(--sp-4);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    min-height: var(--btn-h, 36px);
  }

  .add-toggle:hover {
    background: var(--rt-gray-100, #f5f3ef);
  }

  .connect-form {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) minmax(0, 1fr) auto;
    gap: var(--sp-3);
    align-items: end;
    margin-top: var(--sp-3);
  }

  .field {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .field-label {
    font-size: var(--font-size-xs);
    color: var(--rt-text-muted, #777);
    margin-bottom: 2px;
  }

  .field input {
    padding: var(--sp-3);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: 4px;
    font: inherit;
    min-height: 36px;
  }

  @media (max-width: 600px) {
    .connect-form {
      grid-template-columns: 1fr;
    }
  }

  .error-banner {
    background: var(--rt-danger-bg, #fdecea);
    color: var(--rt-danger-text, #b00020);
    border-radius: var(--radius, 8px);
    padding: var(--sp-3) var(--sp-4);
    margin-bottom: var(--sp-3);
    font-size: var(--font-size-sm);
  }

  .help {
    margin-top: var(--sp-4);
    border-top: 1px solid var(--rt-gray-200, #e4dfda);
    padding-top: var(--sp-3);
  }

  .help summary {
    cursor: pointer;
    font-weight: 600;
    font-size: var(--font-size-sm);
    color: var(--rt-text-light, #555);
  }

  .help-body {
    margin-top: var(--sp-3);
  }

  .tabs {
    display: flex;
    gap: 2px;
    border-bottom: 1px solid var(--rt-gray-200, #e4dfda);
    margin-bottom: var(--sp-3);
    overflow-x: auto;
  }

  .tab {
    background: none;
    border: none;
    padding: var(--sp-3) var(--sp-4);
    font: inherit;
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
  }

  .tab.active {
    color: var(--rt-blue, #3a6db5);
    border-bottom-color: var(--rt-blue, #3a6db5);
    font-weight: 600;
  }

  .tab-panel {
    font-size: var(--font-size-sm);
    line-height: 1.55;
    color: var(--rt-text-light, #555);
    max-height: 60vh;
    overflow-y: auto;
  }

  .tab-panel ol {
    padding-left: 1.25rem;
  }

  .tab-panel img {
    display: block;
    max-width: 100%;
    height: auto;
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: 4px;
    margin: var(--sp-3) 0;
  }

  .tab-panel code {
    background: var(--rt-gray-100, #f5f3ef);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 0.9em;
  }
</style>
