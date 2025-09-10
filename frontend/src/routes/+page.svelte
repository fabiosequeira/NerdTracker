<script lang="ts">

import SearchBar from "$lib/components/SearchBar.svelte";

  type Movie = {
    title: string;
    year?: number;
    genres?: string[];
    rating?: number;
  }

  type Show = {
    title: string;
    seasons?: number;
    episodes?: number;
    genres?: string[];
    rating?: number;
  }

  type Anime = {
    title: string;
    seasons?: number;
    episodes?: number;
    genres?: string[];
    rating?: number;
  }

  let movies: Movie[] = [];
  let shows: Show[] = [];
  let anime: Anime[] = [];

  const apiBase = 'http://127.0.0.1:8000';

  async function fetchData<T>(endpoint: string, setter: (data: T[]) => void) {
    try {
      const res = await fetch(`${apiBase}/${endpoint}/`);
      const data: T[] = await res.json();
      setter(data);
    } catch (err) {
      console.error(`Error fetching ${endpoint}:`, err);
    }
  }

  fetchData<Movie>('movies', (d) => movies = d);
  fetchData<Show>('shows', (d) => shows = d);
  fetchData<Anime>('animes', (d) => anime = d);
</script>


<main class="p-8 bg-gray-100 min-h-screen">
  <h1 class="text-3xl font-bold text-center mb-8">NerdTracker</h1>
  <SearchBar />
  <section class="mb-6">
    <h2 class="text-xl font-semibold mb-2">Movies</h2>
    <ul class="bg-white rounded shadow p-4">
      {#each movies as m}
        <li class="p-2 border-b last:border-b-0 hover:bg-gray-50 transition">{m.title} ({m.year}) - Rating: {m.rating}</li>
      {/each}
    </ul>
  </section>

  <section class="mb-6">
    <h2 class="text-xl font-semibold mb-2">Shows</h2>
    <ul class="bg-white rounded shadow p-4">
      {#each shows as s}
        <li class="p-2 border-b last:border-b-0 hover:bg-gray-50 transition">{s.title} - Seasons: {s.seasons}, Episodes: {s.episodes}, Rating: {s.rating}</li>
      {/each}
    </ul>
  </section>

  <section class="mb-6">
    <h2 class="text-xl font-semibold mb-2">Anime</h2>
    <ul class="bg-white rounded shadow p-4">
      {#each anime as a}
        <li class="p-2 border-b last:border-b-0 hover:bg-gray-50 transition">{a.title} - Seasons: {a.seasons}, Episodes: {a.episodes}, Rating: {a.rating}</li>
      {/each}
    </ul>
  </section>
</main>
