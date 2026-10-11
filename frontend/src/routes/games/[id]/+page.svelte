<script lang="ts">
  import { onMount } from "svelte";
  import { tick } from "svelte";
  import ParticleBackground from "$lib/components/ParticleBackground.svelte";
  import { igdb, onImgError } from "$lib/img";

  export let data: any;
  let game: any = null;
  $: game = data.item;
  let activeTab: "Details" | "Storyline" | "Extras" | "Trophies" | "Screenshots" | "Artworks" | "Videos" = "Details";

  let tabRefs: (HTMLButtonElement | null)[] = [];
  let underlineStyle = "";

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
  let lightboxImages: string[] = [];

  function openLightbox(images: string[], index: number) {
    lightboxImages = images;
    currentIndex = index;
    showLightbox = true;
  }

  function closeLightbox() {
    showLightbox = false;
  }

  function prevImage() {
    currentIndex = (currentIndex - 1 + lightboxImages.length) % lightboxImages.length;
  }

  function nextImage() {
    currentIndex = (currentIndex + 1) % lightboxImages.length;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!showLightbox) return;
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") prevImage();
    if (e.key === "ArrowRight") nextImage();
  }

  onMount(() => {
    tick().then(() => updateUnderline());
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  });
</script>

<!-- Particle background -->
  <ParticleBackground />

