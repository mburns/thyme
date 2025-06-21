#!/usr/bin/env node

import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "fs-extra";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_ROOT = path.join(__dirname, "..");

interface TestResult {
  name: string;
  passed: boolean;
  error?: string;
}

async function runTests(): Promise<TestResult[]> {
  const results: TestResult[] = [];

  // Test 1: Check if required scripts exist
  results.push(await testScriptExistence());

  // Test 2: Check directory structure
  results.push(await testDirectoryStructure());

  // Test 3: Check required templates
  results.push(await testRequiredTemplates());

  return results;
}

async function testScriptExistence(): Promise<TestResult> {
  const requiredScripts = ["scripts/import-imdb.ts", "scripts/build.ts"];

  for (const script of requiredScripts) {
    const scriptPath = path.join(PROJECT_ROOT, script);
    if (!(await fs.pathExists(scriptPath))) {
      return {
        name: "Script Existence",
        passed: false,
        error: `Required script not found: ${script}`,
      };
    }
  }

  return {
    name: "Script Existence",
    passed: true,
  };
}

async function testDirectoryStructure(): Promise<TestResult> {
  const requiredDirs = ["templates", "static", "scripts", "sql"];

  for (const dir of requiredDirs) {
    const dirPath = path.join(PROJECT_ROOT, dir);
    if (!(await fs.pathExists(dirPath))) {
      return {
        name: "Directory Structure",
        passed: false,
        error: `Required directory not found: ${dir}`,
      };
    }
  }

  return {
    name: "Directory Structure",
    passed: true,
  };
}

async function testRequiredTemplates(): Promise<TestResult> {
  const requiredTemplates = ["templates/index.html", "templates/_base.html"];

  for (const template of requiredTemplates) {
    const templatePath = path.join(PROJECT_ROOT, template);
    if (!(await fs.pathExists(templatePath))) {
      return {
        name: "Required Templates",
        passed: false,
        error: `Required template not found: ${template}`,
      };
    }
  }

  return {
    name: "Required Templates",
    passed: true,
  };
}

async function main(): Promise<void> {
  console.log("Running tests and validation...");

  const results = await runTests();

  let allPassed = true;

  for (const result of results) {
    if (result.passed) {
      console.log(`✅ ${result.name}`);
    } else {
      console.log(`❌ ${result.name}: ${result.error}`);
      allPassed = false;
    }
  }

  if (allPassed) {
    console.log("\n✅ All tests passed");
  } else {
    console.log("\n❌ Some tests failed");
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error("Test failed:", error);
    process.exit(1);
  });
}
