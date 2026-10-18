<script lang="ts">
	// Cover with a graceful fallback: missing URL *or* a broken/blocked image shows a styled placeholder
	// instead of a broken-image icon.
	export let src: string | null | undefined = null;
	export let alt = '';
	export let kind: 'book' | 'audiobook' = 'book';
	export let title = '';
	export let eager = false;

	let failed = false;
	let lastSrc: string | null | undefined = undefined;
	$: if (src !== lastSrc) {
		lastSrc = src;
		failed = false;
	}

	// audiobook covers are square, book covers are portrait: keep each uncropped
	$: shape = kind === 'audiobook' ? 'aspect-square' : 'aspect-[2/3]';
</script>

{#if src && !failed}
	<img
		{src}
		{alt}
		loading={eager ? 'eager' : 'lazy'}
		decoding="async"
		referrerpolicy="no-referrer"
		on:error={() => (failed = true)}
		class="w-full {shape} object-cover bg-gray-700"
	/>
{:else}
	<div
		role="img"
		aria-label={alt || title || 'No cover available'}
		class="w-full {shape} flex flex-col items-center justify-center gap-2 p-3 text-center bg-gradient-to-br from-gray-700 to-gray-900 text-gray-400"
	>
		<span class="text-4xl" aria-hidden="true">{kind === 'audiobook' ? '🎧' : '📖'}</span>
		{#if title}<span class="text-xs line-clamp-4 text-gray-300">{title}</span>{/if}
	</div>
{/if}
