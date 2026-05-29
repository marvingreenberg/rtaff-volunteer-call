<script lang="ts">
  import { onMount } from "svelte";
  import { authState, initFromToken } from "$lib/stores/auth.svelte";
  import {
    people,
    type CalendarKind,
    type SubscriptionStatus,
  } from "$lib/api/client";
  import CalendarConnectPanel from "$lib/components/CalendarConnectPanel.svelte";
  import PageHeader from "$lib/components/PageHeader.svelte";
  import Select from "$lib/components/Select.svelte";

  // Lives at /settings — the Avatar menu links here. Houses the
  // per-volunteer self-service knobs that previously only the staff
  // /people/[id] editor touched: notification kind/detail, pause, and
  // calendar connection. Staff editor is unchanged so admins can still
  // edit other volunteers from /people/[id].
  //
  // Density is no longer configured here — the AvatarMenu (top-right)
  // owns it as the single source of truth.

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
  <PageHeader title="Settings" />

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

    <div class="actions">
      <button class="btn btn-primary" onclick={save} disabled={saving}>
        {saving ? "Saving…" : "Save changes"}
      </button>
    </div>
  {/if}
</div>

<style>
  section.card + section.card,
  section.card {
    margin-bottom: var(--sp-4);
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--sp-3);
  }

  .lbl {
    width: 7em;
    font-weight: 500;
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
  }

  .lbl.secondary {
    width: auto;
  }

  .hint {
    color: var(--rt-text-muted);
    font-size: var(--font-size-sm);
    margin: 0 0 var(--sp-3) 0;
  }

  .actions {
    margin-top: var(--sp-4);
  }

  .saved-flash {
    color: var(--rt-success-text);
    font-weight: 500;
    margin-bottom: var(--sp-3);
  }

  .loading-text,
  .empty-text {
    color: var(--rt-text-muted);
    font-style: italic;
  }
</style>
