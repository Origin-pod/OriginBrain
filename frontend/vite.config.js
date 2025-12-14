import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
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
