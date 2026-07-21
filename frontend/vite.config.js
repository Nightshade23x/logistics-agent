import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Python backend is exposed by ../api_server.py (FastAPI).
// Run it with: uvicorn api_server:app --reload --port 8000
// This dev-server proxy forwards /api/* to it so the frontend never
// needs to hardcode a backend origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
