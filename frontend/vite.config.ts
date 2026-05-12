import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

/**
 * MyPipelineHero Phase 1 frontend build (H.1.2).
 *
 * Each entry in `entries/` becomes a separately-built bundle.
 * Cross-bundle dependencies are PROHIBITED. Shared code lives in
 * `src/modules/`.
 *
 * Tailwind 4 is integrated via the official Vite plugin
 * (`@tailwindcss/vite`). No PostCSS config, no autoprefixer — Tailwind 4
 * uses Lightning CSS internally for both compilation and vendor
 * prefixing.
 *
 * The Django side reads the produced manifest via django-vite. In dev
 * (`make up`), Django proxies `/vite/` to this dev server through Nginx
 * (see backend/docker/nginx/dev.conf).
 */
export default defineConfig(({ mode }) => {
  const isDev = mode === "development";

  return {
    root: fileURLToPath(new URL("./", import.meta.url)),

    // The base path matches the Nginx /vite/ proxy mount in dev so
    // django-vite produces URLs the browser can reach through Nginx.
    base: isDev ? "/vite/" : "/static/",

    publicDir: false,

    plugins: [tailwindcss()],

    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },

    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      cors: true,
      hmr: {
        // Browser connects to Nginx on port 80, which proxies to vite:5173.
        host: "mph.local",
        protocol: "ws",
        clientPort: 80,
        path: "/vite/",
      },
      watch: {
        // Docker bind-mount file events are flaky on macOS/Windows
        // without polling.
        usePolling: true,
        interval: 200,
      },
    },

    build: {
      manifest: "manifest.json",
      outDir: "dist",
      emptyOutDir: true,
      sourcemap: true,
      rollupOptions: {
        input: {
          tenant_portal: fileURLToPath(
            new URL("./src/entries/tenant_portal.ts", import.meta.url),
          ),
          platform_console: fileURLToPath(
            new URL("./src/entries/platform_console.ts", import.meta.url),
          ),
          login_landing: fileURLToPath(
            new URL("./src/entries/login_landing.ts", import.meta.url),
          ),
          email_template_preview: fileURLToPath(
            new URL(
              "./src/entries/email_template_preview.ts",
              import.meta.url,
            ),
          ),
        },
      },
    },
  };
});