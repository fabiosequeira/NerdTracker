<script lang="ts">
	// Collection card for Books and Audiobooks. Same outer container as the other media cards so the
	// grid looks uniform; the content emphasises cover, title, author (+ narrator & runtime for audio).
	import { createEventDispatcher } from 'svelte';
	import CoverImage from '$lib/components/CoverImage.svelte';
	import StarRating from '$lib/components/StarRating.svelte';
	import { formatRuntime, itemYear, peopleLine, recordingLabel, seriesLabel } from '$lib/media';

	export let item: any;
	export let kind: 'book' | 'audiobook' = 'book';

	const dispatch = createEventDispatcher<{ delete: void }>();

	$: base = kind === 'book' ? 'books' : 'audiobooks';
	$: href = `/${base}/${item._id}`;
	$: year = itemYear(item);
	$: authors = peopleLine(item.authors, 2);
	$: narrators = peopleLine(item.narrators, 2);
	$: runtime = formatRuntime(item.runtime_minutes);
	$: series = seriesLabel(item.series);
	$: abridged = item.recording_type === 'abridged';
</script>

<div
	class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group"
>
	<a {href} aria-label={item.title}>
		<CoverImage src={item.cover} alt={item.title} {kind} title={item.title} />
	</a>
	<div class="p-4 space-y-1">
		<a {href} class="block font-bold text-lg leading-snug line-clamp-2 group-hover:text-blue-400">{item.title}</a>
		{#if item.subtitle}<p class="text-xs text-gray-500 line-clamp-1">{item.subtitle}</p>{/if}
		{#if authors}<p class="text-sm text-gray-300 line-clamp-2">✍️ {authors}</p>{/if}

		{#if kind === 'audiobook'}
			{#if narrators}<p class="text-sm text-gray-300 line-clamp-1">🎙️ {narrators}</p>{/if}
			{#if runtime}<p class="text-sm text-gray-400">⏱️ {runtime}</p>{/if}
		{:else if item.page_count}
			<p class="text-sm text-gray-400">📄 {item.page_count} pages</p>
		{/if}

		{#if year}<p class="text-sm text-gray-400">📆 {year}</p>{/if}
		{#if series}<p class="text-xs text-blue-300 line-clamp-1">📚 {series}</p>{/if}
		{#if item.personal_rating}<StarRating value={item.personal_rating} size="text-base" />{/if}

		<div class="flex flex-wrap gap-1 mt-1">
			{#if kind === 'audiobook' && item.recording_type}
				<span class="px-2 py-0.5 rounded text-xs {abridged ? 'bg-amber-600/80' : 'bg-emerald-700/80'}">{recordingLabel(item.recording_type)}</span>
			{/if}
			{#each (item.genres ?? []).slice(0, 2) as g}
				<span class="bg-blue-600/80 px-2 py-0.5 rounded text-xs">{g}</span>
			{/each}
		</div>
	</div>
	<button
		class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
		on:click={() => dispatch('delete')}>Delete</button
	>
</div>
