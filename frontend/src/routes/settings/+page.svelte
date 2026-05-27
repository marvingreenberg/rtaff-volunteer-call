<script lang="ts">
  import { onMount } from "svelte";
  import { authState, initFromToken } from "$lib/stores/auth.svelte";
  import {
    people,
    type CalendarKind,
    type SubscriptionStatus,
  } from "$lib/api/client";
  import CalendarConnectPanel from "$lib/components/CalendarConnectPanel.svelte";
  import Select from "$lib/components/Select.svelte";
  import {
    settingsState,
    applySettings,
    type Density,
  } from "$lib/stores/settings.svelte";

  function setDensity(d: Density) {
    settingsState.density = d;
    applySettings();
  }

  const densityOptions: { value: Density; label: string }[] = [
    { value: "large", label: "Large" },
    { value: "standard", label: "Standard" },
    { value: "compact", label: "Compact" },
  ];

  // Lives at /settings — the Avatar menu links here. Houses the
  // per-volunteer self-service knobs that previously only the staff
  // /people/[id] editor touched: notification kind/detail, pause, and
  // calendar connection. Staff editor is unchanged so admins can still
  // edit other volunteers from /people/[id].

  let loading = $state(true);
  let saving = $state(false);
  let error = $state("");
  let saved = $state(false);

  let notificationPreference = $state<"email" | "sms" | "both">("email");
  let notificationDetailLevel = $state<"summary" | "full">("full");
  let subscriptionStatus = $state<SubscriptionStatus>("active");
  let pauseEnd = $state("");
  let calendarKind = $state<CalendarKind>("google");

  onMount(async () => {
    await initFromToken(null);
    if (!authState.user) return;
    notificationPreference = authState.user.notification_preference;
    notificationDetailLevel = authState.user.notification_detail_level;
    subscriptionStatus = authState.user.subscription_status;
    pauseEnd = authState.user.pause_end ?? "";
    calendarKind = authState.user.calendar_kind;
    loading = false;
  });

  async function refreshUser() {
    await initFromToken(null);
  }

  async function save() {
    if (!authState.user) return;
    saving = true;
    saved = false;
    error = "";
    try {
      await people.update(authState.user.id, {
        notification_preference: notificationPreference,
        notification_detail_level: notificationDetailLevel,
        subscription_status: subscriptionStatus,
        pause_end:
          subscriptionStatus === "paused" ? pauseEnd || null : null,
        calendar_kind: calendarKind,
      });
      await refreshUser();
      saved = true;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to save";
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Settings — RT-AFF</title>
</svelte:head>

<div class="page-md">
  <h1>Settings</h1>

  {#if loading}
    <p class="loading-text">Loading…</p>
  {:else if !authState.user}
    <p class="empty-text">Sign in to manage settings.</p>
  {:else}
    {#if error}
      <div class="alert alert-error">{error}</div>
    {/if}
    {#if saved}
      <div class="saved-flash">Saved.</div>
    {/if}

    <section class="card">
      <h2>Notifications</h2>
      <div class="row">
        <span class="lbl">Notify via</span>
        <Select
          bind:value={notificationPreference}
          options={[
            { value: "email", label: "Email" },
            { value: "sms", label: "SMS" },
            { value: "both", label: "Both" },
          ]}
          ariaLabel="Notification channel"
        />
        <span class="lbl secondary">Detail</span>
        <Select
          bind:value={notificationDetailLevel}
          options={[
            { value: "summary", label: "Summary" },
            { value: "full", label: "Full" },
          ]}
          ariaLabel="Notification detail level"
        />
      </div>
    </section>

    <section class="card">
      <h2>Pause</h2>
      <p class="hint">
        Pause to suppress notifications and skip the next call's invite.
        Resume manually, or set a pause-until date to auto-resume.
      </p>
      <div class="row">
        <span class="lbl">Status</span>
        <Select
          bind:value={subscriptionStatus}
          options={[
            { value: "active", label: "Active" },
            { value: "paused", label: "Paused" },
            { value: "unsubscribed", label: "Unsubscribed" },
          ]}
          ariaLabel="Subscription status"
        />
        {#if subscriptionStatus === "paused"}
          <span class="lbl secondary">Until</span>
          <input type="date" bind:value={pauseEnd} />
        {/if}
      </div>
    </section>

    <section class="card">
      <h2>Calendar</h2>
      <div class="row">
        <span class="lbl">Calendar sync</span>
        <Select
          bind:value={calendarKind}
          options={[
            { value: "google", label: "Google Calendar" },
            { value: "apple", label: "Apple Calendar" },
            { value: "outlook", label: "Outlook" },
            { value: "other", label: "Other / .ics download" },
          ]}
          ariaLabel="Preferred calendar app"
        />
      </div>
      <p class="hint">
        Chooses which app opens when you click <em>Add to Calendar</em> on
        an assignment. Apple Calendar has no one-click web action — the
        button downloads an .ics file you double-click to add.
      </p>

      <CalendarConnectPanel
        personId={authState.user.id}
        calendars={authState.user.calendars}
        onChanged={refreshUser}
      />
    </section>

    <section class="card">
      <h2>Display</h2>
      <p class="hint">
        Density controls overall padding and row heights in lists. Saved on
        this device.
      </p>
      <div class="density-options" role="radiogroup" aria-label="Display density">
        {#each densityOptions as opt (opt.value)}
          <label
            class="density-option"
            class:selected={settingsState.density === opt.value}
          >
            <input
              type="radio"
              name="density"
              value={opt.value}
              checked={settingsState.density === opt.value}
              onchange={() => setDensity(opt.value)}
            />
            {opt.label}
          </label>
        {/each}
      </div>
    </section>

    <div class="actions">
      <button class="btn btn-primary" onclick={save} disabled={saving}>
        {saving ? "Saving…" : "Save changes"}
      </button>
    </div>
  {/if}
</div>

<style>
  .card {
    background: var(--rt-white, #fff);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .card h2 {
    font-size: 1rem;
    margin: 0 0 var(--spacing-sm) 0;
    color: var(--color-primary, #3a6db5);
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .lbl {
    width: 7em;
    font-weight: 500;
    font-size: var(--font-size-sm);
    color: var(--rt-gray-600, #555);
  }

  .lbl.secondary {
    width: auto;
  }

  .hint {
    color: var(--rt-text-muted, #777);
    font-size: var(--font-size-sm);
    margin: 0 0 var(--spacing-sm) 0;
  }

  .actions {
    margin-top: var(--spacing-md);
  }

  .saved-flash {
    color: var(--rt-success-text);
    font-weight: 500;
    margin-bottom: var(--spacing-sm);
  }

  .loading-text,
  .empty-text {
    color: var(--rt-text-muted, #777);
    font-style: italic;
  }

  .density-options {
    display: inline-flex;
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
    overflow: hidden;
  }

  .density-option {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: var(--font-size-sm);
    font-weight: 500;
    cursor: pointer;
    border-right: 1px solid var(--rt-gray-200, #e4dfda);
    background: transparent;
    color: var(--rt-text, #222);
    min-height: var(--btn-min-height, 36px);
    user-select: none;
  }

  .density-option:last-child {
    border-right: none;
  }

  .density-option.selected {
    background: var(--color-primary, #3a6db5);
    color: #fff;
  }

  .density-option input {
    /* Visually hidden — the label is the affordance. */
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
  }
</style>
