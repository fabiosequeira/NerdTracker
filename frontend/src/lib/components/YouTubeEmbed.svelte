<script lang="ts">
	// Click-to-load YouTube player. A real <iframe> pulls ~1 MB of YouTube JS *per video* the moment
	// it renders; the Videos tab used to mount up to 6 of them at once. Show the thumbnail instead
	// and only create the iframe when the user hits play.
	export let id: string;
	export let title = 'Video';

	let playing = false;
</script>

{#if playing}
	<iframe
		width="100%"
		height="100%"
		src={`https://www.youtube.com/embed/${id}?autoplay=1`}
		frameborder="0"
		allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
		allowfullscreen
		{title}
	></iframe>
{:else}
	<button
		type="button"
		class="group relative block h-full w-full bg-black"
		aria-label={`Play ${title}`}
		on:click={() => (playing = true)}
	>
		<img
			src={`https://i.ytimg.com/vi/${id}/hqdefault.jpg`}
			alt=""
			loading="lazy"
			decoding="async"
			class="h-full w-full object-cover opacity-90 transition group-hover:opacity-100"
		/>
		<span class="absolute inset-0 flex items-center justify-center">
			<span
				class="flex h-14 w-14 items-center justify-center rounded-full bg-red-600 pl-1 text-2xl text-white shadow-lg"
				>▶</span
			>
		</span>
	</button>
{/if}
