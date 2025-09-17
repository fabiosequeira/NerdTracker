<script lang="ts">
  import SearchBar from "$lib/components/SearchBar.svelte";
  import { onMount } from "svelte";

  let movies: any[] = [], shows: any[] = [], anime: any[] = [], games: any[] = [];
  let activeTab: "Movies" | "Shows" | "Anime" | "Game" = "Movies";
  const apiBase = 'http://127.0.0.1:8000';

  let heroItems = []; // not used anymore, kept in case we want to add banner back

  async function fetchData(endpoint: string, setter: (data: any) => void) {
    try {
      const res = await fetch(`${apiBase}/${endpoint}/`);
      const data = await res.json();
      setter(data);
    } catch(e) { console.error(e); }
  }

  fetchData("movies", d => movies = d);
  fetchData("shows", d => shows = d);
  fetchData("animes", d => anime = d);
  fetchData("games", d => games = d);

  async function deleteItem(item: any, endpoint: string) {
    const id = item._id || item.id;
    if(!id) return alert("No ID found");
    const res = await fetch(`${apiBase}/${endpoint}/${id}`, { method: "DELETE" });
    if(res.ok) {
      alert(`Deleted "${item.title}"`);
      if(endpoint==="movies") movies = movies.filter(i=>i._id!==id);
      if(endpoint==="shows") shows = shows.filter(i=>i._id!==id);
      if(endpoint==="animes") anime = anime.filter(i=>i._id!==id);
      if(endpoint==="games") games = games.filter(i=>i._id!==id);
    } else alert("Delete failed ❌");
  }

  // Particle background
  onMount(()=>{
    const canvas = document.getElementById("particle-canvas") as HTMLCanvasElement;
    if(!canvas) return;
    const ctx = canvas.getContext("2d");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const particles = Array.from({length:80}, ()=>({
      x: Math.random()*canvas.width,
      y: Math.random()*canvas.height,
      r: Math.random()*2+1,
      dx: (Math.random()-0.5)*0.5,
      dy: (Math.random()-0.5)*0.5
    }));

    function draw(){
      if (!ctx) return;
      ctx.clearRect(0,0,canvas.width,canvas.height);
      ctx.fillStyle="rgba(255,255,255,0.3)";
      particles.forEach(p=>{
        ctx.beginPath();
        ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
        ctx.fill();
        p.x+=p.dx;
        p.y+=p.dy;
        if(p.x<0||p.x>canvas.width)p.dx*=-1;
        if(p.y<0||p.y>canvas.height)p.dy*=-1;
      });
      requestAnimationFrame(draw);
    }
    draw();
    window.addEventListener("resize",()=>{canvas.width=window.innerWidth;canvas.height=window.innerHeight});
  });
</script>

<main class="relative bg-gray-900 min-h-screen text-gray-100 overflow-x-hidden">

  <!-- Particle background -->
  <canvas id="particle-canvas" class="absolute inset-0 w-full h-full pointer-events-none"></canvas>

  <!-- Header -->
 <header class="relative z-50 p-6 text-center">
  <h1 class="text-4xl md:text-5xl font-bold mb-4 text-blue-400">NerdTracker</h1>
  <SearchBar on:itemAdded={(e)=>{
    const type = e.detail.type;
    if(type=='Movie') fetchData("movies", d=>movies=d);
    if(type=='Show') fetchData("shows", d=>shows=d);
    if(type=='Anime') fetchData("animes", d=>anime=d);
    if(type=='Game') fetchData("games", d=>games=d);
  }}/>
</header>

  <!-- Tabs with animated underline -->
  <div class="relative z-10 flex justify-center gap-6 mb-8 border-b border-gray-700">
    {#each ["Movies","Shows","Anime","Game"] as tab}
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

  <!-- Grid section -->
<section class="relative z-10 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-6 px-4 md:px-6">

  {#if activeTab === "Movies"}
    {#each movies as item}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/movies/${item._id}`}>
          <img src={item.poster} alt={item.title} class="w-full aspect-[2/3] object-cover"/>
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
    {#each shows as item}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/shows/${item._id}`}>
          <img src={item.poster} alt={item.title} class="w-full aspect-[2/3] object-cover"/>
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
    {#each anime as item}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/animes/${item._id}`}>
          <img src={item.poster} alt={item.title} class="w-full aspect-[2/3] object-cover"/>
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
    {#each games as item}
      <div class="relative bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:scale-105 transform transition duration-300 cursor-pointer group">
        <a href={`/games/${item._id}`}>
          <img src={item.cover ?? item.poster} alt={item.title} class="w-full aspect-[2/3] object-cover"/>
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
</section>
</main>

<style>
  button.selected {
    color: white;
  }
</style>
