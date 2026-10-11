<script lang="ts">
	// Replaces 7 copy-pasted particle snippets. Differences that matter for speed:
	//  - canvas is sized to the viewport (the home page used to size it to the whole *document*)
	//  - the animation loop and resize listener are cleaned up on unmount (they used to leak, so
	//    every visit to a page stacked another never-ending loop)
	//  - all particles are drawn in one path per frame, and nothing animates for users who prefer
	//    reduced motion
	import { onMount } from 'svelte';

	export let count = 80;

	let canvas: HTMLCanvasElement;

	onMount(() => {
		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		let raf = 0;
		let resizeRaf = 0;

		function resize() {
			canvas.width = window.innerWidth;
			canvas.height = window.innerHeight;
		}
		resize();

		const total = window.innerWidth < 640 ? Math.round(count / 2) : count;
		const particles = Array.from({ length: total }, () => ({
			x: Math.random() * canvas.width,
			y: Math.random() * canvas.height,
			r: Math.random() * 2 + 1,
			dx: (Math.random() - 0.5) * 0.5,
			dy: (Math.random() - 0.5) * 0.5
		}));

		function draw() {
			ctx!.clearRect(0, 0, canvas.width, canvas.height);
			ctx!.fillStyle = 'rgba(255,255,255,0.3)';
			ctx!.beginPath();
			for (const p of particles) {
				ctx!.moveTo(p.x + p.r, p.y);
				ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
				if (!reduceMotion) {
					p.x += p.dx;
					p.y += p.dy;
					if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
					if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
				}
			}
			ctx!.fill();
			if (!reduceMotion) raf = requestAnimationFrame(draw);
		}
		draw();

		function onResize() {
			cancelAnimationFrame(resizeRaf);
			resizeRaf = requestAnimationFrame(() => {
				resize();
				for (const p of particles) {
					p.x = Math.min(p.x, canvas.width);
					p.y = Math.min(p.y, canvas.height);
				}
				if (reduceMotion) draw();
			});
		}
		window.addEventListener('resize', onResize);

		return () => {
			cancelAnimationFrame(raf);
			cancelAnimationFrame(resizeRaf);
			window.removeEventListener('resize', onResize);
		};
	});
</script>

<canvas bind:this={canvas} class="fixed inset-0 w-full h-full pointer-events-none" aria-hidden="true"
></canvas>
