import { loadItem } from '$lib/api';
import type { PageLoad } from './$types';

// Client-side only (the page is empty until this fetch lands). As a `load` function SvelteKit starts it on
// link hover/touch (data-sveltekit-preload-data="hover"), so the page opens with its data ready.
export const ssr = false;

export const load: PageLoad = async ({ fetch, params }) => ({
	item: await loadItem(fetch, 'books', params.id)
});
