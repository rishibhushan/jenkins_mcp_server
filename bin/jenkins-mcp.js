#!/usr/bin/env node
/**
 * Jenkins MCP Server - Node.js Wrapper
 *
 * This wrapper handles:
 * - Python version detection (cross-platform)
 * - Virtual environment creation
 * - Dependency installation
 * - Server execution
 *
 * Supports: Windows, macOS, Linux
 */

const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Configuration
const projectRoot = path.join(__dirname, '..');
const args = process.argv.slice(2);
const isWindows = process.platform === 'win32';

// Color codes for terminal output (if supported)
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m'
};

function log(message, color = 'reset') {
  const colorCode = process.stdout.isTTY ? colors[color] : '';
  const resetCode = process.stdout.isTTY ? colors.reset : '';
  console.log(`${colorCode}${message}${resetCode}`);
}

function error(message) {
  console.error(`${colors.red}ERROR: ${message}${colors.reset}`);
}

/**
 * Check for Python 3 installation
 * @returns {string} Python command name
 */
function checkPython() {
  const pythonCommands = isWindows
    ? ['python', 'py', 'python3']
    : ['python3', 'python'];

  log('Checking for Python 3...', 'blue');

  for (const cmd of pythonCommands) {
    try {
      const result = spawnSync(cmd, ['--version'], {
        stdio: 'pipe',
        encoding: 'utf-8'
      });

      if (result.status === 0) {
        const output = result.stdout || result.stderr;
        if (output.includes('Python 3')) {
          const version = output.trim();
          log(`✓ Found ${version}`, 'green');
          return cmd;
        }
      }
    } catch (e) {
      // Command not found, try next
      continue;
    }
  }

  error('Python 3 is required but not found.');
  console.error('\nPlease install Python 3.8 or higher from:');
  console.error('  https://www.python.org/downloads/');
  console.error('\nAfter installation, restart your terminal and try again.');
  process.exit(1);
}

/**
 * Get paths for virtual environment binaries
 * @param {string} venvPath - Path to virtual environment
 * @returns {Object} Paths to python and pip executables
 */
function getVenvPaths(venvPath) {
  if (isWindows) {
    return {
      python: path.join(venvPath, 'Scripts', 'python.exe'),
      pip: path.join(venvPath, 'Scripts', 'pip.exe')
    };
  } else {
    return {
      python: path.join(venvPath, 'bin', 'python'),
      pip: path.join(venvPath, 'bin', 'pip')
    };
  }
}

/**
 * Create virtual environment if it doesn't exist
 * @param {string} pythonCmd - Python command to use
 * @returns {string} Path to virtual environment
 */
function ensureVenv(pythonCmd) {
  const venvPath = path.join(projectRoot, '.venv');

  if (fs.existsSync(venvPath)) {
    log('✓ Virtual environment exists', 'green');
    return venvPath;
  }

  log('Creating Python virtual environment...', 'yellow');

  const result = spawnSync(pythonCmd, ['-m', 'venv', venvPath], {
    cwd: projectRoot,
    stdio: 'inherit'
  });

  if (result.status !== 0) {
    error('Failed to create virtual environment');
    console.error('\nTroubleshooting:');
    console.error('  1. Ensure Python venv module is installed');
    console.error('  2. Check disk space and permissions');
    console.error('  3. Try manually: python3 -m venv .venv');
    process.exit(1);
  }

  log('✓ Virtual environment created', 'green');
  return venvPath;
}

/**
 * Check if dependencies are installed
 * @param {string} pipPath - Path to pip executable
 * @returns {boolean} True if dependencies are installed
 */
function dependenciesInstalled(pipPath) {
  try {
    const result = spawnSync(pipPath, ['list'], {
      stdio: 'pipe',
      encoding: 'utf-8'
    });

    if (result.status === 0) {
      const output = result.stdout || '';
      // Check for key dependencies
      return output.includes('python-jenkins') &&
             output.includes('mcp') &&
             output.includes('requests');
    }
  } catch (e) {
    // If we can't check, assume not installed
  }
  return false;
}

/**
 * Install Python dependencies
 * @param {string} venvPath - Path to virtual environment
 */
