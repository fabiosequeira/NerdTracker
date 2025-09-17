<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { tick } from "svelte";

  let anime: any = null;
  let activeTab: "Details" | "Episodes" | "Screenshots" | "Videos" = "Details";

  let tabRefs: (HTMLButtonElement | null)[] = [];
  let underlineStyle = "";

  const apiBase = "http://127.0.0.1:8000";
  $: animeId = $page.params.id;

  async function fetchAnime() {
    try {
      const res = await fetch(`${apiBase}/animes/${animeId}`);
      if (!res.ok) throw new Error("Failed to fetch anime");
      anime = await res.json();
      await tick();
      updateUnderline();
    } catch (err) {
      console.error(err);
    }
  }

  function setActive(tab: typeof activeTab, index: number) {
    activeTab = tab;
    updateUnderline(index);
  }

  function updateUnderline(index = tabRefs.findIndex(t => t?.classList.contains("selected"))) {
    if (tabRefs[index]) {
      const tab = tabRefs[index];
      underlineStyle = `width: ${tab.offsetWidth}px; transform: translateX(${tab.offsetLeft}px);`;
    }
  }

  // --- Lightbox state ---
  let showLightbox = false;
  let currentIndex = 0;

  function openLightbox(index: number) {
    currentIndex = index;
    showLightbox = true;
  }

  function closeLightbox() {
    showLightbox = false;
  }

  function prevImage() {
    currentIndex = (currentIndex - 1 + anime.images.length) % anime.images.length;
  }

  function nextImage() {
    currentIndex = (currentIndex + 1) % anime.images.length;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!showLightbox) return;
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") prevImage();
    if (e.key === "ArrowRight") nextImage();
  }

onMount(() => {
  fetchAnime();
  window.addEventListener("keydown", handleKeydown);

  const canvas = document.getElementById("particle-canvas") as HTMLCanvasElement;
  if (canvas) {
    const ctx = canvas.getContext("2d");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const particles = Array.from({ length: 80 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 2 + 1,
      dx: (Math.random() - 0.5) * 0.5,
      dy: (Math.random() - 0.5) * 0.5,
    }));

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "rgba(255,255,255,0.3)";
      particles.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
        p.x += p.dx;
        p.y += p.dy;
        if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
      });
      requestAnimationFrame(draw);
    }
    draw();

    window.addEventListener("resize", () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    });
  }

  return () => {
    window.removeEventListener("keydown", handleKeydown);
  };
});

</script>


  <!-- Particle background -->
  <canvas id="particle-canvas" class="absolute inset-0 w-full h-full pointer-events-none"></canvas>

