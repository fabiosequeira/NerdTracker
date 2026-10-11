// Single place for the API base URL (it used to be hard-coded in 10+ places).
export const API_BASE = 'https://ntbck.fabioserver.xyz'; // PRODUCTION
// export const API_BASE = 'http://127.0.0.1:8000'; // LOCAL

/** Used by the detail pages' `load` functions so data starts loading on link hover/touch. */
export async function loadItem(fetchFn: typeof fetch, endpoint: string, id: string) {
	try {
		const res = await fetchFn(`${API_BASE}/${endpoint}/${id}`);
		if (!res.ok) throw new Error(`Failed to fetch ${endpoint}/${id}`);
		return await res.json();
	} catch (err) {
		console.error(err);
		return null;
	}
}

// --- Library lists: tiny in-memory stale-while-revalidate cache -------------------------------
// Coming back to the home page (e.g. from a detail page) shows the last-known lists instantly,
// then refreshes them in the background.
const listCache = new Map<string, any[]>();

export function getCachedList(endpoint: string): any[] | undefined {
	return listCache.get(endpoint);
}

export function setCachedList(endpoint: string, items: any[]) {
	listCache.set(endpoint, items);
}

export async function fetchList(endpoint: string): Promise<any[]> {
	const res = await fetch(`${API_BASE}/${endpoint}/`);
	if (!res.ok) throw new Error(`Failed to fetch ${endpoint}`);
	const data = await res.json();
	listCache.set(endpoint, data);
	return data;
}
