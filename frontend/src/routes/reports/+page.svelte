<script lang="ts">
  import PageHeader from '$lib/components/PageHeader.svelte';
</script>

<svelte:head>
  <title>Reports - RT-AFF</title>
</svelte:head>

<div class="page-sm">
  <PageHeader title="Reports">
    {#snippet meta()}
      Program dashboards, impact summaries, and funder reports.
    {/snippet}
  </PageHeader>

  <div class="report-links">
    <a href="/reports/dashboard" class="section-card report-card">
      <span class="report-icon">&#128202;</span>
      <div>
        <h3>Program Dashboard</h3>
        <p>Project pipeline, impact stats, and program breakdowns</p>
      </div>
    </a>

    <a href="/reports/funders" class="section-card report-card">
      <span class="report-icon">&#128176;</span>
      <div>
        <h3>Funder Reports</h3>
        <p>Per-funding-source project counts, repairs, and costs</p>
      </div>
    </a>

    <a href="/reports/homeowners" class="section-card report-card">
      <span class="report-icon">&#127968;</span>
      <div>
        <h3>Homeowner Directory</h3>
        <p>View and edit homeowner contact information</p>
      </div>
    </a>
  </div>
</div>

<style>
  .report-links {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
  }

  .report-card {
    display: flex;
    align-items: center;
    gap: var(--sp-4);
  }

  .report-icon {
    font-size: 1.75rem;
    flex-shrink: 0;
  }

  .report-card h3 {
    margin: 0;
    font-size: var(--fz-body);
    color: var(--rt-blue);
    font-family: var(--font-body);
    font-weight: 600;
  }

  .report-card p {
    margin: 2px 0 0 0;
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
  }
</style>
