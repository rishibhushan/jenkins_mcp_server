#!/usr/bin/env node

/**
 * Jenkins MCP Server launcher
 *
 * Responsibilities:
 *  1. Create local Python venv
 *  2. Auto-install dependencies (offline wheels if available)
 *  3. Auto-detect/download corporate CA certificates
 *  4. Optionally download portable Windows EXE
 *  5. Run MCP server via Python or EXE
 *  6. Keep pip output OFF stdout to avoid corrupting JSON-RPC
 */

const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const https = require("https");

// Root project dir (where cli.js is located)
const ROOT = path.resolve(__dirname);

// Python virtual environment
const VENV = path.join(ROOT, ".npx_venv");
const PYTHON = process.platform === "win32"
  ? path.join(VENV, "Scripts", "python.exe")
  : path.join(VENV, "bin", "python");

// Location of server package
const SRC = path.join(ROOT, "src");

////////////////////////////////////////////////////////////////////////////////
// UTILITY HELPERS
////////////////////////////////////////////////////////////////////////////////

function log(msg) {
  // log to stderr so VS Code does NOT treat it as JSON-RPC traffic
  process.stderr.write(msg + "\n");
}

function fileExists(p) {
  try { fs.accessSync(p); return true; } catch { return false; }
}

////////////////////////////////////////////////////////////////////////////////
// STEP 1: Ensure Python is available
////////////////////////////////////////////////////////////////////////////////

function resolvePython() {
  // First check system python3
  const python3 = spawnSync("python3", ["--version"]);
  if (python3.status === 0) return "python3";

  // check python
  const python = spawnSync("python", ["--version"]);
  if (python.status === 0) return "python";

  log("FATAL: No Python found. Please install Python 3.10+.");
  process.exit(1);
}

const SYSTEM_PYTHON = resolvePython();

////////////////////////////////////////////////////////////////////////////////
// STEP 2: Create virtual env if needed
////////////////////////////////////////////////////////////////////////////////

function ensureVenv() {
  if (fileExists(VENV)) return;

  log("Creating Python virtual environment...");
  const r = spawnSync(SYSTEM_PYTHON, ["-m", "venv", VENV], {
    stdio: ["ignore", "ignore", "pipe"]
  });

  if (r.status !== 0) {
    log("ERROR: Failed to create virtual environment.");
    log(String(r.stderr));
    process.exit(1);
  }
}

ensureVenv();

////////////////////////////////////////////////////////////////////////////////
// STEP 3: Install corporate CA bundle
////////////////////////////////////////////////////////////////////////////////

async function maybeDownloadCorporateCA() {
  const CA_ENV = process.env.CORPORATE_CA_URL;
  const CA_PATH = path.join(VENV, "corporate-ca.crt");

  // If file already exists, use it
  if (fileExists(CA_PATH)) {
    process.env.REQUESTS_CA_BUNDLE = CA_PATH;
    process.env.SSL_CERT_FILE = CA_PATH;
    return;
  }

  // If not provided, skip
  if (!CA_ENV) return;

  return new Promise((resolve) => {
    log("Downloading corporate CA bundle...");
    const file = fs.createWriteStream(CA_PATH);

    https.get(CA_ENV, (res) => {
      if (res.statusCode !== 200) {
        log(`ERROR: Unable to download CA from ${CA_ENV}`);
        file.close();
        resolve();
        return;
      }
      res.pipe(file);
      file.on("finish", () => {
        file.close();
        process.env.REQUESTS_CA_BUNDLE = CA_PATH;
        process.env.SSL_CERT_FILE = CA_PATH;
        resolve();
      });
    }).on("error", () => {
      log("ERROR: Failed to download corporate CA.");
      resolve();
    });
  });
}

////////////////////////////////////////////////////////////////////////////////
// STEP 4: Install dependencies (pip install) — OFFLINE FIRST
////////////////////////////////////////////////////////////////////////////////

function installDependencies() {
  const wheelsDir = path.join(ROOT, "wheels");
  const hasWheels = fileExists(wheelsDir);

  log("Installing Python dependencies...");

  const args = [
    "-m", "pip", "install",
    "--disable-pip-version-check",
    "--no-color"
  ];

  if (hasWheels) {
    log("Using offline wheels directory...");
    args.push("--no-index", "-f", wheelsDir);
  }

  args.push("-r", path.join(ROOT, "requirements.txt"));

  const proc = spawn(PYTHON, args, {
    env: process.env,
    stdio: ["ignore", "ignore", "pipe"] // IMPORTANT: keep stdout silent
  });

  let stderrBuf = "";
  proc.stderr.on("data", (d) => {
    stderrBuf += d.toString();
  });

  proc.on("close", (code) => {
    if (code !== 0) {
      log("ERROR installing dependencies:");
      log(stderrBuf);
      process.exit(1);
    }
    launchServer();
  });
}

////////////////////////////////////////////////////////////////////////////////
// STEP 5: Optional Windows portable EXE
////////////////////////////////////////////////////////////////////////////////

function tryRunWindowsExe() {
  const EXE_URL = process.env.EXE_URL;
  if (!EXE_URL) return false;

  if (process.platform !== "win32") return false;

  const EXE_PATH = path.join(ROOT, "jenkins_mcp_server.exe");

  if (!fileExists(EXE_PATH)) {
    log("Downloading Windows EXE...");
    const file = fs.createWriteStream(EXE_PATH);

    return new Promise((resolve) => {
      https.get(EXE_URL, (res) => {
        if (res.statusCode !== 200) {
          log("ERROR downloading EXE.");
          resolve(false);
          return;
        }
        res.pipe(file);
        file.on("finish", () => {
          file.close();
          resolve(true);
        });
      });
    });
  }

  return true;
}

////////////////////////////////////////////////////////////////////////////////
// STEP 6: Launch MCP server
////////////////////////////////////////////////////////////////////////////////

function launchServer() {
  log("Starting Jenkins MCP Server...");

  const env = {
    ...process.env,
    PYTHONPATH: SRC,            // ensure Python resolves our package correctly
    REQUESTS_CA_BUNDLE: process.env.REQUESTS_CA_BUNDLE || "",
    SSL_CERT_FILE: process.env.SSL_CERT_FILE || ""
  };

  const proc = spawn(PYTHON, ["-m", "jenkins_mcp_server"], {
    env,
    stdio: ["pipe", "pipe", "pipe"]
  });

  // Forward MCP RPC bytes from Python stdout → VS Code stdin
  proc.stdout.pipe(process.stdout);

  // Send errors to stderr only
  proc.stderr.on("data", (d) => process.stderr.write(d));

  // Keyboard input is forwarded to the server
  process.stdin.pipe(proc.stdin);
}

////////////////////////////////////////////////////////////////////////////////
// MAIN LOGIC
////////////////////////////////////////////////////////////////////////////////

(async () => {
  await maybeDownloadCorporateCA();

  // EXE mode only for Windows users
  const ranExe = await tryRunWindowsExe();
  if (ranExe === true && process.platform === "win32") {
    spawn("jenkins_mcp_server.exe", [], {
      stdio: "inherit"
    });
    return;
  }

  installDependencies();
})();