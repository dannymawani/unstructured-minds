import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import checker from 'vite-plugin-checker'
import path from 'path'

// Backend URL: use VITE_API_PROXY_TARGET for Docker (http://backend:8000),
// falls back to http://localhost:8000 for local dev without Docker
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig(async () => {
  const plugins = [
    react(),
    tailwindcss(),
    checker({ typescript: { tsconfigPath: './tsconfig.app.json' } }),
  ]

  if (process.env.ANALYZE) {
    const { visualizer } = await import('rollup-plugin-visualizer')
    plugins.push(
      visualizer({
        open: true,
        filename: 'dist/stats.html',
        gzipSize: true,
      }) as never
    )
  }

  return {
    envDir: path.resolve(__dirname, '..'),
    plugins,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (id.includes('node_modules')) {
              if (id.includes('react-dom') || id.includes('react-router') || id.includes('/react/')) {
                return 'vendor-react'
              }
              if (id.includes('@milkdown') || id.includes('prosemirror')) {
                return 'vendor-milkdown'
              }
              if (id.includes('lucide-react')) {
                return 'vendor-icons'
              }
            }
          },
        },
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
