#!/usr/bin/env node
/**
 * Jenkins MCP Server launcher for npx/github:
 * - Creates local venv (.npx_venv) if missing
 * - Installs deps from requirements.txt (or ./wheels if present)
 * - Sets PYTHONPATH to locate the package (src/ or repo root)
 * - Sets SSL cert bundle defaults on macOS if unset (fixes corporate TLS proxies)
 * - Runs: python -m jenkins_mcp_server [args...]
 *
 * Env:
 *   PYTHON_CMD          override python executable (default: python3 on *nix, python on Win)
 *   NPX_SKIP_INSTALL=1  skip venv + pip install
 *   HTTP_PROXY/HTTPS_PROXY/NO_PROXY  passed through to pip and runtime
 *   SSL_CERT_FILE / REQUESTS_CA_BUNDLE  honored if already set (we don't override)
 */

const { spawnSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const projectRoot = path.dirname(__filename);
const srcPkgPath = path.join(projectRoot, 'src', 'jenkins_mcp_server');
const rootPkgPath = path.join(projectRoot, 'jenkins_mcp_server');
const wheelsDir = path.join(projectRoot, 'wheels');
const venvDir = path.join(projectRoot, '.npx_venv');
const reqFile = path.join(projectRoot, 'requirements.txt');

const isWin = process.platform === 'win32';
const pythonCmd = process.env.PYTHON_CMD || (isWin ? 'python' : 'python3');
const skipInstall = process.env.NPX_SKIP_INSTALL === '1' || process.argv.includes('--no-venv') || process.argv.includes('--skip-install');

function execSyncOrDie(cmd, args, opts) {
  const res = spawnSync(cmd, args, { stdio: 'inherit', ...opts });
  if (res.error) throw res.error;
  if (typeof res.status === 'number' && res.status !== 0) process.exit(res.status);
  return res;
}

function findPython() {
  for (const candidate of [pythonCmd, isWin ? 'python' : 'python3', 'python']) {
    try {
      const r = spawnSync(candidate, ['--version'], { stdio: 'ignore' });
      if (r.status === 0) return candidate;
    } catch (_) {}
  }
  return null;
}

function ensureVenvAndInstall() {
  if (skipInstall) {
    console.log('Skipping venv/deps install (NPX_SKIP_INSTALL or --no-venv).');
    return null;
  }
  const py = findPython();
  if (!py) {
    console.error('Python not found. Install Python 3 and/or set PYTHON_CMD.');
    process.exit(1);
  }
  if (!fs.existsSync(venvDir)) {
    console.log('Creating virtual environment:', venvDir);
    execSyncOrDie(py, ['-m', 'venv', venvDir]);
  }
  const venvPython = isWin ? path.join(venvDir, 'Scripts', 'python.exe') : path.join(venvDir, 'bin', 'python');
  const venvPip = isWin ? path.join(venvDir, 'Scripts', 'pip.exe') : path.join(venvDir, 'bin', 'pip');

  // Upgrade pip (uses the same cert/proxy env we’ll set for install)
  console.log('Ensuring pip is available in venv...');
  execSyncOrDie(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip']);

  const pipArgs = [];
  // If you later add wheels/ for offline installs, this will auto-use them
  if (fs.existsSync(wheelsDir)) {
    pipArgs.push('--no-index', `--find-links=${wheelsDir}`);
  }
  // Install dependencies
  if (fs.existsSync(reqFile)) {
    console.log('Installing Python dependencies from requirements.txt into venv...');
    execSyncOrDie(venvPip, ['install', ...pipArgs, '-r', reqFile], { env: buildEnvForPip() });
  } else {
    console.warn('No requirements.txt found. Skipping dependency install.');
  }
  return venvPython;
}

function buildEnvForPip() {
  const env = { ...process.env };

  // Pass through proxies if set
  for (const k of ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy']) {
    if (process.env[k]) env[k] = process.env[k];
  }

  // If user hasn’t provided a cert bundle, set a sane default on macOS
  // (This fixes corporate TLS proxy issues without user exports.)
  const macSystemCert = '/etc/ssl/cert.pem';
  const hasUserCerts = !!(env.SSL_CERT_FILE || env.REQUESTS_CA_BUNDLE);
  if (!hasUserCerts && process.platform === 'darwin' && fs.existsSync(macSystemCert)) {
    env.SSL_CERT_FILE = macSystemCert;
    env.REQUESTS_CA_BUNDLE = macSystemCert;
  }

  return env;
}

function buildRuntimeEnv(pythonpathToPrepend) {
  const env = buildEnvForPip(); // include proxy + cert defaults
  const existing = env.PYTHONPATH || '';
  env.PYTHONPATH = pythonpathToPrepend + (existing ? path.delimiter + existing : '');
  return env;
}

function resolvePythonPath() {
  if (fs.existsSync(srcPkgPath)) return path.join(projectRoot, 'src');
  if (fs.existsSync(rootPkgPath)) return projectRoot;
  // Fallback: try src/ anyway
  return path.join(projectRoot, 'src');
}

function runServer(venvPython) {
  const pyExec = venvPython || findPython();
  if (!pyExec) {
    console.error('Python not found. Install Python 3 and/or set PYTHON_CMD.');
    process.exit(1);
  }
  const pyPath = resolvePythonPath();
  const env = buildRuntimeEnv(pyPath);
  const args = ['-m', 'jenkins_mcp_server', ...process.argv.slice(2)];

  console.log(`Running: ${pyExec} ${args.join(' ')}`);
  const child = spawn(pyExec, args, { stdio: 'inherit', env, cwd: process.cwd() });

  child.on('exit', (code) => process.exit(code));
  child.on('error', (err) => {
    console.error('Failed to start python process:', err);
    process.exit(1);
  });
}

// Main
try {
  const venvPython = ensureVenvAndInstall();
  runServer(venvPython);
} catch (err) {
  console.error('Error preparing environment:', err);
  process.exit(1);
}