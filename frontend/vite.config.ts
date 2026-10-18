import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // xfwd envía la IP real del visitante al backend (límites por IP del formulario de contacto).
      "/api": { target: "http://127.0.0.1:8000", xfwd: true },
    },
  },
});
