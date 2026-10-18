<script lang="ts">
	import CatalogDetail from '$lib/components/CatalogDetail.svelte';

	export let data: any;
</script>

{#key data.item?._id}
	<CatalogDetail item={data.item} kind="audiobook" />
{/key}
