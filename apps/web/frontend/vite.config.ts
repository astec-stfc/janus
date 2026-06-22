import path from "path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/v1": {
        target: process.env.LATTICE_API_URL ?? "http://lattice_api:5000",
        changeOrigin: true,
      },
      "/restframe": {
        target: process.env.RESTFRAME_URL ?? "http://restframe:8000",
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/restframe/, ""),
      },
    },
  },
});