function installDependencies(venvPath) {
  const { pip } = getVenvPaths(venvPath);
  const requirementsPath = path.join(projectRoot, 'requirements.txt');

  if (!fs.existsSync(requirementsPath)) {
    error('requirements.txt not found');
    console.error(`Expected at: ${requirementsPath}`);
    process.exit(1);
  }

  log('Installing Python dependencies...', 'yellow');
  log('This may take a minute...', 'blue');

  const result = spawnSync(pip, ['install', '-r', requirementsPath], {
    cwd: projectRoot,
    stdio: 'inherit'
  });

  if (result.status !== 0) {
    error('Failed to install dependencies');
    console.error('\nTroubleshooting:');
    console.error('  1. Check your internet connection');
    console.error('  2. If behind a proxy, set HTTP_PROXY/HTTPS_PROXY env vars');
    console.error('  3. Try manually: .venv/bin/pip install -r requirements.txt');
    process.exit(1);
  }

  log('✓ Dependencies installed', 'green');
}

/**
 * Find the Python entry point
 * @returns {Object} Entry point information
 */
function findEntryPoint() {
  const mainPyPath = path.join(projectRoot, 'src', 'jenkins_mcp_server', '__main__.py');

  if (fs.existsSync(mainPyPath)) {
    return {
      type: 'module',
      args: ['-m', 'jenkins_mcp_server']
    };
  }

  // Fallback options
  const fallbacks = [
    path.join(projectRoot, 'src', 'jenkins_mcp_server', 'server.py'),
    path.join(projectRoot, 'src', 'main.py'),
    path.join(projectRoot, 'main.py')
  ];

  for (const filePath of fallbacks) {
    if (fs.existsSync(filePath)) {
      return {
        type: 'script',
        args: [filePath]
      };
    }
  }

  error('Could not find Python entry point');
  console.error('\nExpected one of:');
  console.error('  - src/jenkins_mcp_server/__main__.py (preferred)');
  console.error('  - src/jenkins_mcp_server/server.py');
  console.error('  - src/main.py');
  process.exit(1);
}

/**
 * Run the Jenkins MCP Server
 * @param {string} venvPath - Path to virtual environment
 */
function runServer(venvPath) {
  const { python } = getVenvPaths(venvPath);
  const entryPoint = findEntryPoint();

  // Set up environment
  const env = {
    ...process.env,
    PYTHONPATH: path.join(projectRoot, 'src'),
    PYTHONUNBUFFERED: '1'  // Ensure output is not buffered
  };

  const serverArgs = [...entryPoint.args, ...args];

  log('Starting Jenkins MCP Server...', 'green');
  log(`Command: ${python} ${serverArgs.join(' ')}`, 'blue');

  const server = spawn(python, serverArgs, {
    cwd: projectRoot,
    stdio: 'inherit',
    env: env,
    shell: isWindows
  });

  server.on('error', (err) => {
    error(`Failed to start server: ${err.message}`);
    process.exit(1);
  });

  server.on('close', (code) => {
    if (code !== 0 && code !== null) {
      log(`Server exited with code ${code}`, 'yellow');
    }
    process.exit(code || 0);
  });

  // Handle graceful shutdown
  const cleanup = () => {
    log('\nShutting down...', 'yellow');
    server.kill('SIGTERM');
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  // Windows doesn't support SIGINT/SIGTERM the same way
  if (isWindows) {
    process.on('SIGBREAK', cleanup);
  }
}

/**
 * Main execution flow
 */
function main() {
  try {
    // Check for help flag
    if (args.includes('--help') || args.includes('-h')) {
      console.log('Jenkins MCP Server - Node.js Wrapper');
      console.log('\nUsage: jenkins-mcp-server [options]');
      console.log('\nOptions:');
      console.log('  --env-file PATH    Path to custom .env file');
      console.log('  --verbose, -v      Enable verbose logging');
      console.log('  --no-vscode        Skip loading VS Code settings');
      console.log('  --version          Show version');
      console.log('  --help, -h         Show this help message');
      process.exit(0);
    }

    // Check Python availability
    const pythonCmd = checkPython();

    // Ensure virtual environment exists
    const venvPath = ensureVenv(pythonCmd);

    // Check and install dependencies if needed
    const { pip } = getVenvPaths(venvPath);
    if (!dependenciesInstalled(pip)) {
      installDependencies(venvPath);
    } else {
      log('✓ Dependencies already installed', 'green');
    }

    // Run the server
    runServer(venvPath);

  } catch (err) {
    error(`Unexpected error: ${err.message}`);
    console.error(err.stack);
    process.exit(1);
  }
}

// Run main function
main();