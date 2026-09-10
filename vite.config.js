import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // in sviluppo puoi lasciare VITE_API_URL vuoto e usare questo proxy verso il backend locale
    proxy: { "/api": "http://localhost:8000" },
  },
});
