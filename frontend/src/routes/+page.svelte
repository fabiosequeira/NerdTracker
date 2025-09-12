<script lang="ts">
import SearchBar from "$lib/components/SearchBar.svelte";

type Movie = {
  title: string;
  year?: number;
  genres?: string[];
  rating?: number;
  poster?: string;
}

type Show = {
  title: string;
  seasons?: number;
  episodes?: number;
  genres?: string[];
  rating?: number;
  poster?: string;
}

type Anime = {
  title: string;
  seasons?: number;
  episodes?: number;
  genres?: string[];
  rating?: number;
  poster?: string;
}

let movies: Movie[] = [];
let shows: Show[] = [];
let anime: Anime[] = [];

let activeTab: "Movies" | "Shows" | "Anime" = "Movies";

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

  <SearchBar on:itemAdded={(e) => {
    const type = e.detail.type;
    if (type == 'Movie') fetchData<Movie>('movies', d => movies = d);
    if (type == 'Show') fetchData<Show>('shows', d => shows = d);
    if (type == 'Anime') fetchData<Anime>('animes', d => anime = d);
  }} />

  <!-- Tabs -->
  <div class="flex justify-center gap-4 mt-6 mb-6">
    {#each ["Movies", "Shows", "Anime"] as tab}
      <button
        class="px-4 py-2 rounded-lg font-medium border shadow-sm"
        class:selected={activeTab === tab}
        on:click={() => activeTab = tab}
      >
        {tab}
      </button>
    {/each}
  </div>

  <!-- Conteúdo das tabs -->
  {#if activeTab === "Movies"}
    <section class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
      {#each movies as m}
        <div class="bg-white rounded-lg shadow hover:shadow-lg overflow-hidden cursor-pointer transition">
          {#if m.poster}
            <img src={m.poster} alt={m.title} class="w-full aspect-[2/3] object-cover"/>
          {/if}
          <div class="p-4">
            <h3 class="font-semibold text-lg">{m.title}</h3>
            <p class="text-sm text-gray-500">Year: {m.year ?? "-"}</p>
            <p class="text-sm text-gray-500">Rating: {m.rating ?? "-"}</p>
          </div>
        </div>
      {/each}
    </section>
  {/if}

  {#if activeTab === "Shows"}
    <section class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
      {#each shows as s}
        <div class="bg-white rounded-lg shadow hover:shadow-lg overflow-hidden cursor-pointer transition">
          {#if s.poster}
            <img src={s.poster} alt={s.title} class="w-full aspect-[2/3] object-cover"/>
          {/if}
          <div class="p-4">
            <h3 class="font-semibold text-lg">{s.title}</h3>
            <p class="text-sm text-gray-500">Seasons: {s.seasons ?? "-"}</p>
            <p class="text-sm text-gray-500">Episodes: {s.episodes ?? "-"}</p>
            <p class="text-sm text-gray-500">Rating: {s.rating ?? "-"}</p>
          </div>
        </div>
      {/each}
    </section>
  {/if}

  {#if activeTab === "Anime"}
    <section class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
      {#each anime as a}
        <div class="bg-white rounded-lg shadow hover:shadow-lg overflow-hidden cursor-pointer transition">
          {#if a.poster}
            <img src={a.poster} alt={a.title} class="w-full aspect-[2/3] object-cover"/>
          {/if}
          <div class="p-4">
            <h3 class="font-semibold text-lg">{a.title}</h3>
            <p class="text-sm text-gray-500">Seasons: {a.seasons ?? "-"}</p>
            <p class="text-sm text-gray-500">Episodes: {a.episodes ?? "-"}</p>
            <p class="text-sm text-gray-500">Rating: {a.rating ?? "-"}</p>
          </div>
        </div>
      {/each}
    </section>
  {/if}
</main>

<style>
  button.selected {
    background-color: #2563eb;
    color: white;
    border-color: transparent;
  }
</style>
