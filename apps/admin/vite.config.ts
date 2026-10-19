import path from "node:path";
import * as dotenv from "dotenv";
import { reactRouter } from "@react-router/dev/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { joinUrlPath } from "@plane/utils";

dotenv.config({ path: path.resolve(__dirname, ".env") });

// Expose only vars starting with VITE_
const viteEnv = Object.keys(process.env)
  .filter((k) => k.startsWith("VITE_"))
  .reduce<Record<string, string>>((a, k) => {
    a[k] = process.env[k] ?? "";
    return a;
  }, {});

const basePath = joinUrlPath(process.env.VITE_ADMIN_BASE_PATH ?? "", "/") ?? "/";

export default defineConfig(() => ({
  base: basePath,
  define: {
    "process.env": JSON.stringify(viteEnv),
  },
  build: {
    assetsInlineLimit: 0,
  },
  plugins: [reactRouter(), tsconfigPaths({ projects: [path.resolve(__dirname, "tsconfig.json")] })],
  resolve: {
    alias: {
      // Next.js compatibility shims used within admin
      "next/link": path.resolve(__dirname, "app/compat/next/link.tsx"),
      "next/navigation": path.resolve(__dirname, "app/compat/next/navigation.ts"),
    },
    dedupe: ["react", "react-dom"],
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
    ],
  },
  // No SSR-specific overrides needed; alias resolves to ESM build
}));