{#if anime}
<main class="min-h-screen bg-gray-900 text-gray-100">

  <!-- Hero/Backdrop -->
  <div class="relative w-full h-64 md:h-80 lg:h-96 z-10">
    {#if anime.backdrop}
      <div
        class="absolute inset-0 bg-cover bg-top before:content-[''] before:absolute before:inset-0 before:bg-gradient-to-t before:from-gray-900 before:via-transparent"
        style="background-image: url('{anime.backdrop}')"
      ></div>
    {/if}

    <!-- Back Arrow -->
    <a href="/" aria-label="Go back to anime list" class="absolute top-4 left-4 md:top-6 md:left-6 bg-black/50 rounded-full p-2 hover:bg-black/70 transition z-20">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
    </a>

    <!-- Poster -->
    {#if anime.poster}
      <img
        src={anime.poster}
        alt={anime.title}
        class="absolute left-6 bottom-[-4rem] md:bottom-[-6rem] w-44 md:w-56 rounded-lg shadow-2xl border-4 border-gray-900 z-20"
      />
    {/if}
  </div>

  <!-- Main content -->
  <div class="flex flex-col lg:flex-row px-6 md:px-12 mt-[5rem] md:mt-[7rem] gap-10">
    <div class="flex-1 space-y-6">

      <!-- Tabs -->
      <div class="bg-gray-900 flex gap-4 mb-6 border-b border-gray-700 relative py-2">
        {#each (["Details", "Episodes", "Screenshots", "Videos"] as const) as tab, i (tab)}
          <button
            bind:this={tabRefs[i]}
            class="px-4 py-2 font-semibold rounded-md text-gray-200 hover:text-white transition-colors duration-200"
            class:selected={activeTab === tab}
            on:click={() => setActive(tab, i)}
          >
            {tab}
          </button>
        {/each}

        <!-- Sliding underline -->
        <div
          class="absolute bottom-0 h-1 bg-blue-500 transition-all duration-300 rounded-full"
          style={underlineStyle}
        ></div>
      </div>

      <!-- Tab content -->
      <div class="mt-2"></div>
      {#if activeTab === "Details"}
        <div class="bg-gray-800 p-6 md:p-8 rounded-lg shadow-lg space-y-4 animate-fadeIn">
          <h1 class="text-2xl md:text-3xl font-bold">{anime.title} <span class="text-gray-400 text-lg md:text-xl">({anime.year ?? "-"})</span></h1>
          <p class="text-gray-300">{anime.overview ?? "-"}</p>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
            <p><strong>Genres:</strong> {anime.genres?.join(", ") ?? "-"}</p>
            <p><strong>Rating:</strong> {anime.rating ?? "-"} ({anime.rating_count ?? 0} votes)</p>
            <p><strong>Seasons:</strong> {anime.seasons ?? "-"}</p>
            <p><strong>Episodes:</strong> {anime.episodes ?? "-"}</p>
            <p><strong>Popularity:</strong> {anime.popularity ?? "-"}</p>
            <p><strong>Adult:</strong> {anime.adult ? "Yes" : "No"}</p>
            <p><strong>IMDb:</strong> {anime.imdb_id ?? "-"}</p>
            <p><strong>TMDb:</strong> {anime.tmdb_id ?? "-"}</p>
          </div>
        </div>
      {/if}

      {#if activeTab === "Episodes"}
        <div class="bg-gray-800 p-6 md:p-8 rounded-lg shadow-lg animate-fadeIn">
          <h2 class="text-xl font-semibold mb-2">Episodes</h2>
          <p class="text-gray-400">Episodes will be listed here soon 🚧</p>
        </div>
      {/if}

      {#if activeTab === "Screenshots"}
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
          {#if anime.images?.length > 0}
            {#each anime.images.slice(0,12) as img, i}
              <button
                type="button"
                class="p-0 bg-transparent border-none rounded-lg shadow-lg transform transition-transform duration-300 hover:scale-105 hover:-rotate-1 cursor-pointer focus:outline-none"
                on:click={() => openLightbox(i)}
                aria-label={`Open screenshot ${i + 1} from ${anime.title}`}
              >
                <img
                  src={img}
                  alt={`Screenshot ${i + 1} from ${anime.title}`}
                  class="rounded-lg w-full h-auto"
                  draggable="false"
                />
              </button>
            {/each}
          {:else}
            <p class="text-gray-400">No screenshots available.</p>
          {/if}
        </div>

        <!-- Lightbox -->
        {#if showLightbox}
          <div class="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
            <button class="absolute top-6 right-6 text-white text-3xl" on:click={closeLightbox}>×</button>
            <button class="absolute left-4 text-white text-4xl" on:click={prevImage}>‹</button>
            <img src={anime.images[currentIndex]} alt="Screenshot" class="max-h-[90vh] max-w-[90vw] rounded-lg shadow-lg" />
            <button class="absolute right-4 text-white text-4xl" on:click={nextImage}>›</button>
          </div>
        {/if}
      {/if}

      {#if activeTab === "Videos"}
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-8">
          {#if anime.videos?.length > 0}
            {#each anime.videos.slice(0,6) as vid}
              <div class="aspect-video rounded-lg overflow-hidden shadow-lg transform transition-transform duration-300 hover:scale-105 hover:shadow-xl">
                <iframe
                  width="100%"
                  height="100%"
                  src={`https://www.youtube.com/embed/${vid.key}`}
                  frameborder="0"
                  allowfullscreen
                  title={`Video for ${anime.title}`}
                ></iframe>
              </div>
            {/each}
          {:else}
            <p class="text-gray-400">No videos available.</p>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</main>
{/if}

<style>
  button.selected {
    color: white;
    font-weight: bold;
  }

  @keyframes fadeIn {
    0% {opacity: 0; transform: translateY(20px);}
    100% {opacity: 1; transform: translateY(0);}
  }

  .animate-fadeIn {
    animation: fadeIn 0.5s ease forwards;
  }
</style>
