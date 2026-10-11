import { loadItem } from '$lib/api';
import type { PageLoad } from './$types';

// Client-side only: the page is empty until this fetch lands, so there is nothing to server-render,
// and running it on the web container would just add a pointless server->API hop.
// Because it is a `load` function, SvelteKit starts it on link hover/touch
// (data-sveltekit-preload-data="hover" in app.html), so the page opens with its data already there.
export const ssr = false;

export const load: PageLoad = async ({ fetch, params }) => ({
	item: await loadItem(fetch, 'manga', params.id)
});
