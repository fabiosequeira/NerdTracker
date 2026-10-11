<script lang="ts">
  import { onMount } from "svelte";
  import { tick } from "svelte";
  import ParticleBackground from "$lib/components/ParticleBackground.svelte";
  import { comicvine, onImgError } from "$lib/img";

  export let data: any;
  let comic: any = null;
  $: comic = data.item;
  let activeTab: "Details" | "Issues" = "Details";

  let tabRefs: (HTMLButtonElement | null)[] = [];
  let underlineStyle = "";

  function setActive(tab: typeof activeTab, index: number) {
    activeTab = tab;
    updateUnderline(index);
  }

  function updateUnderline(index = tabRefs.findIndex(t => t?.classList.contains('selected'))) {
    if (tabRefs[index]) {
      const tab = tabRefs[index];
      underlineStyle = `width: ${tab.offsetWidth}px; transform: translateX(${tab.offsetLeft}px);`;
    }
  }

  onMount(() => {
    tick().then(() => updateUnderline());
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  });

  function handleKeydown(e: KeyboardEvent) {}
</script>

<!-- Particle background -->
<ParticleBackground />

{#if comic}
<main class="min-h-screen bg-gray-900 text-gray-100">

<!-- Hero/Backdrop -->
<div class="relative w-full h-64 md:h-80 lg:h-96 z-10">
  <!-- Back Arrow -->
  <a href="/" aria-label="Go back to comics list" class="absolute top-4 left-4 md:top-6 md:left-6 bg-black/50 rounded-full p-2 hover:bg-black/70 transition z-20">
    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
    </svg>
  </a>

  <!-- Cover -->
  {#if comic.poster}
    <img
      src={comicvine(comic.poster)}
      on:error={(e) => onImgError(e, comic.poster)}
      decoding="async"
      fetchpriority="high"
      alt={comic.title}
      class="absolute left-6 bottom-[-4rem] md:bottom-[-6rem] w-44 md:w-56 rounded-lg shadow-2xl border-4 border-gray-900 z-20"
    />
  {/if}
</div>

  <!-- Main content -->
<div class="flex flex-col lg:flex-row px-6 md:px-12 mt-[5rem] md:mt-[7rem] gap-10">
  <div class="flex-1 space-y-6">

<!-- Tabs -->
    <div class="bg-gray-900 flex gap-4 mb-6 border-b border-gray-700 relative py-2">
      {#each (["Details", "Issues"] as ("Details" | "Issues")[]) as tab, i}
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
      <h1 class="text-2xl md:text-3xl font-bold">
        {comic.title}
        <span class="text-gray-400 text-lg md:text-xl">({comic.year ?? "-"})</span>
      </h1>

      <p class="text-gray-300">{comic.summary ?? "-"}</p>

      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
        <p><strong>Publisher:</strong> {comic.publisher ?? "-"}</p>
        <p><strong>Issues:</strong> {comic.count_of_issues ?? "-"}</p>
        <p><strong>ComicVine ID:</strong> {comic.comicvine_id ?? "-"}</p>
        <p><a href={comic.site_detail_url} target="_blank" class="text-blue-400 hover:underline">
          View on ComicVine
        </a></p>
      </div>
    </div>
    {/if}

    {#if activeTab === "Issues"}
    <div class="bg-gray-800 p-6 rounded-lg text-gray-300 animate-fadeIn">
      <p>This comic has <strong>{comic.count_of_issues ?? 0}</strong> issues.</p>
      <p class="text-sm text-gray-400 mt-2">
        (Coming soon.)
      </p>
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
