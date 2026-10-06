#!/usr/bin/env node

import { execSync } from "node:child_process";

interface Dependency {
  name: string;
  command: string;
  description: string;
  required: boolean;
}

const dependencies: Dependency[] = [
  {
    name: "Volta",
    command: "volta",
    description: "Node.js version manager",
    required: true,
  },
  {
    name: "Node.js",
    command: "node",
    description: "Node.js runtime",
    required: true,
  },
  {
    name: "npm",
    command: "npm",
    description: "Node package manager",
    required: false,
  },
  {
    name: "yarn",
    command: "yarn",
    description: "Yarn package manager",
    required: false,
  },
  {
    name: "sqlite3",
    command: "sqlite3",
    description: "SQLite database",
    required: true,
  },
  { name: "curl", command: "curl", description: "HTTP client", required: true },
  {
    name: "gunzip",
    command: "gunzip",
    description: "Gzip decompression",
    required: true,
  },
  {
    name: "git",
    command: "git",
    description: "Version control",
    required: true,
  },
];

function checkCommand(command: string): boolean {
  try {
    execSync(`which ${command}`, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

function checkVoltaVersion(): { installed: boolean; version?: string } {
  try {
    const version = execSync("volta --version", { encoding: "utf-8" }).trim();
    return { installed: true, version };
  } catch {
    return { installed: false };
  }
}

function checkNodeVersion(): { installed: boolean; version?: string } {
  try {
    const version = execSync("node --version", { encoding: "utf-8" }).trim();
    return { installed: true, version };
  } catch {
    return { installed: false };
  }
}

async function main(): Promise<void> {
  console.log("Checking system dependencies...");
  console.log("");

  let allRequiredInstalled = true;

  // Check Volta first
  const voltaCheck = checkVoltaVersion();
  if (voltaCheck.installed) {
    console.log(`✅ Volta (${voltaCheck.version}) - Node.js version manager`);
  } else {
    console.log("❌ Volta is required but not installed");
    console.log("   Install from: https://volta.sh/");
    allRequiredInstalled = false;
  }

  // Check Node.js
  const nodeCheck = checkNodeVersion();
  if (nodeCheck.installed) {
    console.log(`✅ Node.js (${nodeCheck.version}) - JavaScript runtime`);
  } else {
    console.log("❌ Node.js is required but not installed");
    allRequiredInstalled = false;
  }

  // Check other dependencies
  for (const dep of dependencies.slice(2)) {
    // Skip Volta and Node.js as we already checked them
    if (checkCommand(dep.command)) {
      console.log(`✅ ${dep.name} (${dep.description})`);
    } else if (dep.required) {
      console.log(`❌ ${dep.name} is required but not installed`);
      allRequiredInstalled = false;
    } else {
      console.log(`⚠️  ${dep.name} (${dep.description}) - optional`);
    }
  }

  console.log("");

  if (allRequiredInstalled) {
    console.log("✅ All required dependencies are installed");
    console.log("");
    console.log("💡 Next steps:");
    console.log('   1. Run "npm install" to install project dependencies');
    console.log('   2. Run "npm run dev:setup" for complete setup');
  } else {
    console.log("❌ Some required dependencies are missing");
    console.log("");
    console.log("💡 Installation help:");
    console.log("   - Volta: https://volta.sh/");
    console.log("   - Node.js: Will be installed by Volta");
    console.log("   - SQLite: Use your system package manager");
    console.log("   - Other tools: Use your system package manager");
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error("Check failed:", error);
    process.exit(1);
  });
}
