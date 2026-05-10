<script lang="ts">
  import { people } from "$lib/api/client";

  type Props = {
    personId: string;
    calendarConnected: boolean;
    calendarProvider: string | null;
    onChanged: () => void | Promise<void>;
  };

  let { personId, calendarConnected, calendarProvider, onChanged }: Props =
    $props();

  let expanded = $state(false);
  let urlInput = $state("");
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

  function toggle() {
    expanded = !expanded;
    if (!expanded) {
      // Reset transient state so the next open is clean.
      errorMsg = "";
    }
  }

  async function handleConnect(e: SubmitEvent) {
    e.preventDefault();
    const url = urlInput.trim();
    if (!url) return;
    saving = true;
    errorMsg = "";
    try {
      await people.connectCalendar(personId, {
        calendar_url: url,
        calendar_provider: providerInput.trim() || null,
      });
      urlInput = "";
      providerInput = "";
      expanded = false;
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

  async function handleDisconnect() {
    if (!confirm("Disconnect calendar? Conflict warnings will stop appearing."))
      return;
    saving = true;
    errorMsg = "";
    try {
      await people.disconnectCalendar(personId);
      expanded = false;
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

  let buttonLabel = $derived(
    calendarConnected
      ? `Calendar connected · ${calendarProvider || "iCal"}`
      : "Connect Calendar",
  );
</script>

<div class="calendar-connect">
  <button
    type="button"
    class="connect-btn"
    class:connected={calendarConnected}
    title="Connect your calendar to make volunteering simpler"
    aria-expanded={expanded}
    onclick={toggle}
  >
    {buttonLabel}
  </button>

  {#if expanded}
    <div class="panel" role="region" aria-label="Connect calendar">
      {#if errorMsg}
        <div class="error-banner" role="alert">{errorMsg}</div>
      {/if}

      {#if calendarConnected}
        <p class="connected-status">
          Your calendar is connected{calendarProvider
            ? ` (${calendarProvider})`
            : ""}. We use it only to flag conflicts with your assignments.
        </p>
        <button
          type="button"
          class="btn btn-secondary"
          onclick={handleDisconnect}
          disabled={saving}
        >
          {saving ? "Working..." : "Disconnect calendar"}
        </button>
      {:else}
        <form onsubmit={handleConnect} class="connect-form">
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
          <label class="field provider-field">
            <span class="field-label">Provider (optional)</span>
            <input
              type="text"
              bind:value={providerInput}
              placeholder="Google, Apple, Outlook..."
              autocomplete="off"
            />
          </label>
          <button
            type="submit"
            class="btn btn-primary"
            disabled={saving || !urlInput.trim()}
          >
            {saving ? "Connecting..." : "Connect"}
          </button>
        </form>
        <p class="hint">
          Calendar URLs are kept secret and used only to flag conflicts with
          your assignments. You can only connect one calendar.
        </p>
      {/if}

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
                A "calendar URL" is a private subscription link that lets us
                read the busy/free times on your calendar. You publish it once
                from your calendar app, paste the URL here, and we'll flag any
                volunteer task that overlaps an existing event.
              </p>
              <p>
                Treat the URL as a secret &mdash; anyone with it could read
                your calendar. We never display it back to you and never share
                it.
              </p>
              <p>
                If something looks wrong after connecting, double-check that
                the URL ends in <code>.ics</code> or is a
                <code>webcal://</code> link (we'll fetch it the same way).
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
    </div>
  {/if}
</div>

<style>
  .calendar-connect {
    margin: var(--spacing-sm) 0 var(--spacing-md);
  }

  .connect-btn {
    background: var(--rt-white, #fff);
    color: var(--color-primary, #3a6db5);
    border: 1px solid var(--color-primary, #3a6db5);
    border-radius: var(--card-radius, 8px);
    padding: var(--spacing-sm) var(--spacing-md);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    min-height: var(--btn-min-height, 40px);
  }

  .connect-btn.connected {
    background: var(--rt-success-bg, #e6f4ea);
    border-color: var(--rt-success-text, #2f7a45);
    color: var(--rt-success-text, #2f7a45);
  }

  .connect-btn:hover {
    background: var(--rt-gray-100, #f5f3ef);
  }

  .panel {
    margin-top: var(--spacing-sm);
    padding: var(--spacing-md);
    background: var(--rt-white, #fff);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
  }

  .connected-status {
    margin: 0 0 var(--spacing-md) 0;
  }

  .connect-form {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) auto;
    gap: var(--spacing-sm);
    align-items: end;
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
    padding: var(--spacing-sm);
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

  .hint {
    margin: var(--spacing-sm) 0 0;
    font-size: var(--font-size-xs);
    color: var(--rt-text-muted, #777);
  }

  .error-banner {
    background: var(--rt-danger-bg, #fdecea);
    color: var(--rt-danger-text, #b00020);
    border-radius: var(--card-radius, 8px);
    padding: var(--spacing-sm) var(--spacing-md);
    margin-bottom: var(--spacing-sm);
    font-size: var(--font-size-sm);
  }

  .help {
    margin-top: var(--spacing-md);
    border-top: 1px solid var(--rt-gray-200, #e4dfda);
    padding-top: var(--spacing-sm);
  }

  .help summary {
    cursor: pointer;
    font-weight: 600;
    font-size: var(--font-size-sm);
    color: var(--rt-text-light, #555);
  }

  .help-body {
    margin-top: var(--spacing-sm);
  }

  .tabs {
    display: flex;
    gap: 2px;
    border-bottom: 1px solid var(--rt-gray-200, #e4dfda);
    margin-bottom: var(--spacing-sm);
    overflow-x: auto;
  }

  .tab {
    background: none;
    border: none;
    padding: var(--spacing-sm) var(--spacing-md);
    font: inherit;
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
  }

  .tab.active {
    color: var(--color-primary, #3a6db5);
    border-bottom-color: var(--color-primary, #3a6db5);
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
    margin: var(--spacing-sm) 0;
  }

  .tab-panel code {
    background: var(--rt-gray-100, #f5f3ef);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 0.9em;
  }
</style>
