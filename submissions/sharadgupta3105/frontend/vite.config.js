import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// In dev the frontend runs on its own port and proxies /api + redirects to
// the backend. In production the backend serves the built bundle directly.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:3000',
      '/': {
        target: 'http://localhost:3000',
        bypass: (req) => (req.headers.accept?.includes('text/html') ? null : false),
      },
    },
  },
});
