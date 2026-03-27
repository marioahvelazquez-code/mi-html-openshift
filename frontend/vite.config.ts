import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || "http://localhost:8001";

export default defineConfig({
  plugins: [react()],
  base: "/",
  //Mario Necesario para descargar PPT/PPTX 
  assetsInclude: ["**/*.ppt", "**/*.pptx", "**/*.PPT", "**/*.PPTX"],

  server: {
    host: true,
    port: 5180,
    allowedHosts: ["localhost", "frontend"],

    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
