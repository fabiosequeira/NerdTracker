
<script lang="ts">
  import { onMount, tick } from "svelte";
  import ParticleBackground from "$lib/components/ParticleBackground.svelte";
  import { tmdb, onImgError } from "$lib/img";
  import YouTubeEmbed from "$lib/components/YouTubeEmbed.svelte";

  export let data: any;

  let anime: any = null;
  $: anime = data.item;

  type Episode = {
    season: number;
    episode: number;
    title?: string | null;
    overview?: string | null;
    air_date?: string | null;
    still?: string | null;
  };

  type Tab = "Details" | "Episodes" | "Screenshots" | "Videos";

  let activeTab: Tab = "Details";
  let tabRefs: (HTMLButtonElement | null)[] = [];
  let underlineStyle = "";

  let selectedSeason: number | null = null;
  let grouped: Record<number, Episode[]> = {};
  let seasons: number[] = [];
  let currentEpisodes: Episode[] = [];

  function groupBySeason(
    episodes: Episode[]
  ): Record<number, Episode[]> {
    const sorted = [...episodes].sort((a, b) => {
      if (a.season !== b.season) {
        return a.season - b.season;
      }
      return a.episode - b.episode;
    });

    return sorted.reduce<Record<number, Episode[]>>((acc, ep) => {
      if (!acc[ep.season]) {
        acc[ep.season] = [];
      }

      acc[ep.season].push(ep);
      return acc;
    }, {});
  }

  $: grouped = groupBySeason(
    (anime?.episodes_list ?? []) as Episode[]
  );

  $: seasons = Object.keys(grouped)
    .map(Number)
    .sort((a, b) => {
      if (a === 0) return 1;
      if (b === 0) return -1;
      return a - b;
    });

  $: if (seasons.length > 0 && selectedSeason === null) {
    selectedSeason = seasons.includes(1) ? 1 : seasons[0];
  }

  $: if (
    selectedSeason !== null &&
    seasons.length > 0 &&
    !seasons.includes(selectedSeason)
  ) {
    selectedSeason = seasons.includes(1) ? 1 : seasons[0];
  }

  $: currentEpisodes =
    selectedSeason !== null ? grouped[selectedSeason] ?? [] : [];

  function setActive(tab: Tab, index: number): void {
    activeTab = tab;
    updateUnderline(index);
  }

  function updateUnderline(
    index: number = tabRefs.findIndex((tab) =>
      tab?.classList.contains("selected")
    )
  ): void {
    const tab = tabRefs[index];

    if (tab) {
      underlineStyle = `width: ${tab.offsetWidth}px; transform: translateX(${tab.offsetLeft}px);`;
    }
  }

  let showLightbox = false;
  let currentIndex = 0;

  function openLightbox(index: number): void {
    currentIndex = index;
    showLightbox = true;
  }

  function closeLightbox(): void {
    showLightbox = false;
  }

  function prevImage(): void {
    const images = anime?.images;
    if (!images?.length) return;

    currentIndex =
      (currentIndex - 1 + images.length) % images.length;
  }

  function nextImage(): void {
    const images = anime?.images;
    if (!images?.length) return;

    currentIndex = (currentIndex + 1) % images.length;
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (!showLightbox) return;

    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") prevImage();
    if (e.key === "ArrowRight") nextImage();
  }

  onMount(() => {
    tick().then(() => updateUnderline());

    window.addEventListener("keydown", handleKeydown);

    return () => {
      window.removeEventListener("keydown", handleKeydown);
    };
  });
</script>



  <!-- Particle background -->
  <ParticleBackground />

{#if anime}
<main class="min-h-screen bg-gray-900 text-gray-100">

  <!-- Hero/Backdrop -->
  <div class="relative w-full h-64 md:h-80 lg:h-96 z-10">
    {#if anime.backdrop}
      <div
        class="absolute inset-0 bg-cover bg-top before:content-[''] before:absolute before:inset-0 before:bg-gradient-to-t before:from-gray-900 before:via-transparent"
        style="background-image: url('{tmdb(anime.backdrop, "w1280")}')"
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
        src={tmdb(anime.poster, "w500")}
      on:error={(e) => onImgError(e, anime.poster)}
      decoding="async"
      fetchpriority="high"
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
        <div class="space-y-6 animate-fadeIn">

          {#if seasons.length > 0}

            <div class="bg-gray-800 p-6 rounded-lg shadow-lg">

              <!-- Header -->
              <div class="flex items-center justify-between mb-4">

                <!-- Season Dropdown -->
                <select
                  bind:value={selectedSeason}
                  class="bg-gray-700 text-white px-3 py-2 rounded outline-none"
                >
                  {#each seasons as season}
                    <option value={season}>
                      {season == 0 ? "Specials" : `Season ${season}`}
                    </option>
                  {/each}
                </select>

                <!-- Episode count -->
                <span class="text-sm text-gray-400">
                  {currentEpisodes.length} episodes
                </span>

              </div>

              <!-- Episodes list -->
              <div class="space-y-4">

                {#each currentEpisodes as ep}
                  <div class="flex gap-4 bg-gray-700 p-4 rounded-lg hover:bg-gray-600 transition group">

                    <!-- Thumbnail -->
                    {#if ep.still}
                      <img
                        loading="lazy"
                        decoding="async"
                        on:error={(e) => onImgError(e, ep.still)}
                        src={tmdb(ep.still, "w300")}
                        alt={ep.title}
                        class="w-32 h-20 object-cover rounded"
                      />
                    {:else}
                      <div class="w-32 h-20 bg-gray-600 flex items-center justify-center text-xs text-gray-300 rounded">
                        No Image
                      </div>
                    {/if}

                    <!-- Info -->
                    <div class="flex-1">

                      <!-- Title -->
                      <h3 class="font-semibold text-white">
                        S{String(ep.season).padStart(2, "0")}E{String(ep.episode).padStart(2, "0")}
                        — {ep.title ?? "Untitled"}
                      </h3>

                      <!-- Overview -->
                      <p class="text-sm text-gray-300 line-clamp-2">
                        {ep.overview ?? "No description available."}
                      </p>

                      <!-- Footer -->
                      <div class="flex items-center justify-between mt-2">

                        <!-- Air date -->
                        <p class="text-xs text-gray-400">
                          {ep.air_date ?? "Unknown date"}
                        </p>

                        <!-- Future Play Button -->
                        <!--
                        <button
                          class="opacity-0 group-hover:opacity-100 transition text-sm bg-blue-500 hover:bg-blue-600 px-3 py-1 rounded"
                        >
                          ▶ Play
                        </button>
                        -->

                      </div>

                    </div>

                  </div>
                {/each}

              </div>

            </div>

          {:else}
            <div class="bg-gray-800 p-6 rounded-lg text-center text-gray-400">
              No episodes available.
            </div>
          {/if}

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
                <img loading="lazy" decoding="async" on:error={(e) => onImgError(e, img)} src={tmdb(img, "w500")}
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
                <YouTubeEmbed id={vid.key} title={`Video for ${anime.title}`} />
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
