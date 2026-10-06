import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const here = path.dirname(fileURLToPath(import.meta.url));

// Bundle the browser-side timeline app into dist/static/js/, next to the
// rendered pages. `yarn build:site` renders the templates first (which
// empties dist/), then runs this build.
export default defineConfig({
  root: here,
  build: {
    outDir: path.join(here, "..", "dist", "static", "js"),
    emptyOutDir: false,
    sourcemap: true,
    lib: {
      entry: path.join(here, "timeline", "main.ts"),
      name: "thymeTimeline",
      fileName: () => "timeline.js",
      formats: ["es"],
    },
  },
});
