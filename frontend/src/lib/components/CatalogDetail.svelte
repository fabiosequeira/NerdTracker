<script lang="ts">
	// Detail page for a Book or an Audiobook. It is a personal vault entry: bibliographic facts +
	// the user's own rating / notes / finished date. No progress tracking of any kind.
	import { API_BASE } from '$lib/api';
	import ParticleBackground from '$lib/components/ParticleBackground.svelte';
	import CoverImage from '$lib/components/CoverImage.svelte';
	import StarRating from '$lib/components/StarRating.svelte';
	import {
		fieldLabel,
		formatDate,
		formatRuntime,
		formatTimestamp,
		languageName,
		peopleLine,
		providerLabel,
		recordingLabel,
		seriesLabel
	} from '$lib/media';

	export let item: any;
	export let kind: 'book' | 'audiobook' = 'book';

	const endpoint = kind === 'book' ? 'books' : 'audiobooks';
	const label = kind === 'book' ? 'book' : 'audiobook';
	const today = new Date().toISOString().slice(0, 10);

	// --- personal data editing ----------------------------------------------------------------
	let loadedId: string | undefined;
	let draftNotes = '';
	let draftDate = '';
	let personalMsg = '';
	let personalErr = false;
	let saving = false;

	$: if (item && item._id !== loadedId) {
		loadedId = item._id;
		draftNotes = item.notes ?? '';
		draftDate = item.finished_on ?? '';
		personalMsg = '';
	}
	$: dirty = !!item && (draftNotes.trim() !== (item.notes ?? '') || draftDate !== (item.finished_on ?? ''));

	async function savePersonal(patch: Record<string, unknown>, quiet = false) {
		saving = true;
		personalMsg = '';
		try {
			const res = await fetch(`${API_BASE}/${endpoint}/${item._id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(patch)
			});
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				const d = Array.isArray(body.detail) ? body.detail.map((x: any) => x.msg).join('; ') : body.detail;
				throw new Error(d || 'Could not save');
			}
			const updated = await res.json();
			item = { ...item, personal_rating: updated.personal_rating, notes: updated.notes, finished_on: updated.finished_on, updated_at: updated.updated_at };
			draftNotes = item.notes ?? '';
			draftDate = item.finished_on ?? '';
			personalErr = false;
			if (!quiet) personalMsg = 'Saved ✅';
		} catch (e: any) {
			personalErr = true;
			personalMsg = `${e.message ?? 'Could not save'} ❌`;
		} finally {
			saving = false;
		}
	}

	const saveText = () => savePersonal({ notes: draftNotes, finished_on: draftDate || null });
	const rate = (e: CustomEvent<number | null>) => savePersonal({ personal_rating: e.detail }, true);

	// --- metadata refresh ---------------------------------------------------------------------
	let refreshing = false;
	let refreshMsg = '';
	let refreshErr = false;
	let refreshIssues: string[] = [];

	async function refresh() {
		refreshing = true;
		refreshMsg = '';
		refreshIssues = [];
		try {
			const res = await fetch(`${API_BASE}/${endpoint}/${item._id}/refresh`, { method: 'POST' });
			const body = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Refresh failed');
			item = body.item;
			const changed: string[] = body.changed_fields ?? [];
			refreshErr = false;
			refreshMsg = changed.length ? `Updated: ${changed.map(fieldLabel).join(', ')}` : 'Already up to date';
			refreshIssues = [
				...Object.entries(body.providers ?? {})
					.filter(([, s]: any) => s.status === 'error' || s.status === 'timeout')
					.map(([n, s]: any) => `${providerLabel(n)}: ${s.detail ?? s.status}`),
				...(body.warnings ?? [])
			];
		} catch (e: any) {
			refreshErr = true;
			refreshMsg = e.message ?? 'Refresh failed';
		} finally {
			refreshing = false;
		}
	}

	// --- derived display ------------------------------------------------------------------------
	let expanded = false;
	$: facts = item
		? ([
				['Published', formatDate(item.published_date)],
				['First published', item.first_published_year ? String(item.first_published_year) : ''],
				['Publisher', item.publisher],
				['Edition', item.edition],
				[kind === 'book' ? 'Pages' : 'Runtime', kind === 'book' ? (item.page_count ? String(item.page_count) : '') : formatRuntime(item.runtime_minutes)],
				['Recording', kind === 'audiobook' ? recordingLabel(item.recording_type) : ''],
				['Language', languageName(item.language)],
				['ISBN-13', item.isbn_13],
				['ISBN-10', item.isbn_10],
				['ASIN', kind === 'audiobook' ? item.asin : ''],
				['Other ISBNs', (item.other_isbns ?? []).join(', ')]
			] as [string, string | null | undefined][]).filter(([, v]) => !!v)
		: [];
	$: longDescription = (item?.description ?? '').length > 600;
</script>

<main class="relative min-h-screen bg-gray-900 text-gray-100 overflow-x-hidden">
	<ParticleBackground />

	{#if !item}
		<div class="relative z-10 max-w-xl mx-auto p-10 text-center space-y-4">
			<p class="text-2xl">😕 Couldn't load this {label}</p>
			<p class="text-gray-400">It may have been removed, or the server is unreachable.</p>
			<a href="/" class="inline-block text-blue-400 hover:underline">← Back to NerdTracker</a>
		</div>
	{:else}
		<div class="relative z-10 max-w-5xl mx-auto px-4 md:px-6 py-8 space-y-8">
			<a href="/" class="text-blue-400 hover:underline text-sm">← Back to NerdTracker</a>

			<!-- Hero -->
			<section class="flex flex-col md:flex-row gap-8">
				<div class="w-48 md:w-60 shrink-0 mx-auto md:mx-0 rounded-xl overflow-hidden shadow-2xl bg-gray-800">
					<CoverImage src={item.cover} alt={item.title} {kind} eager />
				</div>

				<div class="space-y-3 min-w-0">
					<h1 class="text-3xl md:text-4xl font-bold text-blue-400 break-words">{item.title}</h1>
					{#if item.subtitle}<p class="text-lg text-gray-300">{item.subtitle}</p>{/if}
					{#if item.authors?.length}<p class="text-gray-200">✍️ {item.authors.join(', ')}</p>{/if}
					{#if kind === 'audiobook' && item.narrators?.length}<p class="text-gray-200">🎙️ Narrated by {item.narrators.join(', ')}</p>{/if}
					{#if item.series?.name}<p class="text-blue-300">📚 {seriesLabel(item.series)}</p>{/if}

					<div class="flex flex-wrap gap-2">
						{#if kind === 'audiobook' && item.recording_type}
							<span class="px-2 py-0.5 rounded text-xs {item.recording_type === 'abridged' ? 'bg-amber-600/80' : 'bg-emerald-700/80'}">{recordingLabel(item.recording_type)}</span>
						{/if}
						{#each item.genres ?? [] as g}<span class="bg-blue-600/80 px-2 py-0.5 rounded text-xs">{g}</span>{/each}
					</div>

					{#if item.level === 'work'}
						<p class="text-xs text-amber-300 bg-amber-900/30 border border-amber-700/50 rounded p-2">
							No specific edition could be identified for this {label}, so only work-level information is shown.
						</p>
					{/if}

					{#if facts.length}
						<dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm pt-2">
							{#each facts as [k, v]}
								<dt class="text-gray-500">{k}</dt>
								<dd class="text-gray-200 break-words">{v}</dd>
							{/each}
						</dl>
					{/if}
				</div>
			</section>

			{#if item.description}
				<section class="space-y-2">
					<h2 class="text-xl font-semibold">About</h2>
					<p class="text-gray-300 whitespace-pre-line leading-relaxed {longDescription && !expanded ? 'line-clamp-6' : ''}">{item.description}</p>
					{#if longDescription}
						<button class="text-blue-400 text-sm hover:underline" on:click={() => (expanded = !expanded)}>{expanded ? 'Show less' : 'Show more'}</button>
					{/if}
				</section>
			{/if}

			{#if item.contributors?.length}
				<section class="space-y-1">
					<h2 class="text-xl font-semibold">Contributors</h2>
					<ul class="text-sm text-gray-300">
						{#each item.contributors as c}<li>{c.name} <span class="text-gray-500">· {c.role}</span></li>{/each}
					</ul>
				</section>
			{/if}

			<!-- Personal -->
			<section class="bg-gray-800/80 rounded-xl p-5 space-y-4">
				<h2 class="text-xl font-semibold">My notes</h2>
				<div class="flex flex-wrap items-center gap-3">
					<span class="text-gray-400 text-sm">My rating</span>
					<StarRating value={item.personal_rating} editable disabled={saving} on:change={rate} />
					{#if item.personal_rating}<span class="text-sm text-gray-400">{item.personal_rating} / 5</span>{/if}
				</div>
				<div class="flex flex-wrap items-center gap-3">
					<label for="finished" class="text-gray-400 text-sm">Finished on</label>
					<input id="finished" type="date" max={today} bind:value={draftDate} class="bg-gray-700 text-gray-100 rounded px-2 py-1" />
				</div>
				<div>
					<label for="notes" class="sr-only">Notes</label>
					<textarea id="notes" rows="5" maxlength="10000" bind:value={draftNotes} placeholder="Thoughts, favourite parts, who to recommend it to..."
						class="w-full bg-gray-700 text-gray-100 rounded p-2 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-400"></textarea>
				</div>
				<div class="flex items-center gap-3">
					<button on:click={saveText} disabled={!dirty || saving}
						class="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed">{saving ? 'Saving…' : 'Save'}</button>
					{#if personalMsg}<span class="text-sm {personalErr ? 'text-red-400' : 'text-green-400'}" role="status">{personalMsg}</span>{/if}
				</div>
			</section>

			<!-- Metadata / sources -->
			<section class="space-y-3 pb-10">
				<div class="flex flex-wrap items-center gap-3">
					<h2 class="text-xl font-semibold">Metadata</h2>
					<button on:click={refresh} disabled={refreshing} class="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-sm disabled:opacity-50">
						{refreshing ? 'Refreshing…' : '↻ Refresh metadata'}
					</button>
					{#if refreshMsg}<span class="text-sm {refreshErr ? 'text-red-400' : 'text-green-400'}" role="status">{refreshMsg}</span>{/if}
				</div>
				<p class="text-xs text-gray-500">Refreshing updates the book information only. Your rating, notes and dates are never touched.</p>
				{#each refreshIssues as issue}<p class="text-xs text-amber-300">⚠️ {issue}</p>{/each}

				{#if item.sources?.length}
					<ul class="text-sm text-gray-300 space-y-1">
						{#each item.sources as s}
							<li>
								{#if s.url?.startsWith('https://')}<a href={s.url} target="_blank" rel="noopener noreferrer" class="text-blue-400 hover:underline">{providerLabel(s.provider)}</a>{:else}{providerLabel(s.provider)}{/if}
								<span class="text-gray-500">· {s.level === 'work' ? 'work' : 'edition'}{s.provider_id ? ` · ${s.provider_id}` : ''}</span>
							</li>
						{/each}
					</ul>
				{/if}
				<p class="text-xs text-gray-500">
					Added {formatTimestamp(item.added_at)}{#if item.metadata_refreshed_at} · metadata updated {formatTimestamp(item.metadata_refreshed_at)}{/if}
				</p>
			</section>
		</div>
	{/if}
</main>
