import path from "node:path";
import * as dotenv from "dotenv";
import { reactRouter } from "@react-router/dev/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

dotenv.config({ path: path.resolve(__dirname, ".env") });

// Expose only vars starting with VITE_
const viteEnv = Object.keys(process.env)
  .filter((k) => k.startsWith("VITE_"))
  .reduce<Record<string, string>>((a, k) => {
    a[k] = process.env[k] ?? "";
    return a;
  }, {});

export default defineConfig(() => ({
  define: {
    "process.env": JSON.stringify(viteEnv),
  },
  build: {
    assetsInlineLimit: 0,
  },
  plugins: [reactRouter(), tsconfigPaths({ projects: [path.resolve(__dirname, "tsconfig.json")] })],
  resolve: {
    alias: {
      // Next.js compatibility shims used within web
      "next/link": path.resolve(__dirname, "app/compat/next/link.tsx"),
      "next/navigation": path.resolve(__dirname, "app/compat/next/navigation.ts"),
      "next/script": path.resolve(__dirname, "app/compat/next/script.tsx"),
    },
    dedupe: ["react", "react-dom", "@headlessui/react"],
  },
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/auth": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  optimizeDeps: {
    force: true,
    include: [
      "react",
      "react-dom",
      "react/jsx-runtime",
      "react/jsx-dev-runtime",
      "react-router",
      "next-themes",
      "swr",
      "mobx-react",
      "mobx",
      "@bprogress/core",
      "lucide-react",
      "lodash-es",
      "uuid",
      "axios",
      "file-type",
      "react-popper",
      "@headlessui/react",
      "react-color",
      "@radix-ui/react-scroll-area",
      "date-fns",
      "date-fns/differenceInCalendarDays",
      "clsx",
      "tailwind-merge",
      "rehype-parse",
      "rehype-remark",
      "remark-gfm",
      "remark-stringify",
      "unified",
      "sanitize-html",
      "chroma-js",
      "class-variance-authority",
      "@base-ui-components/react/tooltip",
      "@base-ui-components/react/toast",
      "cookie",
      "set-cookie-parser",
      "use-sync-external-store/shim/index.js",
      "react-hook-form",
      "@atlaskit/pragmatic-drag-and-drop/combine",
      "@atlaskit/pragmatic-drag-and-drop/element/adapter",
      "@atlaskit/pragmatic-drag-and-drop-auto-scroll/element",
      "@atlaskit/pragmatic-drag-and-drop-hitbox/tree-item",
    ],
  },
  // No SSR-specific overrides needed; alias resolves to ESM build
}));
