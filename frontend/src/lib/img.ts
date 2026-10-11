// Image URL helpers: request the smallest variant that still looks sharp where it is displayed.
// TMDB / IGDB / ComicVine all serve resized variants from the same path, but we store the biggest
// ones (`original`, `w780`, `t_1080p`...). Every helper is a no-op for URLs it doesn't recognise,
// and `onImgError` falls back to the original URL, so a missing variant can never leave a broken image.

const TMDB = /^(https:\/\/image\.tmdb\.org\/t\/p\/)(?:original|w\d+)(\/.+)$/;
const IGDB = /^(https:\/\/images\.igdb\.com\/igdb\/image\/upload\/)t_[a-z0-9_]+(\/.+)$/;
const COMICVINE = /^(https:\/\/comicvine\.gamespot\.com\/a\/uploads\/)original(\/.+)$/;

type Url = string | null | undefined;

export function tmdb(url: Url, size: 'w185' | 'w300' | 'w342' | 'w500' | 'w780' | 'w1280' | 'original'): Url {
	return url ? url.replace(TMDB, `$1${size}$2`) : url;
}

export function igdb(url: Url, size: 't_screenshot_med' | 't_screenshot_big' | 't_cover_big'): Url {
	return url ? url.replace(IGDB, `$1${size}$2`) : url;
}

export function comicvine(url: Url, size: 'scale_large' | 'scale_medium' = 'scale_large'): Url {
	return url ? url.replace(COMICVINE, `$1${size}$2`) : url;
}

/** Poster size for the library grid (cards are ~200px wide). */
export function cardImage(url: Url): Url {
	return comicvine(tmdb(url, 'w342'));
}

/** `on:error` handler: retry once with the original (full-size) URL. */
export function onImgError(e: Event, original: Url) {
	const img = e.currentTarget as HTMLImageElement;
	if (original && !img.dataset.fallback) {
		img.dataset.fallback = '1';
		img.src = original;
	}
}
