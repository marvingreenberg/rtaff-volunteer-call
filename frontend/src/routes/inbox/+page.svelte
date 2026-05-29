<script lang="ts">
    import { notifications } from '$lib/api/client';
    import type { NotificationResponse } from '$lib/api/types';
    import { goto } from '$app/navigation';
    import Breadcrumb from '$lib/components/Breadcrumb.svelte';
    import PageHeader from '$lib/components/PageHeader.svelte';

    let items: NotificationResponse[] = $state([]);
    let loading = $state(true);
    let error = $state('');
    let expandedId: string | null = $state(null);

    async function load() {
        loading = true;
        try {
            items = await notifications.list();
        } catch (e: unknown) {
            error = e instanceof Error && e.message || 'Failed to load';
        } finally {
            loading = false;
        }
    }

    async function openNotification(item: NotificationResponse) {
        if (!item.read) {
            await notifications.markRead(item.id);
            item.read = true;
        }
        if (item.link) {
            goto(item.link);
        } else {
            expandedId = expandedId === item.id ? null : item.id;
        }
    }

    function timeAgo(dateStr: string): string {
        const diff = Date.now() - new Date(dateStr).getTime();
        const minutes = Math.floor(diff / 60000);
        if (minutes < 1) return 'just now';
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }

    $effect(() => {
        load();
    });
</script>

<div class="page-md">
    <Breadcrumb crumbs={[{ label: 'Inbox' }]} />

    <PageHeader title="Inbox" />

    {#if loading}
        <p>Loading...</p>
    {:else if error}
        <p class="error-text">{error}</p>
    {:else if items.length === 0}
        <p class="text-muted">No notifications</p>
    {:else}
        <ul class="inbox-list">
            {#each items as item (item.id)}
                <li>
                    <button
                        class="notification-row"
                        class:unread={!item.read}
                        onclick={() => openNotification(item)}
                    >
                        <div class="notif-subject">
                            {item.subject}
                        </div>
                        <div class="notif-meta">
                            <span class="notif-type">{item.type.replace('_', ' ')}</span>
                            <span class="notif-time">{timeAgo(item.created_at)}</span>
                        </div>
                    </button>
                    {#if expandedId === item.id && !item.link}
                        <div class="notif-body">
                            {item.body}
                        </div>
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    .inbox-list {
        list-style: none;
        padding: 0;
        margin: 0;
        background: var(--surface-1);
        border: 1px solid var(--hairline);
        border-radius: var(--radius);
        overflow: hidden;
    }
    .notification-row {
        display: block;
        width: 100%;
        text-align: left;
        background: transparent;
        border: 0;
        border-top: 1px solid var(--hairline);
        padding: var(--sp-3) var(--card-pad-x);
        cursor: pointer;
        transition: background 0.15s;
        color: inherit;
        font-family: inherit;
    }
    .inbox-list li:first-child .notification-row {
        border-top: 0;
    }
    .notification-row:hover {
        background: var(--surface-2);
    }
    .notification-row.unread {
        border-left: 3px solid var(--rt-blue);
        font-weight: 600;
    }
    .notif-subject {
        font-size: var(--fz-body);
    }
    .notif-meta {
        display: flex;
        gap: var(--sp-3);
        align-items: center;
        margin-top: var(--sp-2);
        font-size: var(--font-size-sm);
        color: var(--rt-text-muted);
    }
    .notif-type {
        text-transform: capitalize;
        font-size: var(--font-size-xs);
        padding: 2px var(--sp-3);
        border-radius: 999px;
        background: var(--surface-3);
    }
    .notif-body {
        padding: var(--sp-3) var(--card-pad-x);
        background: var(--surface-2);
        border-top: 1px solid var(--hairline);
        white-space: pre-line;
        font-size: var(--font-size-sm);
        color: var(--rt-text-muted);
    }
</style>
