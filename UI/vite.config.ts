import { defineConfig } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',      // already passed via CLI flag, but explicit here too
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_API_PROXY_TARGET || "http://localhost:8008",
        changeOrigin: true,
      },
    },
    watch: {
      usePolling: true,   // required for Docker volume mounts — inotify doesn't work
      interval: 1000,     // poll every 1s (increase to 2000 if CPU usage is high)
    },
  },
})
