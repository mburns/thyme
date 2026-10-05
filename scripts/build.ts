#!/usr/bin/env node
/// Render the page templates into `dist/` and copy static assets.
///
/// Pages are every `templates/*.html` that does not start with `_` (layouts)
/// and is not `error.html` (rendered by the server with an error message).
/// Serve the result with TrailBase so the pages and the API share an origin:
///   trail run --public-dir dist

import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "fs-extra";
import { render } from "./templates";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TEMPLATES_DIR = path.join(__dirname, "..", "templates");
const STATIC_DIR = path.join(__dirname, "..", "static");
const DIST_DIR = path.join(__dirname, "..", "dist");
const NOT_PAGES = new Set(["error.html"]);

function pageTemplates(dir: string): string[] {
  return fs
    .readdirSync(dir)
    .filter(
      (f) => f.endsWith(".html") && !f.startsWith("_") && !NOT_PAGES.has(f),
    )
    .sort();
}

async function build(): Promise<void> {
  console.log("Starting build...");
  await fs.emptyDir(DIST_DIR);

  const cache = new Map<string, string>();
  const load = (name: string): string => {
    let text = cache.get(name);
    if (text === undefined) {
      text = fs.readFileSync(path.join(TEMPLATES_DIR, name), "utf-8");
      cache.set(name, text);
    }
    return text;
  };

  const pages = pageTemplates(TEMPLATES_DIR);
  for (const name of pages) {
    const html = render(name, load);
    await fs.writeFile(path.join(DIST_DIR, name), html, "utf-8");
    console.log(`  - ${name}`);
  }

  if (await fs.pathExists(STATIC_DIR)) {
    await fs.copy(STATIC_DIR, path.join(DIST_DIR, "static"));
  }
  console.log(`Rendered ${pages.length} pages into ${DIST_DIR}`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  build().catch((error) => {
    console.error("Build failed:", error);
    process.exit(1);
  });
}
