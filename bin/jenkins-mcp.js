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

async function run(cmd, args, cwd) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { cwd, stdio: "inherit" });
    p.on("exit", (code) =>
      code === 0 ? resolve() : reject(new Error(`${cmd} failed`))
    );
  });
}

async function ensureVenv() {
  if (fs.existsSync(pythonPath)) {
    return;
  }

  console.error("[jenkins-mcp] Python venv not found, bootstrapping...");

  await run("python3", ["-m", "venv", ".venv"], PACKAGE_ROOT);

  const pip = path.join(PACKAGE_ROOT, ".venv", "bin", "pip");
  await run(pip, ["install", "-r", "requirements.txt"], PACKAGE_ROOT);

  console.error("[jenkins-mcp] Bootstrap complete");
}

(async () => {
  try {
    await ensureVenv();
  } catch (err) {
    console.error("[jenkins-mcp] Bootstrap failed:", err);
    process.exit(1);
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
})();