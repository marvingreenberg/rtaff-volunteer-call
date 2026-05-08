<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { authState } from '$lib/stores/auth.svelte';

  onMount(() => {
    if (!authState.user) {
      goto('/login');
      return;
    }
    const roles = authState.user.roles;
    const isVolunteerOnly = roles.length === 1 && roles[0] === 'volunteer';
    goto(isVolunteerOnly ? '/volunteering' : '/volunteer-calls');
  });
</script>

<svelte:head>
  <title>RT-AFF Volunteer Call</title>
</svelte:head>
