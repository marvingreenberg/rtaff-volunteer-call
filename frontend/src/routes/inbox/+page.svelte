<script lang="ts">
    import { notifications } from '$lib/api/client';
    import type { NotificationResponse } from '$lib/api/types';
    import { goto } from '$app/navigation';
    import Breadcrumb from '$lib/components/Breadcrumb.svelte';

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

    <h1>Inbox</h1>

    {#if loading}
        <p>Loading...</p>
    {:else if error}
        <p class="error-text">{error}</p>
    {:else if items.length === 0}
        <p class="text-muted">No notifications</p>
    {:else}
        <div class="notification-list">
            {#each items as item (item.id)}
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
            {/each}
        </div>
    {/if}
</div>

<style>
    .notification-list {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .notification-row {
        display: block;
        width: 100%;
        text-align: left;
        background: var(--rt-white);
        border: 1px solid var(--rt-gray-200);
        border-radius: var(--card-radius);
        padding: var(--spacing-sm) var(--spacing-md);
        cursor: pointer;
        transition: background 0.15s;
    }
    .notification-row:hover {
        background: var(--rt-bg-subtle);
    }
    .notification-row.unread {
        border-left: 3px solid var(--rt-blue);
        font-weight: 600;
    }
    .notif-subject {
        font-size: var(--btn-font-size);
    }
    .notif-meta {
        display: flex;
        gap: var(--spacing-sm);
        align-items: center;
        margin-top: var(--spacing-xs);
        font-size: var(--font-size-sm);
        color: var(--rt-text-muted);
    }
    .notif-type {
        text-transform: capitalize;
        font-size: var(--font-size-xs);
        padding: var(--spacing-xs) var(--spacing-sm);
        border-radius: var(--card-radius);
        background: var(--rt-gray-100);
    }
    .notif-body {
        padding: var(--spacing-sm) var(--spacing-md);
        background: var(--rt-bg-subtle);
        border: 1px solid var(--rt-gray-200);
        border-top: none;
        border-radius: 0 0 var(--card-radius) var(--card-radius);
        white-space: pre-line;
        font-size: var(--font-size-sm);
        color: var(--rt-text-light);
    }
</style>
