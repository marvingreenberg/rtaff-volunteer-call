<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import {
    people,
    type PersonResponse,
    type SkillCategory,
    type RoleType,
    type NotificationPreference,
    type NotificationDetailLevel,
    type SubscriptionStatus,
  } from '$lib/api/client';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';

  let person = $state<PersonResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);
  let saving = $state(false);
  let savedAt = $state<number | null>(null);

  let firstName = $state('');
  let lastName = $state('');
  let email = $state('');
  let phone = $state('');
  let skillCategory = $state<SkillCategory>('unknown');
  let active = $state(true);
  let notificationPreference = $state<NotificationPreference>('email');
  let notificationDetailLevel = $state<NotificationDetailLevel>('summary');
  let subscriptionStatus = $state<SubscriptionStatus>('active');
  let pauseEnd = $state('');
  let notes = $state('');
  let roles = $state<RoleType[]>([]);

  let personId = $derived(page.params.id!);

  const ROLES: { value: RoleType; label: string }[] = [
    { value: 'volunteer', label: 'Volunteer' },
    { value: 'team_leader', label: 'Team Leader' },
    { value: 'staff', label: 'Staff' },
  ];

  onMount(loadPerson);

  async function loadPerson() {
    loading = true;
    error = null;
    try {
      const p = await people.get(personId);
      person = p;
      firstName = p.first_name;
      lastName = p.last_name;
      email = p.email ?? '';
      phone = p.phone ?? '';
      skillCategory = p.skill_category;
      active = p.active;
      notificationPreference = p.notification_preference;
      notificationDetailLevel = p.notification_detail_level;
      subscriptionStatus = p.subscription_status;
      pauseEnd = p.pause_end ?? '';
      notes = p.notes ?? '';
      roles = [...p.roles];
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load person';
    } finally {
      loading = false;
    }
  }

  function toggleRole(role: RoleType) {
    if (roles.includes(role)) {
      roles = roles.filter((r) => r !== role);
    } else {
      roles = [...roles, role];
    }
  }

  let canSave = $derived(!!firstName.trim() && !!lastName.trim());

  async function handleSave() {
    if (!canSave || saving) return;
    saving = true;
    error = null;
    savedAt = null;
    try {
      const updated = await people.update(personId, {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        skill_category: skillCategory,
        active,
        notification_preference: notificationPreference,
        notification_detail_level: notificationDetailLevel,
        subscription_status: subscriptionStatus,
        pause_end: subscriptionStatus === 'paused' ? pauseEnd || null : null,
        notes: notes.trim() || undefined,
        roles,
      });
      person = updated;
      savedAt = Date.now();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>{person ? `${person.first_name} ${person.last_name}` : 'Person'} - RT-AFF</title>
</svelte:head>

<div class="person-page page-md">
  <Breadcrumb
    crumbs={[
      { label: 'People', href: '/people' },
      { label: person ? `${person.first_name} ${person.last_name}` : 'Person' },
    ]}
  />

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if loading}
    <p class="loading">Loading...</p>
  {:else if person}
    <div class="page-header">
      <h1>{person.first_name} {person.last_name}</h1>
      {#if savedAt}
        <span class="saved-flash" aria-live="polite">Saved</span>
      {/if}
    </div>

    <form
      class="card editor"
      onsubmit={(e) => {
        e.preventDefault();
        handleSave();
      }}
    >
      <div class="row">
        <span class="lbl">Name</span>
        <input type="text" bind:value={firstName} placeholder="First" required />
        <input type="text" bind:value={lastName} placeholder="Last" required />
      </div>

      <div class="row">
        <span class="lbl">Email</span>
        <input type="email" bind:value={email} class="grow" />
        <span class="lbl secondary">Phone</span>
        <input type="text" bind:value={phone} class="grow" />
        {#if person.phone_verified}
          <span class="verified-tag" title="Phone verified">verified</span>
        {/if}
      </div>

      <div class="row">
        <span class="lbl">Skill</span>
        <select bind:value={skillCategory}>
          <option value="unknown">Unknown</option>
          <option value="skilled">Skilled</option>
          <option value="unskilled">Unskilled</option>
        </select>
        <label class="checkbox-inline">
          <input type="checkbox" bind:checked={active} />
          Active
        </label>
      </div>

      <div class="row">
        <span class="lbl">Roles</span>
        {#each ROLES as role (role.value)}
          <label class="checkbox-inline">
            <input
              type="checkbox"
              checked={roles.includes(role.value)}
              onchange={() => toggleRole(role.value)}
            />
            {role.label}
          </label>
        {/each}
      </div>

      <hr class="divider" />

      <div class="row">
        <span class="lbl">Notify via</span>
        <select bind:value={notificationPreference}>
          <option value="email">Email</option>
          <option value="sms">SMS</option>
          <option value="both">Both</option>
        </select>
        <span class="lbl secondary">Detail</span>
        <select bind:value={notificationDetailLevel}>
          <option value="summary">Summary</option>
          <option value="full">Full</option>
        </select>
      </div>

      <div class="row">
        <span class="lbl">Subscription</span>
        <select bind:value={subscriptionStatus}>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="unsubscribed">Unsubscribed</option>
        </select>
        {#if subscriptionStatus === 'paused'}
          <span class="lbl secondary">Until</span>
          <input type="date" bind:value={pauseEnd} />
        {/if}
      </div>

      <div class="row align-top">
        <span class="lbl">Notes</span>
        <textarea bind:value={notes} rows="3" class="grow"></textarea>
      </div>

      <div class="form-actions">
        <a class="btn btn-secondary" href="/people">Back</a>
        <button type="submit" class="btn btn-primary" disabled={!canSave || saving}>
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </form>
  {/if}
</div>

<style>
  .page-header {
    display: flex;
    align-items: baseline;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .page-header h1 {
    margin: 0;
  }

  .saved-flash {
    color: var(--rt-success-text);
    font-size: var(--font-size-sm);
    font-weight: 500;
  }

  .editor {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .row.align-top {
    align-items: flex-start;
  }

  .lbl {
    width: 7em;
    flex-shrink: 0;
    font-weight: 500;
    font-size: var(--font-size-sm);
    color: var(--rt-gray-600);
  }

  .lbl.secondary {
    width: auto;
    margin-left: var(--spacing-sm);
  }

  .row input[type='text'],
  .row input[type='email'],
  .row input[type='date'],
  .row select,
  .row textarea {
    padding: var(--spacing-xs) var(--spacing-sm);
    min-height: 32px;
    border: 1px solid var(--rt-gray-200);
    border-radius: var(--card-radius);
    font-size: inherit;
    font-family: var(--font-body);
    background: var(--rt-white);
    color: var(--color-text);
    box-sizing: border-box;
  }

  .row input[type='text'],
  .row input[type='email'] {
    flex: 1;
    min-width: 8em;
  }

  .row input.grow,
  .row textarea.grow {
    flex: 1;
  }

  .row textarea {
    resize: vertical;
    min-height: 4.5em;
    padding: var(--spacing-sm);
  }

  .row input:focus,
  .row select:focus,
  .row textarea:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px rgba(58, 109, 181, 0.2);
  }

  .checkbox-inline {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: inherit;
    cursor: pointer;
    margin-right: var(--spacing-md);
  }

  .checkbox-inline input[type='checkbox'] {
    width: 16px;
    height: 16px;
    margin: 0;
  }

  .verified-tag {
    display: inline-block;
    padding: 1px 6px;
    background: var(--rt-success-bg);
    color: var(--rt-success-text);
    border-radius: 10px;
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .divider {
    border: none;
    border-top: 1px solid var(--rt-gray-200);
    margin: var(--spacing-sm) 0;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-md);
  }

  @media (max-width: 600px) {
    .lbl {
      width: 100%;
    }
    .row input[type='text'],
    .row input[type='email'] {
      flex: 1 1 100%;
    }
  }
</style>
