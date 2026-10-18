// Helpers shared by the Book / Audiobook UI. Every helper tolerates missing data: records are allowed
// to be incomplete (nothing is invented), so "unknown" is a normal input here.

export type CatalogKind = 'book' | 'audiobook';

export interface CatalogItem {
	_id: string;
	title: string;
	subtitle?: string | null;
	authors?: string[];
	narrators?: string[];
	cover?: string | null;
	published_date?: string | null;
	first_published_year?: number | null;
	page_count?: number | null;
	runtime_minutes?: number | null;
	recording_type?: string | null;
	series?: { name: string; position?: string | null } | null;
	personal_rating?: number | null;
	[key: string]: any;
}

/** Best-known year for sorting / display: edition year, else first publication. 0 = unknown. */
export function itemYear(item: any): number {
	if (typeof item?.year === 'number') return item.year;
	const m = /^(\d{4})/.exec(item?.published_date ?? '');
	if (m) return parseInt(m[1], 10);
	return item?.first_published_year ?? 0;
}

export function formatRuntime(minutes?: number | null): string {
	if (!minutes || minutes <= 0) return '';
	const h = Math.floor(minutes / 60);
	const m = Math.round(minutes % 60);
	if (h === 0) return `${m}m`;
	return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

/** "A, B" or "A, B +2" */
export function peopleLine(names?: string[] | null, max = 2): string {
	const list = (names ?? []).filter(Boolean);
	if (list.length <= max) return list.join(', ');
	return `${list.slice(0, max).join(', ')} +${list.length - max}`;
}

export function recordingLabel(type?: string | null): string {
	return type ? type.charAt(0).toUpperCase() + type.slice(1) : '';
}

export function seriesLabel(series?: { name: string; position?: string | null } | null): string {
	if (!series?.name) return '';
	return series.position ? `${series.name} #${series.position}` : series.name;
}

export function languageName(code?: string | null): string {
	if (!code) return '';
	try {
		return new Intl.DisplayNames(['en'], { type: 'language' }).of(code) ?? code.toUpperCase();
	} catch {
		return code.toUpperCase();
	}
}

/** 'YYYY' | 'YYYY-MM' | 'YYYY-MM-DD' -> readable, never claiming more precision than the data has. */
export function formatDate(partial?: string | null): string {
	if (!partial) return '';
	const parts = partial.split('-').map((p) => parseInt(p, 10));
	if (!parts[0]) return '';
	if (parts.length === 1) return String(parts[0]);
	const d = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2] ?? 1));
	return new Intl.DateTimeFormat('en', {
		year: 'numeric',
		month: 'short',
		...(parts.length === 3 ? { day: 'numeric' } : {}),
		timeZone: 'UTC'
	}).format(d);
}

export function formatTimestamp(iso?: string | null): string {
	if (!iso) return '';
	const d = new Date(iso);
	return isNaN(d.getTime()) ? '' : d.toLocaleString();
}

const PROVIDER_LABELS: Record<string, string> = {
	google_books: 'Google Books',
	open_library: 'Open Library',
	hardcover: 'Hardcover',
	itunes: 'Apple Books',
	audnexus: 'Audnexus (Audible data)'
};
export function providerLabel(name: string): string {
	return PROVIDER_LABELS[name] ?? name;
}

const FIELD_LABELS: Record<string, string> = {
	title: 'title', subtitle: 'subtitle', authors: 'authors', narrators: 'narrators', contributors: 'contributors',
	isbn_10: 'ISBN-10', isbn_13: 'ISBN-13', other_isbns: 'other ISBNs', asin: 'ASIN', identifiers: 'identifiers',
	edition: 'edition', publisher: 'publisher', published_date: 'publication date', first_published_year: 'first published',
	language: 'language', page_count: 'page count', runtime_minutes: 'runtime', recording_type: 'recording type',
	description: 'description', cover: 'cover', genres: 'genres', series: 'series'
};
export function fieldLabel(field: string): string {
	return FIELD_LABELS[field] ?? field;
}

export const ISBN_LIKE = /^(?:isbn[\s:-]*)?(?:\d[\s-]?){9}[\dXx]$|^(?:isbn[\s:-]*)?(?:\d[\s-]?){12}\d$/i;
// real Audible ASINs are "B0" + 8 alphanumerics; looser would swallow words like "Bridgerton"
export const ASIN_LIKE = /^B0[0-9A-Z]{8}$/i;
