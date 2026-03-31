import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
  },
  define: {
    'import.meta.vitest': 'undefined',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    env: {
      VITE_API_URL: 'https://api.example.com',
      VITE_COGNITO_DOMAIN: 'https://auth.example.com',
      VITE_COGNITO_CLIENT_ID: 'test-client-id',
      VITE_COGNITO_REDIRECT_URI: 'https://app.example.com/callback',
    },
  },
} as import('vitest/config').UserConfig)
