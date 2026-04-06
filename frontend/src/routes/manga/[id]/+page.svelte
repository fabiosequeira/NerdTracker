<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { tick } from "svelte";

  let manga: any = null;
  let activeTab: "Details" | "Trailer" = "Details";

  let tabRefs: (HTMLButtonElement | null)[] = [];
  let underlineStyle = "";

  const apiBase = 'https://ntbck.fabioserver.xyz'; // PRODUCTION
  //   const apiBase = 'http://127.0.0.1:8000'; - LOCAL
  
  $: mangaId = $page.params.id;

  async function fetchManga() {
    try {
      const res = await fetch(`${apiBase}/manga/${mangaId}`);
      if (!res.ok) throw new Error("Failed to fetch manga");
      manga = await res.json();
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

  function updateUnderline(index = tabRefs.findIndex(t => t?.classList.contains('selected'))) {
    if (tabRefs[index]) {
      const tab = tabRefs[index];
      underlineStyle = `width: ${tab.offsetWidth}px; transform: translateX(${tab.offsetLeft}px);`;
    }
  }

  onMount(() => {
    fetchManga();
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
    return () => window.removeEventListener("keydown", handleKeydown);
  });

  function handleKeydown(e: KeyboardEvent) {}
</script>

<!-- Particle background -->
<canvas id="particle-canvas" class="absolute inset-0 w-full h-full pointer-events-none"></canvas>

{#if manga}
<main class="min-h-screen bg-gray-900 text-gray-100">

<!-- Hero/Backdrop -->
<div class="relative w-full" style="padding-top: 21%; z-index: 10;">
  <!-- Back Arrow -->
  <a href="/" aria-label="Go back to mangas list" class="absolute top-4 left-4 md:top-6 md:left-6 bg-black/50 rounded-full p-2 hover:bg-black/70 transition z-20">
    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
    </svg>
  </a>

  <!-- Banner -->
    {#if manga.banner_image}
      <img src={manga.banner_image} alt={manga.title} class="absolute w-full h-full object-cover opacity-30" />
    {/if}
  <!-- Poster -->
  {#if manga.poster}
    <img
      src={manga.poster}
      alt={manga.title}
      class="absolute left-6 bottom-[-4rem] md:bottom-[-6rem] w-44 md:w-56 rounded-lg shadow-2xl border-4 border-gray-900 z-20"
    />
  {/if}
</div>

  <!-- Main content -->
<div class="flex flex-col lg:flex-row px-6 md:px-12 mt-[5rem] md:mt-[7rem] gap-10">
  <div class="flex-1 space-y-6">

<!-- Tabs -->
    <div class="bg-gray-900 flex gap-4 mb-6 border-b border-gray-700 relative py-2">
      {#each (["Details", "Trailer"] as ("Details" | "Trailer")[]) as tab, i}
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
        {manga.title}
        <span class="text-gray-400 text-lg md:text-xl">({manga.year ?? "-"})</span>
      </h1>

      <p class="text-gray-300">{manga.summary ?? "-"}</p>

      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
        <p><strong>AniList ID:</strong> {manga.anilist_id ?? "-"}</p>
        <p><strong>Title Native:</strong> {manga.title_native ?? "-"}</p>
        <p><strong>Title Romaji:</strong> {manga.title_romaji ?? "-"}</p>
        <p><strong>Year of Release:</strong> {manga.year ?? "-"}</p>
        <p><strong>Genres:</strong> {manga.genres?.join(", ") ?? "-"}</p>
        <p><strong>Average Score:</strong> {manga.average_score ?? "-"}</p>

      </div>
    </div>
    {/if}

    {#if activeTab === "Trailer"}
      <div class="flex justify-center items-start">
        {#if manga.trailer_id}
          <div class="aspect-video rounded-lg overflow-hidden shadow-lg transform transition-transform duration-300 hover:scale-105 hover:shadow-xl">
            <iframe
              width="100%"
              height="100%"
              src={`https://www.youtube.com/embed/${manga.trailer_id}`}
              frameborder="0"
              allowfullscreen
              title={`Trailer for ${manga.title}`}
            ></iframe>
          </div>
        {:else}
          <p class="text-gray-400">No trailer available.</p>
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
