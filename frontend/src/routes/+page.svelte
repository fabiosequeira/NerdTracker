<script lang="ts">
  import SearchBar from "$lib/components/SearchBar.svelte";
  import { browser } from "$app/environment";
  import ParticleBackground from "$lib/components/ParticleBackground.svelte";
  import { API_BASE, fetchList, getCachedList, setCachedList } from "$lib/api";
  import { cardImage, onImgError } from "$lib/img";

  let movies: any[] = [], shows: any[] = [], anime: any[] = [], games: any[] = [], comics: any[] = [], mangas: any[] = [];
  let activeTab: "Movies" | "Shows" | "Anime" | "Game" | "Comics" | "Mangas" = "Movies";
  const apiBase = API_BASE;
  
  let heroItems = []; // not used anymore, kept in case we want to add banner back

  // Show the last-known list instantly when we have one (e.g. coming back from a detail page),
  // then refresh it in the background.
  async function fetchData(endpoint: string, setter: (data: any) => void) {
    const cached = getCachedList(endpoint);
    if (cached) setter(cached);
    try {
      setter(await fetchList(endpoint));
    } catch(e) { console.error(e); }
  }

  // Browser only. During SSR these six requests used to fire from the web container as well,
  // and their results were thrown away.
  if (browser) {
    fetchData("movies", d => movies = d);
    fetchData("shows", d => shows = d);
    fetchData("animes", d => anime = d);
    fetchData("games", d => games = d);
    fetchData("comics", d => comics = d);
    fetchData("manga", d => mangas = d);
  }



  async function deleteItem(item: any, endpoint: string) {
    const id = item._id || item.id;
    if(!id) return alert("No ID found");
    const res = await fetch(`${apiBase}/${endpoint}/${id}`, { method: "DELETE" });
    if(res.ok) {
      alert(`Deleted "${item.title}"`);
      if(endpoint==="movies") { movies = movies.filter(i=>i._id!==id); setCachedList(endpoint, movies); }
      if(endpoint==="shows") { shows = shows.filter(i=>i._id!==id); setCachedList(endpoint, shows); }
      if(endpoint==="animes") { anime = anime.filter(i=>i._id!==id); setCachedList(endpoint, anime); }
      if(endpoint==="games") { games = games.filter(i=>i._id!==id); setCachedList(endpoint, games); }
      if(endpoint==="comics") { comics = comics.filter(i=>i._id!==id); setCachedList(endpoint, comics); }
      if(endpoint==="manga") { mangas = mangas.filter(i=>i._id!==id); setCachedList(endpoint, mangas); }
    } else alert("Delete failed ❌");
  }


  let sortOrder: "release" | "rating" | "title" = "release"; // default sorting

function sortItems(items: any[]) {
  return [...items].sort((a, b) => {
    if (sortOrder === "release") return (b.year ?? 0) - (a.year ?? 0);
    if (sortOrder === "rating") return (b.rating ?? 0) - (a.rating ?? 0);
    if (sortOrder === "title") return a.title.localeCompare(b.title);
    return 0;
  });
}
</script>

<main class="relative bg-gray-900 min-h-screen text-gray-100 overflow-x-hidden">

  <!-- Particle background -->
  <ParticleBackground />


  <!-- Header -->
 <header class="relative z-50 p-6 text-center">
  <h1 class="text-4xl md:text-5xl font-bold mb-4 text-blue-400">NerdTracker</h1>
  <SearchBar on:itemAdded={(e)=>{
    const type = e.detail.type;
    if(type=='Movie') fetchData("movies", d=>movies=d);
    if(type=='Show') fetchData("shows", d=>shows=d);
    if(type=='Anime') fetchData("animes", d=>anime=d);
    if(type=='Game') fetchData("games", d=>games=d);
    if(type=='Comic') fetchData("comics", d=>comics=d);
    if(type=='Manga') fetchData("manga", d=>mangas=d);
  }}/>
