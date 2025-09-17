<script lang="ts">
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();

  let query = "";
  let results: any[] = [];
  let loading = false;
  let items: any[] = []; // DB list

  let highlightedIndex = -1; // for keyboard navigation
  let inputEl: HTMLInputElement;

  // --- Debounce and Cancellation state ---
  let debounceTimeout: ReturnType<typeof setTimeout> | null = null;
  let currentController: AbortController | null = null;

  // --- In-memory cache with expiry ---
  const cache = new Map<string, { timestamp: number; data: any[] }>();
  const CACHE_TTL = 120_000; // 2 minutes

  async function searchAllInternal(q: string) {
    if (q.length < 2) {
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
    currentController = new AbortController();
    const { signal } = currentController;

    try {
      const [moviesRes, showsRes, animeRes, gamesRes] = await Promise.all([
        fetch(`http://127.0.0.1:8000/tmdb/search/movie?query=${encodeURIComponent(q)}`, { signal }),
        fetch(`http://127.0.0.1:8000/tmdb/search/tv?query=${encodeURIComponent(q)}`, { signal }),
        fetch(`http://127.0.0.1:8000/tmdb/search/anime?query=${encodeURIComponent(q)}`, { signal }),
        fetch(`http://127.0.0.1:8000/igdb/search/game?query=${encodeURIComponent(q)}`, { signal })
      ]);

      const movies = await moviesRes.json();
      const shows = await showsRes.json();
      const animes = await animeRes.json();
      const games = await gamesRes.json();

      const merged = [
        ...movies.map((m: any) => ({ ...m, type: "Movie" })),
        ...shows.map((s: any) => ({ ...s, type: "Show" })),
        ...animes.map((a: any) => ({ ...a, type: "Anime" })),
        ...games.map((g: any) => ({ ...g, type: "Game" }))
      ].sort((a, b) => (b.popularity ?? 0) - (a.popularity ?? 0));

      results = merged;
      cache.set(q, { timestamp: Date.now(), data: merged });
      highlightedIndex = -1;
    } catch (err: any) {
      if (err.name === "AbortError") {
        return; // Ignore aborted requests
      }
      console.error("Search failed:", err);
    } finally {
      loading = false;
    }
  }

  function searchAll() {
    if (debounceTimeout) clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      searchAllInternal(query);
    }, 300); // 300ms debounce
  }

  async function fetchItems(endpoint: string) {
    try {
      const res = await fetch(`http://127.0.0.1:8000/${endpoint}/`);
      if (res.ok) items = await res.json();
    } catch (err) {
      console.error("Failed to fetch items:", err);
    }
  }

  async function addItem(item: any) {
    let endpoint = "";
    if (item.type === "Movie") endpoint = "movies";
    if (item.type === "Show") endpoint = "shows";
    if (item.type === "Anime") endpoint = "animes";
    if (item.type === "Game") endpoint = "games";

    if (!endpoint) return;

    try {
      let res;
      if (item.type === "Game") {
        res = await fetch(`http://127.0.0.1:8000/${endpoint}/?igdb_id=${item.id}`, { method: "POST" });
      } else {
        res = await fetch(`http://127.0.0.1:8000/${endpoint}/?tmdb_id=${item.id}`, { method: "POST" });
      }

      if (!res.ok) {
        const errText = await res.text();
        console.error("Error adding item:", errText);
        alert("Failed to add item ❌");
        return;
      }

      // fetch all DB lists after adding
      await Promise.all([
        fetchItems("movies"),
        fetchItems("shows"),
        fetchItems("animes"),
        fetchItems("games")
      ]);

      alert(`${item.type} "${item.title}" added ✅`);
      query = "";
      results = [];
      highlightedIndex = -1;
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
    placeholder="Search for a movie, show, anime or game..."
    class="w-full border border-gray-700 rounded-lg p-2 bg-gray-800 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
  />

  {#if loading}
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
              <img src={item.poster} alt={item.title} class="w-10 h-14 object-cover rounded" />
            {/if}
            <div>
              <span class="font-medium text-gray-100">{item.title}</span>
              <span class="text-sm text-gray-400">
                {item.year ? `(${item.year})` : ""} • {item.type}
              </span>
            </div>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
