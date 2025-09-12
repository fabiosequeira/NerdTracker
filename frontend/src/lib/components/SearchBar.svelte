<script lang="ts">
	import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();

  let query = "";
  let results: any[] = [];
  let loading = false;
  let items: any[] = []; // lista da DB visível

  async function searchAll() {
    if (query.length < 2) {
      results = [];
      return;
    }
    loading = true;

    try {
      const [moviesRes, showsRes, animeRes] = await Promise.all([
        fetch(`http://127.0.0.1:8000/tmdb/search/movie?query=${encodeURIComponent(query)}`),
        fetch(`http://127.0.0.1:8000/tmdb/search/tv?query=${encodeURIComponent(query)}`),
        fetch(`http://127.0.0.1:8000/tmdb/search/anime?query=${encodeURIComponent(query)}`)
      ]);

      const movies = await moviesRes.json();
      const shows = await showsRes.json();
      const animes = await animeRes.json();

      results = [
        ...movies.map((m: any) => ({ ...m, type: "Movie" })),
        ...shows.map((s: any) => ({ ...s, type: "Show" })),
        ...animes.map((a: any) => ({ ...a, type: "Anime" }))
      ].sort((a, b) => (b.popularity ?? 0) - (a.popularity ?? 0));
    } catch (err) {
      console.error("Search failed:", err);
    }

    loading = false;
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

    if (!endpoint) return;

    try {
      const res = await fetch(`http://127.0.0.1:8000/${endpoint}/?tmdb_id=${item.id}`, {
        method: "POST"
      });

      if (!res.ok) {
        const errText = await res.text();
        console.error("Error adding item:", errText);
        alert("Failed to add item ❌");
        return;
      }

      await Promise.all([
        fetchItems("movies"),
        fetchItems("shows"),
        fetchItems("animes")
      ]);

      alert(`${item.type} "${item.title}" added ✅`);
      query = "";
      results = [];
      dispatch('itemAdded', { type: item.type });
    } catch (err) {
      console.error("Add failed:", err);
      alert("Failed to add item ❌");
    }
  }

</script>

<div class="relative w-full max-w-md mx-auto">
  <input
    type="text"
    bind:value={query}
    on:input={searchAll}
    placeholder="Search for a movie, show or anime..."
    class="w-full border rounded-lg p-2"
  />

  {#if loading}
    <div class="absolute bg-white border w-full mt-1 p-2 text-gray-500">Loading...</div>
  {/if}

  {#if results.length > 0}
    <ul class="absolute bg-white border w-full mt-1 rounded-lg shadow-lg z-10 max-h-96 overflow-y-auto">
      {#each results as item}
        <li>
          <button
            type="button"
            class="flex items-center gap-3 w-full text-left p-2 hover:bg-gray-100 cursor-pointer"
            on:click={() => addItem(item)}
          >
            {#if item.poster}
              <img src={item.poster} alt={item.title} class="w-10 h-14 object-cover rounded" />
            {/if}
            <div>
              <span class="font-medium">{item.title}</span>
              <span class="text-sm text-gray-500">({item.year}) • {item.type}</span>
            </div>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
