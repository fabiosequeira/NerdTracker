<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { API_BASE, getCachedList } from "$lib/api";
  import { ASIN_LIKE, ISBN_LIKE, formatRuntime, peopleLine } from "$lib/media";
  const dispatch = createEventDispatcher();

  let query = "";
  let results: any[] = [];
  let loading = false;

  let highlightedIndex = -1; // for keyboard navigation
  let inputEl: HTMLInputElement;

  // --- Debounce and Cancellation state ---
  let debounceTimeout: ReturnType<typeof setTimeout> | null = null;
  let currentController: AbortController | null = null;

  // --- In-memory cache with expiry ---
  const cache = new Map<string, { timestamp: number; data: any[] }>();
  const CACHE_TTL = 120_000; // 2 minutes

  const SEARCH_SOURCES = [
    { type: "Movie", path: "tmdb/search/movie" },
    { type: "Show", path: "tmdb/search/tv" },
    { type: "Anime", path: "tmdb/search/anime" },
    { type: "Game", path: "igdb/search/game" },
    { type: "Comic", path: "comics/search" },
    { type: "Manga", path: "manga/search" },
    { type: "Book", path: "books/search" },
    { type: "Audiobook", path: "audiobooks/search" }
  ];

  const CATALOG_TYPES = ["Book", "Audiobook"];
  const isCatalog = (type: string) => CATALOG_TYPES.includes(type);

  // An ISBN (or, for audiobooks, an ASIN) can only mean a book / audiobook: skip the other sources.
  function sourcesFor(q: string) {
    const compact = q.trim();
    if (ISBN_LIKE.test(compact)) return SEARCH_SOURCES.filter(s => isCatalog(s.type));
    if (ASIN_LIKE.test(compact)) return SEARCH_SOURCES.filter(s => s.type === "Audiobook");
    return SEARCH_SOURCES;
  }

  // providers that failed / timed out during the last search (shown quietly under the results)
  let providerIssues: string[] = [];

  const ENDPOINT_FOR_TYPE: Record<string, string> = {
    Movie: "movies", Show: "shows", Anime: "animes", Game: "games", Comic: "comics", Manga: "manga",
    Book: "books", Audiobook: "audiobooks"
  };
  // which stored field holds the external (search) id for each type
  const ID_FIELD_FOR_TYPE: Record<string, string> = {
    Movie: "tmdb_id", Show: "tmdb_id", Anime: "tmdb_id", Game: "igdb_id", Comic: "comicvine_id", Manga: "anilist_id"
  };

  async function searchAllInternal(q: string) {
    if (q.length < 2) {
      if (currentController) currentController.abort();
      loading = false;
      results = [];
      highlightedIndex = -1;
      return;
    }

    const cached = cache.get(q);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      results = cached.data;
      highlightedIndex = -1;
      return;
    }

    loading = true;

    // Cancel previous request if still running
    if (currentController) {
      currentController.abort();
    }
    const controller = new AbortController();
    currentController = controller;
    const { signal } = controller;

    const collected: any[] = [];
    const issues = new Set<string>();
    providerIssues = [];
    let allOk = true;

    // Each source reports as soon as it answers, so fast ones show up immediately instead of
    // everything waiting for the slowest (ComicVine, TV detail lookups). A source that fails no
    // longer throws away the results of the others.
    await Promise.all(
      sourcesFor(q).map(async ({ type, path }) => {
        try {
          const res = await fetch(`${API_BASE}/${path}?query=${encodeURIComponent(q)}`, { signal });
          const body = res.ok ? await res.json() : null;
          // Books/Audiobooks answer { results, providers }; the older sources answer a plain list
          const data = Array.isArray(body) ? body : body?.results;
          if (!Array.isArray(data)) { allOk = false; return; }
          if (!Array.isArray(body) && body?.providers) {
            for (const [name, st] of Object.entries<any>(body.providers)) {
              if (st.status === "error" || st.status === "timeout") issues.add(name.replace(/_/g, " "));
            }
            providerIssues = [...issues];
          }
          if (signal.aborted) return;
          collected.push(...data.map((item: any) => ({ ...item, type })));
          results = [...collected].sort((a, b) => (b.popularity ?? 0) - (a.popularity ?? 0));
          highlightedIndex = -1;
        } catch (err: any) {
          allOk = false;
          if (err.name !== "AbortError") console.error(`Search failed (${type}):`, err);
        }
      })
    );

    if (signal.aborted) return; // superseded by a newer query
    if (allOk) cache.set(q, { timestamp: Date.now(), data: results });
    loading = false;
  }

  function searchAll() {
    if (debounceTimeout) clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      searchAllInternal(query);
    }, 300); // 300ms debounce
  }

  async function addItem(item: any) {
    const endpoint = ENDPOINT_FOR_TYPE[item.type];
    if (!endpoint) return;

    // check the library the home page already loaded (per type) before sending a request
    const idField = ID_FIELD_FOR_TYPE[item.type];
    const library = getCachedList(endpoint);
    const alreadyThere = isCatalog(item.type)
      ? library?.some((e) =>
          (item.identifiers?.isbn_13 && e.isbn_13 === item.identifiers.isbn_13) ||
          (item.identifiers?.asin && e.asin === item.identifiers.asin))
      : library?.some((existing) => existing[idField] === item.id);
    if (alreadyThere) {
      alert(`${item.type} "${item.title}" is already in your library ✅`);
      return;
    }

    try {
      let res;

      if (isCatalog(item.type)) {
        // The server re-fetches and merges the metadata from these identifiers itself.
        res = await fetch(`${API_BASE}/${endpoint}/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ identifiers: item.identifiers })
        });
        if (res.status === 409) {
          alert(`${item.type} "${item.title}" is already in your library ✅`);
          return;
        }
      } else if (item.type === "Game") {
        res = await fetch(`${API_BASE}/${endpoint}/?igdb_id=${item.id}`, { method: "POST" });
      } else if (item.type === "Comic") {
        res = await fetch(`${API_BASE}/comics/?comicvine_id=${item.id}`, { method: "POST" });
      } else if (item.type === "Manga") {
        res = await fetch(`${API_BASE}/manga/?anilist_id=${item.id}`, { method: "POST" });
      } else {
        // Movies, Shows, Anime
        res = await fetch(`${API_BASE}/${endpoint}/?tmdb_id=${item.id}`, { method: "POST" });
      }

      if (!res.ok) {
        const errText = await res.text();
        console.error("Error adding item:", errText);
        let reason = "";
        if (isCatalog(item.type)) {
          try { const d = JSON.parse(errText).detail; reason = typeof d === "string" ? `\n${d}` : ""; } catch { /* not JSON */ }
        }
        alert(`Failed to add item ❌${reason}`);
        return;
      }

      alert(`${item.type} "${item.title}" added ✅`);
      query = "";
      results = [];
      highlightedIndex = -1;
      // the home page re-fetches just this list (and refreshes its cache)
      dispatch('itemAdded', { type: item.type });

    } catch (err) {
      console.error("Add failed:", err);
      alert("Failed to add item ❌");
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!results.length) return;

    if (e.key === "ArrowDown") {
      highlightedIndex = (highlightedIndex + 1) % results.length;
      e.preventDefault();
    }
    if (e.key === "ArrowUp") {
      highlightedIndex = (highlightedIndex - 1 + results.length) % results.length;
      e.preventDefault();
    }
    if (e.key === "Enter") {
      if (highlightedIndex >= 0) addItem(results[highlightedIndex]);
      e.preventDefault();
    }
    if (e.key === "Escape") {
      results = [];
      highlightedIndex = -1;
    }
  }
</script>

<div class="relative w-full max-w-md mx-auto z-50">
  <input
    bind:this={inputEl}
    type="text"
    bind:value={query}
    on:input={searchAll}
    on:keydown={handleKeydown}
    placeholder="Search movies, shows, anime, games, comics, books, audiobooks or an ISBN..."
    class="w-full border border-gray-700 rounded-lg p-2 bg-gray-800 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
  />

  {#if loading && results.length === 0}
    <div class="absolute bg-gray-800 border border-gray-700 w-full mt-1 p-2 text-gray-400 z-50">Loading...</div>
  {/if}

  {#if results.length > 0}
  <ul class="absolute bg-gray-800 border border-gray-700 w-full mt-1 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
    {#each results as item, i}
      <li>
        <button
          type="button"
          class="flex items-center gap-3 w-full text-left p-2 cursor-pointer rounded
            {i === highlightedIndex ? 'bg-gray-700' : ''} hover:bg-gray-700"
          on:click={() => addItem(item)}
        >
          {#if item.poster}
            <img src={item.poster} alt={item.title} width="40" height="56" loading="lazy" decoding="async" class="w-10 h-14 object-cover rounded" />
          {:else if isCatalog(item.type)}
            <div class="w-10 h-14 shrink-0 rounded bg-gray-700 flex items-center justify-center" aria-hidden="true">{item.type === 'Audiobook' ? '🎧' : '📖'}</div>
          {/if}

          <div class="min-w-0">
            <span class="font-medium text-gray-100">{item.title}</span>

            <span class="text-sm text-gray-400">
              {item.year ? `(${item.year})` : ""} • {item.type}
            </span>

            {#if isCatalog(item.type)}
              <div class="text-xs text-gray-400">
                {[
                  peopleLine(item.authors, 2),
                  item.type === 'Audiobook' && item.narrators?.length ? `🎙️ ${peopleLine(item.narrators, 1)}` : '',
                  item.type === 'Audiobook' ? formatRuntime(item.runtime_minutes) : '',
                  item.type === 'Book' && item.page_count ? `${item.page_count} pages` : '',
                  item.type === 'Audiobook' && item.recording_type ? item.recording_type : '',
                ].filter(Boolean).join(' • ')}
              </div>
              {#if item.publisher || item.identifiers?.isbn_13 || item.identifiers?.asin}
                <div class="text-xs text-gray-500">
                  {[item.publisher, item.identifiers?.isbn_13 ? `ISBN ${item.identifiers.isbn_13}` : item.identifiers?.asin ? `ASIN ${item.identifiers.asin}` : ''].filter(Boolean).join(' • ')}
                </div>
              {/if}
            {/if}

            {#if item.type === 'Comic'}
              <div class="text-xs text-gray-400">
                {item.count_of_issues ? `${item.count_of_issues} issues` : ""}
                {item.publisher ? ` • ${item.publisher}` : ""}
              </div>
            {/if}
          </div>
        </button>
      </li>
    {/each}
    {#if providerIssues.length}
      <li class="p-2 text-xs text-amber-300 border-t border-gray-700" aria-live="polite">
        ⚠️ Some results may be missing: {providerIssues.join(", ")} unavailable
      </li>
    {/if}
  </ul>
{/if}

</div>
