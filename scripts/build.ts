#!/usr/bin/env node

import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "fs-extra";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TEMPLATES_DIR = path.join(__dirname, "..", "templates");
const STATIC_DIR = path.join(__dirname, "..", "static");
const DIST_DIR = path.join(__dirname, "..", "dist");

// Simple template engine to replace Jinja2
class SimpleTemplateEngine {
  private templates: Map<string, string> = new Map();

  constructor(private templatesDir: string) {}

  async loadTemplate(name: string): Promise<string> {
    if (this.templates.has(name)) {
      // biome-ignore lint/style/noNonNullAssertion: TODO
      return this.templates.get(name)!;
    }

    const templatePath = path.join(this.templatesDir, name);
    const content = await fs.readFile(templatePath, "utf-8");
    this.templates.set(name, content);
    return content;
  }

  // biome-ignore lint/suspicious/noExplicitAny: TODO
  render(templateContent: string, data: Record<string, any> = {}): string {
    let result = templateContent;

    // Simple variable replacement {{ variable }}
    for (const [key, value] of Object.entries(data)) {
      const regex = new RegExp(`{{\\s*${key}\\s*}}`, "g");
      result = result.replace(regex, String(value));
    }

    // Handle extends and blocks (simplified)
    const extendsMatch = result.match(/{%\s*extends\s+['"]([^'"]+)['"]\s*%}/);
    if (extendsMatch) {
      // const baseTemplate = extendsMatch[1]; // TODO: Implement base template support
      // For now, just remove the extends directive
      result = result.replace(/{%\s*extends\s+['"][^'"]+['"]\s*%}/, "");
    }

    // Remove block markers for now
    result = result.replace(/{%\s*block\s+\w+\s*%}/g, "");
    result = result.replace(/{%\s*endblock\s*%}/g, "");

    return result;
  }
}

async function build(): Promise<void> {
  console.log("Starting build...");

  // 1. Clean and create the dist directory
  if (await fs.pathExists(DIST_DIR)) {
    await fs.remove(DIST_DIR);
  }
  await fs.ensureDir(DIST_DIR);

  // 2. Set up template engine
  const engine = new SimpleTemplateEngine(TEMPLATES_DIR);

  // 3. Find and render page templates (those not starting with '_')
  const pageTemplates = [
    "index.html",
    "about.html",
    "movies.html",
    "persons.html",
    "person.html",
    "title.html",
    "genres.html",
    "top-rated.html",
    "short.html",
    "video.html",
    "videogame.html",
    "tv.html",
    "search.html",
  ];

  console.log(`Found page templates: ${pageTemplates.join(", ")}`);

  for (const templateName of pageTemplates) {
    try {
      const templateContent = await engine.loadTemplate(templateName);
      const renderedHtml = engine.render(templateContent);

      const outputPath = path.join(DIST_DIR, templateName);
      await fs.ensureDir(path.dirname(outputPath));

      await fs.writeFile(outputPath, renderedHtml, "utf-8");
      console.log(`  - Rendered ${templateName} -> ${outputPath}`);
    } catch (error) {
      console.error(`  - Error rendering ${templateName}:`, error);
    }
  }

  // 4. Copy static assets if they exist
  if (await fs.pathExists(STATIC_DIR)) {
    await fs.copy(STATIC_DIR, path.join(DIST_DIR, "static"));
    console.log("Copied static assets.");
  } else {
    // Create an empty static dir in dist so it can be served
    await fs.ensureDir(path.join(DIST_DIR, "static"));
    console.log("Created empty static directory.");
  }

  console.log('\nBuild complete! Your static site is in the "dist" directory.');
}

async function main(): Promise<void> {
  try {
    await build();
  } catch (error) {
    console.error("Build failed:", error);
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
