// import adapter from '@sveltejs/adapter-auto';
// import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// export default {
// 	preprocess: vitePreprocess(),
// 	kit: {
// 		adapter: adapter({
// 			out: 'build'
// 		})
// 	}
// };

import adapter from '@sveltejs/adapter-node';
export default {
  kit: {
    adapter: adapter(),
  }
};

