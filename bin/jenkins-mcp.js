#!/usr/bin/env node

import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

/**
 * Resolve paths relative to the *installed package*,
 * NOT the caller's current working directory.
 */
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PACKAGE_ROOT = path.resolve(__dirname, "..");

/**
 * Debug (stderr only – safe for MCP)
 */
console.error("[jenkins-mcp] package root:", PACKAGE_ROOT);

/**
 * Resolve Python executable inside packaged venv
 */
const pythonPath = path.join(
  PACKAGE_ROOT,
  ".venv",
  "bin",
  "python"
);

if (!fs.existsSync(pythonPath)) {
  console.error("[jenkins-mcp] Python venv not found, bootstrapping...");

  const bootstrap = spawn("python3", ["-m", "venv", ".venv"], {
    cwd: PACKAGE_ROOT,
    stdio: "inherit",
  });

  bootstrap.on("exit", (code) => {
    if (code !== 0) {
      console.error("[jenkins-mcp] Failed to create venv");
      process.exit(1);
    }

    const pip = path.join(PACKAGE_ROOT, ".venv", "bin", "pip");

    const install = spawn(pip, ["install", "-r", "requirements.txt"], {
      cwd: PACKAGE_ROOT,
      stdio: "inherit",
    });

    install.on("exit", (pipCode) => {
      if (pipCode !== 0) {
        console.error("[jenkins-mcp] Failed to install dependencies");
        process.exit(1);
      }

      console.error("[jenkins-mcp] Bootstrap complete, restarting...");

      spawn(process.execPath, process.argv.slice(1), {
        stdio: "inherit",
      });
      process.exit(0);
    });
  });

  process.exit(0);
}

/**
 * Forward CLI arguments (e.g. --env-file ...)
 */
const args = process.argv.slice(2);

/**
 * Final Python command:
 *   python -m jenkins_mcp_server <args>
 */
const pythonArgs = [
  "-m",
  "jenkins_mcp_server",
  ...args,
];

console.error("[jenkins-mcp] Python:", pythonPath);
console.error("[jenkins-mcp] Args:", pythonArgs.join(" "));

/**
 * Spawn Python MCP server
 */
const child = spawn(pythonPath, pythonArgs, {
  cwd: PACKAGE_ROOT, // 🔑 critical
  env: {
    ...process.env,
    PYTHONPATH: path.join(PACKAGE_ROOT, "src"), // 🔑 critical
  },
  stdio: ["inherit", "inherit", "inherit"], // MCP stdio
});

/**
 * Propagate exit code
 */
child.on("exit", (code, signal) => {
  if (signal) {
    console.error("[jenkins-mcp] exited due to signal:", signal);
    process.exit(1);
  }
  process.exit(code ?? 0);
});

child.on("error", (err) => {
  console.error("[jenkins-mcp] failed to start:", err);
  process.exit(1);
});