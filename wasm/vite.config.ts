import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const here = path.dirname(fileURLToPath(import.meta.url));

// Bundle the handlers into one ES module for `jco componentize`. The WASI and
// TrailBase host interfaces are provided by the runtime and stay external.
export default defineConfig({
  root: here,
  build: {
    outDir: path.join(here, "dist"),
    emptyOutDir: true,
    minify: false,
    lib: {
      entry: path.join(here, "src", "index.ts"),
      name: "thyme",
      fileName: "index",
      formats: ["es"],
    },
    rollupOptions: {
      preserveEntrySignatures: "strict",
      external: /(wasi|trailbase):.*/,
    },
  },
});
