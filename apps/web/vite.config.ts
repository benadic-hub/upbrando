import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const srcPath = new URL("./src", import.meta.url).pathname;
const sharedPath = new URL("../../packages/shared/src", import.meta.url).pathname;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:5174",
        changeOrigin: true
      }
    }
  },
  resolve: {
    alias: {
      "@": srcPath,
      "@shared": sharedPath
    }
  }
});
