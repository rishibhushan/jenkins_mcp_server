#!/usr/bin/env node

import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

/**
 * Resolve paths relative to the *installed package*,
 * NOT the caller's current working directory.
 */
const IS_WINDOWS = process.platform === "win32";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PACKAGE_ROOT = path.resolve(__dirname, "..");
const isVerbose = process.argv.includes('--verbose');

/**
 * Debug (stderr only – safe for MCP)
 */
 if (isVerbose) {
  console.error("[jenkins-mcp] package root:", PACKAGE_ROOT);
}
/**
 * Resolve Python executable inside packaged venv
 */
const pythonPath = IS_WINDOWS
  ? path.join(PACKAGE_ROOT, ".venv", "Scripts", "python.exe")
  : path.join(PACKAGE_ROOT, ".venv", "bin", "python");

function run(cmd, args, cwd) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"], // Always pipe stdout/stderr
    });

    // Handle stdout
    p.stdout.on("data", (d) => {
      if (isVerbose) {
        console.error(d.toString()); // Only show if verbose
      }
    });

    // Handle stderr
    p.stderr.on("data", (d) => {
      if (isVerbose) {
        console.error(d.toString()); // Only show if verbose
      }
    });

    p.on("exit", (code) =>
      code === 0 ? resolve() : reject(new Error(`${cmd} failed`))
    );
  });
}

async function ensureVenv() {
  if (!fs.existsSync(pythonPath)) {
    if (isVerbose) {
      console.error("[jenkins-mcp] Python venv not found, creating...");
    }
    const venvPython = IS_WINDOWS ? "python" : "python3";
    await run(venvPython, ["-m", "venv", ".venv"], PACKAGE_ROOT);
  } else {
    if (isVerbose) {
      console.error("[jenkins-mcp] Python venv exists, ensuring dependencies...");
    }
  }

  const pipArgs = ["-m", "pip", "install", "-r", "requirements.txt"];

  // Optional enterprise / proxy support
  if (process.env.PIP_INDEX_URL) {
    pipArgs.push("--index-url", process.env.PIP_INDEX_URL);
  }

  if (process.env.PIP_EXTRA_INDEX_URL) {
    pipArgs.push("--extra-index-url", process.env.PIP_EXTRA_INDEX_URL);
  }

  if (process.env.PIP_TRUSTED_HOST) {
    pipArgs.push("--trusted-host", process.env.PIP_TRUSTED_HOST);
  }

  await run(pythonPath, pipArgs, PACKAGE_ROOT);

    if (isVerbose) {
      console.error("[jenkins-mcp] Python environment ready");
    }
}

(async () => {
  try {
    await ensureVenv();
  } catch (err) {
    if (isVerbose) {
      console.error("[jenkins-mcp] Bootstrap failed:", err);
    }
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

  if (isVerbose) {
    console.error("[jenkins-mcp] Python:", pythonPath);
    console.error("[jenkins-mcp] Args:", pythonArgs.join(" "));
  }

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
      if (isVerbose) {
        console.error("[jenkins-mcp] exited due to signal:", signal);
      }
      process.exit(1);
    }
    process.exit(code ?? 0);
  });

  child.on("error", (err) => {
    if (isVerbose) {
      console.error("[jenkins-mcp] failed to start:", err);
    }
    process.exit(1);
  });
})();