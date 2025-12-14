import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/drop': 'http://127.0.0.1:5002',
      '/search': 'http://127.0.0.1:5002',
      '/status': 'http://127.0.0.1:5002',
      '/api': {
        target: 'http://127.0.0.1:5002',
        changeOrigin: true,
      }
    }
  }
})