{#if game}
<main class="min-h-screen bg-gray-900 text-gray-100">

  <!-- Hero/Backdrop -->
  <div class="relative w-full h-64 md:h-80 lg:h-96 z-10">
    {#if game.screenshots?.length || game.artworks?.length}
      <div
        class="absolute inset-0 bg-cover bg-center before:content-[''] before:absolute before:inset-0 before:bg-gradient-to-t before:from-gray-900 before:via-transparent"
        style="background-image: url('{game.screenshots?.[0] ?? game.artworks?.[0]}');"
      ></div>
    {:else}
      <div class="absolute inset-0 bg-gradient-to-br from-gray-800 to-gray-900"></div>
    {/if}

    <!-- Back Arrow -->
    <a href="/" aria-label="Go back to games list" class="absolute top-4 left-4 md:top-6 md:left-6 bg-black/50 rounded-full p-2 hover:bg-black/70 transition z-20">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
    </a>

    <!-- Cover -->
    {#if game.cover}
      <img
        src={game.cover}
        alt={game.title}
        class="absolute left-6 bottom-[-4rem] md:bottom-[-6rem] w-44 md:w-56 rounded-lg shadow-2xl border-4 border-gray-900 z-20"
      />
    {/if}
  </div>

  <!-- Main content -->
  <div class="flex flex-col lg:flex-row px-6 md:px-12 mt-[5rem] md:mt-[7rem] gap-10">
    <div class="flex-1 space-y-6">

      <!-- Tabs -->
      <div class="bg-gray-900 flex gap-4 mb-6 border-b border-gray-700 relative py-2">
        {#each (["Details", "Storyline", "Extras", "Trophies", "Screenshots", "Artworks"] as const) as tab, i}
          <button
            bind:this={tabRefs[i]}
            class="px-4 py-2 font-semibold rounded-md text-gray-200 hover:text-white transition-colors duration-200"
            class:selected={activeTab === tab}
            on:click={() => setActive(tab, i)}
          >
            {tab}
          </button>
        {/each}

        <div
          class="absolute bottom-0 h-1 bg-blue-500 transition-all duration-300 rounded-full"
          style={underlineStyle}
        ></div>
      </div>

      <!-- Tab content -->
      {#if activeTab === "Details"}
        <div class="bg-gray-800 p-6 md:p-8 rounded-lg shadow-lg space-y-4 animate-fadeIn">
          <h1 class="text-2xl md:text-3xl font-bold">{game.title} <span class="text-gray-400 text-lg md:text-xl">({game.year ?? "-"})</span></h1>
          <p class="text-gray-300">{game.summary ?? "No summary available."}</p>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4 text-sm">
            <p><strong>Genres:</strong> {game.genres?.join(", ") ?? "-"}</p>
            <p><strong>Modes:</strong> {game.game_modes?.join(", ") ?? "-"}</p>
            <p><strong>Platforms:</strong> {game.platforms?.join(", ") ?? "-"}</p>
            <p><strong>Rating:</strong> {game.rating ?? "-"} ({game.rating_count ?? 0} votes)</p>
            <p><strong>Critics:</strong> {game.aggregated_rating ?? "-"} ({game.aggregated_rating_count ?? 0})</p>
            <p><strong>Companies:</strong> {game.involved_companies?.join(", ") ?? "-"}</p>
            <p><strong>Collection:</strong> {game.collection ?? "-"}</p>
            <p><strong>Franchise:</strong> {game.franchise ?? "-"}</p>
          </div>
        </div>
      {/if}

      <!-- Storyline -->
      {#if activeTab === "Storyline"}
        <div class="bg-gray-800 p-6 md:p-8 rounded-lg shadow-lg animate-fadeIn">
          <h2 class="text-xl md:text-2xl font-semibold mb-2">Storyline</h2>
          {#if game.storyline}
            <p class="text-gray-300 whitespace-pre-line">{game.storyline}</p>
          {:else}
            <p class="text-gray-400">No storyline available.</p>
          {/if}
        </div>
      {/if}

{#if activeTab === "Extras"}
<div class="bg-gray-800 p-6 md:p-8 rounded-lg shadow-lg animate-fadeIn space-y-6">
  <h2 class="text-xl font-semibold mb-4">Extras</h2>

  {#if game.dlcs?.length || game.expansions?.length || game.remakes?.length || game.remasters?.length || game.bundles?.length}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {#if game.dlcs?.length}
        <div class="bg-gray-700 p-4 rounded-lg shadow-inner">
          <h3 class="font-semibold mb-2">DLCs</h3>
          <ul class="list-disc list-inside max-h-40 overflow-auto text-gray-200 text-sm">
            {#each game.dlcs as dlc}
              <li>{dlc}</li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if game.expansions?.length}
        <div class="bg-gray-700 p-4 rounded-lg shadow-inner">
          <h3 class="font-semibold mb-2">Expansions</h3>
          <ul class="list-disc list-inside max-h-40 overflow-auto text-gray-200 text-sm">
            {#each game.expansions as expansion}
              <li>{expansion}</li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if game.remakes?.length}
        <div class="bg-gray-700 p-4 rounded-lg shadow-inner">
          <h3 class="font-semibold mb-2">Remakes</h3>
          <ul class="list-disc list-inside max-h-40 overflow-auto text-gray-200 text-sm">
            {#each game.remakes as remake}
              <li>{remake}</li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if game.remasters?.length}
        <div class="bg-gray-700 p-4 rounded-lg shadow-inner">
          <h3 class="font-semibold mb-2">Remasters</h3>
          <ul class="list-disc list-inside max-h-40 overflow-auto text-gray-200 text-sm">
            {#each game.remasters as remaster}
              <li>{remaster}</li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if game.bundles?.length}
        <div class="bg-gray-700 p-4 rounded-lg shadow-inner">
          <h3 class="font-semibold mb-2">Bundles</h3>
          <ul class="list-disc list-inside max-h-40 overflow-auto text-gray-200 text-sm">
            {#each game.bundles as bundle}
              <li>{bundle}</li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  {:else}
    <p class="text-gray-400">No extras available.</p>
  {/if}
</div>
{/if}


      {#if activeTab === "Trophies"}
        <div class="bg-gray-800 p-6 md:p-8 rounded-lg shadow-lg animate-fadeIn">
          <h2 class="text-xl font-semibold mb-2">Trophies / Achievements</h2>
          <p class="text-gray-400">🚧 Coming soon...</p>
        </div>
      {/if}

      {#if activeTab === "Screenshots"}
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6 animate-fadeIn">
          {#if game.screenshots?.length > 0}
            {#each game.screenshots.slice(0,12) as img, i}
              <button
                type="button"
                class="p-0 bg-transparent border-none rounded-lg shadow-lg transform transition-transform duration-300 hover:scale-105 hover:-rotate-1 cursor-pointer"
                on:click={() => openLightbox(game.screenshots, i)}
                aria-label="View screenshot from {game.title}"
              >
                <img loading="lazy" decoding="async" on:error={(e) => onImgError(e, img)} src={igdb(img, "t_screenshot_med")}
                  alt="Screenshot from {game.title}"
                  class="rounded-lg w-full h-auto"
                />
              </button>
            {/each}
          {:else}
            <p class="text-gray-400">No screenshots available.</p>
          {/if}
        </div>
      {/if}

      {#if activeTab === "Artworks"}
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6 animate-fadeIn">
          {#if game.artworks?.length > 0}
            {#each game.artworks.slice(0,12) as art, i}
              <button
                type="button"
                class="p-0 bg-transparent border-none rounded-lg shadow-lg transform transition-transform duration-300 hover:scale-105 hover:-rotate-1 cursor-pointer"
                on:click={() => openLightbox(game.artworks, i)}
                aria-label="View artwork from {game.title}"
              >
                <img loading="lazy" decoding="async" on:error={(e) => onImgError(e, art)} src={igdb(art, "t_screenshot_med")}
                  alt="Artwork from {game.title}"
                  class="rounded-lg w-full h-auto"
                />
              </button>
            {/each}
          {:else}
            <p class="text-gray-400">No artworks available.</p>
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <!-- Lightbox -->
  {#if showLightbox}
    <div class="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
      <button class="absolute top-6 right-6 text-white text-3xl" on:click={closeLightbox}>×</button>
      <button class="absolute left-4 text-white text-4xl" on:click={prevImage}>‹</button>
      <img src={lightboxImages[currentIndex]} alt="Lightbox" class="max-h-[90vh] max-w-[90vw] rounded-lg shadow-lg" />
      <button class="absolute right-4 text-white text-4xl" on:click={nextImage}>›</button>
    </div>
  {/if}
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