</header>

  <!-- Tabs with animated underline -->
  <div class="relative z-10 flex justify-center gap-6 mb-8 border-b border-gray-700">
    {#each ["Movies","Shows","Anime","Game","Comics","Mangas"] as tab}
      <button
        class="py-2 px-4 font-semibold text-gray-300 hover:text-white transition-colors relative"
        class:selected={activeTab===tab}
        on:click={()=>activeTab=tab as typeof activeTab}
      >
        {tab}
        {#if activeTab===tab}
          <span class="absolute bottom-0 left-0 w-full h-1 bg-blue-500 rounded-full"></span>
        {/if}
      </button>
    {/each}
  </div>


  
<div class="flex justify-end gap-4 mb-4 px-4 md:px-6">
  <label for="sort" class="text-gray-300">Sort by:</label>
  <select id="sort" bind:value={sortOrder} class="bg-gray-700 text-gray-100 rounded px-2 py-1">
    <option value="release">Release Date</option>
    <option value="rating">Rating</option>
    <option value="title">Title</option>
  </select>
</div>

<!-- Grid section -->
<section class="relative z-10 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-6 px-4 md:px-6">

  {#if activeTab === "Movies"}
    {#each sortItems(movies) as item (item._id)}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/movies/${item._id}`}>
          <img src={cardImage(item.poster)} on:error={(e) => onImgError(e, item.poster)} loading="lazy" decoding="async" alt={item.title} class="w-full aspect-[2/3] object-cover"/>
        </a>
        <div class="p-4 space-y-1">
          <a href={`/movies/${item._id}`} class="font-bold text-lg group-hover:text-blue-400">{item.title}</a>
          {#if item.year}<p class="text-sm text-gray-400">📆 {item.year}</p>{/if}
          {#if item.rating}<p class="text-sm text-gray-400">⭐ {item.rating}</p>{/if}
          {#if item.genres?.length}
            <div class="flex flex-wrap gap-1 mt-1">
              {#each item.genres as g}
                <span class="bg-blue-600/80 px-2 py-0.5 rounded text-xs">{g}</span>
              {/each}
            </div>
          {/if}
        </div>
        <button
          class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
          on:click={() => deleteItem(item, "movies")}
        >Delete</button>
      </div>
    {/each}
  {/if}

  {#if activeTab === "Shows"}
    {#each sortItems(shows) as item (item._id)}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/shows/${item._id}`}>
          <img src={cardImage(item.poster)} on:error={(e) => onImgError(e, item.poster)} loading="lazy" decoding="async" alt={item.title} class="w-full aspect-[2/3] object-cover"/>
        </a>
        <div class="p-4 space-y-1">
          <a href={`/shows/${item._id}`} class="font-bold text-lg group-hover:text-blue-400">{item.title}</a>
          {#if item.seasons}<p class="text-sm text-gray-400">📺Seasons: {item.seasons}</p>{/if}
          {#if item.episodes}<p class="text-sm text-gray-400">🎬Episodes: {item.episodes}</p>{/if}
          {#if item.rating}<p class="text-sm text-gray-400">⭐ {item.rating}</p>{/if}
          {#if item.genres?.length}
            <div class="flex flex-wrap gap-1 mt-1">
              {#each item.genres as g}
                <span class="bg-blue-600/80 px-2 py-0.5 rounded text-xs">{g}</span>
              {/each}
            </div>
          {/if}
        </div>
        <button
          class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
          on:click={() => deleteItem(item, "shows")}
        >Delete</button>
      </div>
    {/each}
  {/if}

  {#if activeTab === "Anime"}
    {#each sortItems(anime) as item (item._id)}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/animes/${item._id}`}>
          <img src={cardImage(item.poster)} on:error={(e) => onImgError(e, item.poster)} loading="lazy" decoding="async" alt={item.title} class="w-full aspect-[2/3] object-cover"/>
        </a>
        <div class="p-4 space-y-1">
          <a href={`/animes/${item._id}`} class="font-bold text-lg group-hover:text-blue-400">{item.title}</a>
          {#if item.seasons}<p class="text-sm text-gray-400">📺Seasons: {item.seasons}</p>{/if}
          {#if item.episodes}<p class="text-sm text-gray-400">🎬Episodes: {item.episodes}</p>{/if}
          {#if item.rating}<p class="text-sm text-gray-400">⭐ {item.rating}</p>{/if}
          {#if item.genres?.length}
            <div class="flex flex-wrap gap-1 mt-1">
              {#each item.genres as g}
                <span class="bg-blue-600/80 px-2 py-0.5 rounded text-xs">{g}</span>
              {/each}
            </div>
          {/if}
        </div>
        <button
          class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
          on:click={() => deleteItem(item, "animes")}
        >Delete</button>
      </div>
    {/each}
  {/if}

  {#if activeTab === "Game"}
    {#each sortItems(games) as item (item._id)}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/games/${item._id}`}>
          <img src={cardImage(item.cover ?? item.poster)} on:error={(e) => onImgError(e, item.cover ?? item.poster)} loading="lazy" decoding="async" alt={item.title} class="w-full aspect-[2/3] object-cover"/>
        </a>
        <div class="p-4 space-y-1">
          <a href={`/games/${item._id}`} class="font-bold text-lg group-hover:text-blue-400">{item.title}</a>
          {#if item.year}<p class="text-sm text-gray-400">📆 {item.year}</p>{/if}
          {#if item.rating}<p class="text-sm text-gray-400">⭐ {item.rating}</p>{/if}
          {#if item.genres?.length}
            <div class="flex flex-wrap gap-1 mt-1">
              {#each item.genres as g}
                <span class="bg-blue-600/80 px-2 py-0.5 rounded text-xs">{g}</span>
              {/each}
            </div>
          {/if}
        </div>
        <button
          class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
          on:click={() => deleteItem(item, "games")}
        >Delete</button>
      </div>
    {/each}
  {/if}

  {#if activeTab === "Comics"}
    {#each sortItems(comics) as item (item._id)}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/comics/${item._id}`}>
          <img src={cardImage(item.poster)} on:error={(e) => onImgError(e, item.poster)} loading="lazy" decoding="async" alt={item.title} class="w-full aspect-[2/3] object-cover"/>
        </a>
        <div class="p-4 space-y-1">
          <a href={`/comics/${item._id}`} class="font-bold text-lg group-hover:text-blue-400">{item.title}</a>
          {#if item.year}<p class="text-sm text-gray-400">📆 {item.year}</p>{/if}
          {#if item.count_of_issues}<p class="text-sm text-gray-400">#️⃣Issues: {item.count_of_issues}</p>{/if}
          {#if item.publisher}<p class="text-sm text-gray-400">🏢 {item.publisher}</p>{/if}
        </div>
        <button
          class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
          on:click={() => deleteItem(item, "comics")}
        >Delete</button>
      </div>
    {/each}
  {/if}

  {#if activeTab === "Mangas"}
    {#each sortItems(mangas) as item (item._id)}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/manga/${item._id}`}>
          <img src={cardImage(item.poster)} on:error={(e) => onImgError(e, item.poster)} loading="lazy" decoding="async" alt={item.title} class="w-full aspect-[2/3] object-cover"/>
        </a>
        <div class="p-4 space-y-1">
          <a href={`/manga/${item._id}`} class="font-bold text-lg group-hover:text-blue-400">{item.title}</a>
          {#if item.year}<p class="text-sm text-gray-400">📆 {item.year}</p>{/if}
          {#if item.average_score}<p class="text-sm text-gray-400">⭐ {item.average_score}</p>{/if}
          {#if item.genres?.length}
            <div class="flex flex-wrap gap-1 mt-1">
              {#each item.genres as g}
                <span class="bg-blue-600/80 px-2 py-0.5 rounded text-xs">{g}</span>
              {/each}
            </div>
          {/if}
        </div>
        <button
          class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
          on:click={() => deleteItem(item, "manga")}
        >Delete</button>
      </div>
    {/each}
  {/if}


</section>
</main>

<style>
  button.selected {
    color: white;
  }
</style>
