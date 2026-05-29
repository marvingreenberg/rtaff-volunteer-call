<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import {
    people,
    type PersonResponse,
    type Skill,
    type Program,
    type RoleType,
    type NotificationPreference,
    type NotificationDetailLevel,
    type SubscriptionStatus,
  } from '$lib/api/client';
  import { ALL_PROGRAMS, ALL_SKILLS, PROGRAM_LABELS } from '$lib/api/types';
  import { authState } from '$lib/stores/auth.svelte';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import Select from '$lib/components/Select.svelte';
  import { skillLabel } from '$lib/utils/badges';

  let person = $state<PersonResponse | null>(null);
  let loading = $state(true);
  let error: string | null = $state(null);
  let saving = $state(false);
  let savedAt = $state<number | null>(null);

  let firstName = $state('');
  let lastName = $state('');
  let email = $state('');
  let phone = $state('');
  let skills = $state<Skill[]>([]);
  let programs = $state<Program[]>([]);
  let active = $state(true);
  let notificationPreference = $state<NotificationPreference>('email');
  let notificationDetailLevel = $state<NotificationDetailLevel>('summary');
  let subscriptionStatus = $state<SubscriptionStatus>('active');
  let pauseEnd = $state('');
  let notes = $state('');
  let roles = $state<RoleType[]>([]);

  let personId = $derived(page.params.id!);
  let isStaff = $derived(authState.user?.roles.includes('staff') ?? false);

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
      skills = [...p.skills];
      programs = p.programs.filter(m => m.active).map(m => m.program);
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

  function toggleSkill(skill: Skill) {
    if (skills.includes(skill)) {
      skills = skills.filter((s) => s !== skill);
    } else {
      skills = [...skills, skill];
    }
  }

  function toggleProgram(program: Program) {
    if (programs.includes(program)) {
      programs = programs.filter((p) => p !== program);
    } else {
      programs = [...programs, program];
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
        skills,
        active,
        notification_preference: notificationPreference,
        notification_detail_level: notificationDetailLevel,
        subscription_status: subscriptionStatus,
        pause_end: subscriptionStatus === 'paused' ? pauseEnd || null : null,
        notes: notes.trim() || undefined,
        roles,
        // Programs are staff-managed; non-staff editing themselves don't
        // get to silently grant themselves new program memberships.
        ...(isStaff ? { programs } : {}),
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
    <PageHeader title={`${person.first_name} ${person.last_name}`}>
      {#snippet meta()}
        {#if savedAt}
          <span class="saved-flash" aria-live="polite">Saved</span>
        {/if}
      {/snippet}
    </PageHeader>

    <form
      class="editor"
      onsubmit={(e) => {
        e.preventDefault();
        handleSave();
      }}
    >
      <section class="card">
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
      </section>

      <section class="card">
        <div class="row">
          <span class="lbl">Skills</span>
          {#each ALL_SKILLS as skill (skill)}
            <label class="checkbox-inline">
              <input
                type="checkbox"
                checked={skills.includes(skill)}
                onchange={() => toggleSkill(skill)}
              />
              {skillLabel(skill)}
            </label>
          {/each}
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

        {#if isStaff}
          <div class="row">
            <span class="lbl">Programs</span>
            {#each ALL_PROGRAMS as p (p)}
              <label class="checkbox-inline">
                <input
                  type="checkbox"
                  checked={programs.includes(p)}
                  onchange={() => toggleProgram(p)}
                />
                {PROGRAM_LABELS[p]}
              </label>
            {/each}
          </div>
        {/if}
      </section>

      <section class="card">
        <div class="row">
          <span class="lbl">Notify via</span>
          <Select
            bind:value={notificationPreference}
            options={[
              { value: 'email', label: 'Email' },
              { value: 'sms', label: 'SMS' },
              { value: 'both', label: 'Both' },
            ]}
            ariaLabel="Notification channel"
          />
          <span class="lbl secondary">Detail</span>
          <Select
            bind:value={notificationDetailLevel}
            options={[
              { value: 'summary', label: 'Summary' },
              { value: 'full', label: 'Full' },
            ]}
            ariaLabel="Notification detail level"
          />
        </div>

        <div class="row">
          <span class="lbl">Subscription</span>
          <Select
            bind:value={subscriptionStatus}
            options={[
              { value: 'active', label: 'Active' },
              { value: 'paused', label: 'Paused' },
              { value: 'unsubscribed', label: 'Unsubscribed' },
            ]}
            ariaLabel="Subscription status"
          />
          {#if subscriptionStatus === 'paused'}
            <span class="lbl secondary">Until</span>
            <input type="date" bind:value={pauseEnd} />
          {/if}
        </div>
      </section>

      <section class="card">
        <div class="row align-top">
          <span class="lbl">Notes</span>
          <textarea bind:value={notes} rows="3" class="grow"></textarea>
        </div>
      </section>

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
  .saved-flash {
    color: var(--rt-success-text);
    font-size: var(--font-size-sm);
    font-weight: 600;
  }

  .editor {
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    flex-wrap: wrap;
  }

  .row + .row {
    margin-top: var(--sp-3);
  }

  .row.align-top {
    align-items: flex-start;
  }

  .lbl {
    width: 7em;
    flex-shrink: 0;
    font-weight: 600;
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
  }

  .lbl.secondary {
    width: auto;
    margin-left: var(--sp-3);
  }

  .row input[type='text'],
  .row input[type='email'],
  .row input[type='date'],
  .row textarea {
    padding: 0 var(--sp-4);
    min-height: var(--btn-h);
    border: 1px solid var(--rt-input-border);
    border-radius: var(--radius-sm);
    background: var(--rt-input-bg);
    color: var(--color-text);
    font-size: var(--fz-body);
    font-family: var(--font-body);
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
    padding: var(--sp-3) var(--sp-4);
  }

  .row input:focus,
  .row textarea:focus {
    outline: none;
    border-color: var(--rt-blue);
    box-shadow: 0 0 0 3px rgba(58, 109, 181, 0.18);
  }

  .checkbox-inline {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-2);
    font-size: inherit;
    cursor: pointer;
    margin-right: var(--sp-4);
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

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--sp-3);
    margin-top: var(--sp-3);
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
