import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Lade Umgebungsvariablen
  const env = loadEnv(mode, process.cwd(), '');
  
  // Bestimme, ob wir in Produktion sind, basierend auf NODE_ENV
  const isProduction = process.env.NODE_ENV === 'production';
  
  // API-Basis-URL aus Umgebungsvariablen oder Fallback
  const apiBaseUrl = env.API_BASE_URL || 'http://localhost:5001';
  
  // Client-URL aus Umgebungsvariablen oder Fallback
  const clientUrl = env.CLIENT_URL || 'http://localhost:3000';
  
  // Interner API-Schlüssel für sichere Kommunikation zwischen Frontend und Backend
  const internalApiKey = env.INTERNAL_API_KEY || 'development-key-for-local-use-only';
  
  console.log(`Mode: ${mode}, Production: ${isProduction}, API Base URL: ${apiBaseUrl}, Client URL: ${clientUrl}`);
  
  return {
    plugins: [react()],
    optimizeDeps: {
      exclude: ['lucide-react'],
    },
    worker: {
      format: 'es',
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: apiBaseUrl,
          changeOrigin: true,
          secure: false,
          headers: {
            // Diese Header werden an den Proxy-Server gesendet, um die Quelle zu authentifizieren
            'X-API-Key': internalApiKey,
            'Origin': clientUrl,
            'Referer': `${clientUrl}/`,
            // Diese Header helfen, den Vite-Proxy von direkten Browser-Anfragen zu unterscheiden
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log('Proxy error:', err);
            });
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.log('Sending Request:', req.method, req.url);
              
              // Stelle sicher, dass der Accept-Header konsistent ist
              proxyReq.setHeader('Accept', 'application/json');
            });
          }
        },
      },
      // HMR Konfiguration
      hmr: isProduction ? false : {
        host: 'localhost',
        port: 3000,
        protocol: 'ws',
      },
    },
    preview: {
      port: 3000,
    },
    // Definiere Umgebungsvariablen für den Client
    define: {
      'process.env.NODE_ENV': JSON.stringify(isProduction ? 'production' : 'development')
    }
  };
});