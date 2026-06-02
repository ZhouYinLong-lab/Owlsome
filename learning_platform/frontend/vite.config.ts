import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const allowedHosts = (process.env.VITE_PREVIEW_ALLOWED_HOSTS || env.VITE_PREVIEW_ALLOWED_HOSTS || "owlsome.lilystudio.space")
    .split(",")
    .map((host) => host.trim())
    .filter(Boolean);

  return {
    plugins: [react()],
    server: {
      port: 5173
    },
    preview: {
      allowedHosts
    }
  };
});
