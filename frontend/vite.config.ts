import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		host: true,       // listen on all network interfaces
		port: 5173,       // your desired port
		strictPort: true, // optional: fail if port is in use
	},
});
