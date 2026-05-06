<svelte:head>
  <title>Reports - RT-AFF</title>
</svelte:head>

<div class="reports-page page-sm">
  <h1>Reports</h1>
  <p class="subtitle">Program dashboards, impact summaries, and funder reports.</p>

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
  .reports-page h1 {
    font-size: 2rem;
    margin-bottom: var(--spacing-xs);
  }

  .subtitle {
    color: var(--rt-text-light);
    margin-bottom: var(--spacing-lg);
  }

  .report-links {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .report-card {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    min-height: var(--btn-min-height);
  }

  .report-icon {
    font-size: 1.75rem;
    flex-shrink: 0;
  }

  .report-card h3 {
    margin: 0;
    font-size: var(--btn-font-size);
    color: var(--color-primary);
    font-family: var(--font-body);
    font-weight: 600;
  }

  .report-card p {
    margin: 2px 0 0 0;
    font-size: var(--font-size-sm);
    color: var(--rt-text-muted);
  }
</style>
