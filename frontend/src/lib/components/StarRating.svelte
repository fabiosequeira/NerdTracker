<script lang="ts">
	// 5 stars in half-star steps (stored as 0.5 .. 5). Read-only by default; `editable` makes every half
	// clickable, and clicking the current value again clears the rating (emits `change` with null).
	import { createEventDispatcher } from 'svelte';

	export let value: number | null | undefined = null;
	export let editable = false;
	export let size = 'text-xl';
	export let disabled = false;

	const dispatch = createEventDispatcher<{ change: number | null }>();
	let hover: number | null = null;

	$: shown = hover ?? value ?? 0;

	function pick(v: number) {
		if (!editable || disabled) return;
		dispatch('change', v === value ? null : v);
	}
</script>

<div
	class="inline-flex items-center {size}"
	role={editable ? 'radiogroup' : 'img'}
	aria-label={value ? `Rated ${value} out of 5` : 'Not rated'}
	on:mouseleave={() => (hover = null)}
>
	{#each [0, 1, 2, 3, 4] as i}
		<span class="relative inline-block leading-none select-none">
			<span class="text-gray-600">★</span>
			<span
				class="absolute inset-y-0 left-0 overflow-hidden text-yellow-400 whitespace-nowrap"
				style="width: {Math.max(0, Math.min(1, shown - i)) * 100}%">★</span
			>
			{#if editable}
				<button
					type="button"
					class="absolute inset-y-0 left-0 w-1/2 cursor-pointer disabled:cursor-default"
					aria-label="Rate {i + 0.5} stars"
					{disabled}
					on:mouseenter={() => (hover = i + 0.5)}
					on:click={() => pick(i + 0.5)}
				></button>
				<button
					type="button"
					class="absolute inset-y-0 right-0 w-1/2 cursor-pointer disabled:cursor-default"
					aria-label="Rate {i + 1} stars"
					{disabled}
					on:mouseenter={() => (hover = i + 1)}
					on:click={() => pick(i + 1)}
				></button>
			{/if}
		</span>
	{/each}
</div>
