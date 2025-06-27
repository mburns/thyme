#!/usr/bin/env node

console.log("Thyme - IMDB Data Browser");
console.log("=========================");
console.log("");
console.log("Available commands:");
console.log("  npm run dev:setup    - Complete development environment setup");
console.log(
  "  npm run check-deps   - Check if required system dependencies are installed",
);
console.log("  npm run test         - Run tests and validation");
console.log("  npm run test:search  - Test FTS5 search functionality");
console.log("  npm run test:import  - Run import tests");
console.log("  npm run type-check   - Run TypeScript type checking");
console.log("  npm run lint         - Run linting checks");
console.log("  npm run lint:fix     - Fix linting issues");
console.log("  npm run format       - Format code with Prettier");
console.log("  npm run clean        - Clean build artifacts");
console.log(
  "  npm run clean:all    - Clean everything (build artifacts + database)",
);
console.log("  npm run build        - Build static site");
console.log("  npm run build:watch  - Build static site with file watching");
console.log("  npm run import:data  - Import IMDB data (memory optimized)");
console.log(
  "  npm run import:test  - Import limited IMDB data for testing (1000 entries per file)",
);
console.log("  npm run info         - Show project information");
console.log("");
console.log("Development:");
console.log("  npm install          - Install dependencies");
console.log("  npm run dev:setup    - Complete setup");
console.log("");
console.log("Usage:");
console.log("  1. Start TrailBase server to create database");
console.log('  2. Run "npm run import:data" to import IMDB data');
console.log('  3. Run "npm run build" to build the static site');
console.log('  4. Run "npm run help" to see all available commands');
