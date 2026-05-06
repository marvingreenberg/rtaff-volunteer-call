<script lang="ts">
  import { authState } from '$lib/stores/auth.svelte';

  const allNavCards = [
    { href: '/projects', label: 'Projects', icon: '\u{1F3E0}', description: 'Create and manage home repair projects from intake through completion.', minRole: 'team_leader' },
    { href: '/planning', label: 'Planning', icon: '\u{1F4CB}', description: 'Inventory management and volunteer call coordination.', minRole: 'team_leader' },
    { href: '/volunteering', label: 'Volunteering', icon: '\u{1F91D}', description: 'View open volunteer calls and your project assignments.', minRole: 'volunteer' },
    { href: '/volunteer-calls', label: 'Volunteer Calls', icon: '\u{1F465}', description: 'Create calls, assemble project teams, and track assignments.', minRole: 'team_leader' },
    { href: '/execution', label: 'Execution', icon: '\u{1F528}', description: 'Track repairs, materials, hours, and project completion.', minRole: 'team_leader' },
    { href: '/reports', label: 'Reports', icon: '\u{1F4CA}', description: 'Dashboard metrics, funder reports, and program impact.', minRole: 'staff' },
  ];

  function userCanSee(minRole: string, roles: string[]): boolean {
    if (minRole === 'volunteer') return true;
    if (minRole === 'team_leader') return roles.includes('staff') || roles.includes('team_leader');
    if (minRole === 'staff') return roles.includes('staff');
    return false;
  }

  let navCards = $derived(
    authState.user
      ? allNavCards.filter(c => userCanSee(c.minRole, authState.user!.roles))
      : []
  );
</script>

<svelte:head>
  <title>RT-AFF Home Repair Program</title>
</svelte:head>

<div class="home">
  <h1>Home Repair Program</h1>
  <p class="subtitle">Manage assessments, agreements, and volunteer coordination for home repair projects
    serving families, seniors, veterans, and people living with disabilities.</p>

  <div class="nav-grid">
    {#each navCards as card (card.href)}
      <a href={card.href} class="nav-card">
        <span class="card-icon">{card.icon}</span>
        <span class="card-label">{card.label}</span>
        <span class="card-desc">{card.description}</span>
      </a>
    {/each}
  </div>
</div>

<style>
  .home {
    max-width: 900px;
  }

  .home h1 {
    font-size: 2rem;
    margin-bottom: var(--spacing-xs);
  }

  .subtitle {
    font-size: var(--btn-font-size);
    color: var(--rt-text-light);
    margin-bottom: var(--spacing-lg);
  }

  .nav-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: var(--spacing-md);
  }

  .nav-card {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    padding: var(--spacing-lg);
    background: var(--rt-white, white);
    border: 1px solid var(--rt-gray-200, #e4dfda);
    border-radius: var(--card-radius, 8px);
    text-decoration: none;
    color: inherit;
    min-height: 120px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .nav-card:hover {
    border-color: var(--color-primary, #3a6db5);
    box-shadow: 0 2px 8px rgba(58, 109, 181, 0.1);
    text-decoration: none;
  }

  .card-icon {
    font-size: 1.75rem;
    line-height: 1;
  }

  .card-label {
    font-size: var(--btn-font-size);
    font-weight: 600;
    color: var(--color-primary, #3a6db5);
  }

  .card-desc {
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted, #777);
    line-height: 1.4;
  }

  @media (max-width: 600px) {
    .nav-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
