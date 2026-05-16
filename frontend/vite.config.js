import { defineConfig } from 'vite'
import { default as react } from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,   // fail instead of silently picking a different port
  },
})
