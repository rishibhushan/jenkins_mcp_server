#!/usr/bin/env node
/**
 * Jenkins MCP Server - Node.js Wrapper
 *
 * This wrapper handles:
 * - Python version detection (cross-platform)
 * - Virtual environment creation
 * - Smart proxy detection and handling (auto-detects corporate vs public networks)
 * - Dependency installation with retry logic
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
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m'
};

function log(message, color = 'reset') {
  const colorCode = process.stderr.isTTY ? colors[color] : '';
  const resetCode = process.stderr.isTTY ? colors.reset : '';
  // CRITICAL: Use stderr for all output, stdout is for JSON-RPC only
  console.error(`${colorCode}${message}${resetCode}`);
}

function error(message) {
  console.error(`${colors.red}ERROR: ${message}${colors.reset}`);
}

function warning(message) {
  console.error(`${colors.yellow}WARNING: ${message}${colors.reset}`);
}

function info(message) {
  console.error(`${colors.cyan}ℹ ${message}${colors.reset}`);
}

/**
 * Detect and display proxy configuration
 * @returns {Object} Proxy configuration details
 */
function detectProxyConfig() {
  const proxyVars = [
    'HTTP_PROXY', 'http_proxy',
    'HTTPS_PROXY', 'https_proxy',
    'ALL_PROXY', 'all_proxy',
    'NO_PROXY', 'no_proxy'
  ];

  const activeProxies = {};
  for (const varName of proxyVars) {
    if (process.env[varName]) {
      activeProxies[varName] = process.env[varName];
    }
  }

  return activeProxies;
}

/**
 * Check npm config for proxy settings
 * @returns {Object} npm proxy configuration
 */
function checkNpmProxy() {
  try {
    const result = spawnSync('npm', ['config', 'list'], {
      stdio: 'pipe',
      encoding: 'utf-8'
    });

    if (result.status === 0) {
      const output = result.stdout || '';
      const proxyLines = output.split('\n').filter(line =>
        line.toLowerCase().includes('proxy') && !line.includes('; ///')
      );

      if (proxyLines.length > 0) {
        return {
          found: true,
          config: proxyLines.join('\n')
        };
      }
    }
  } catch (e) {
    // npm not available or error
  }
  return { found: false };
}

/**
 * Check pip config for proxy settings
 * @returns {Object} pip proxy configuration
 */
function checkPipProxy() {
  try {
    const result = spawnSync('pip3', ['config', 'list'], {
      stdio: 'pipe',
      encoding: 'utf-8'
    });

    if (result.status === 0) {
      const output = result.stdout || '';
      if (output.toLowerCase().includes('proxy')) {
        return {
          found: true,
          config: output
        };
      }
    }
  } catch (e) {
    // pip not available or error
  }
  return { found: false };
}

/**
 * Test if proxy is reachable
 * @param {string} proxyUrl - Proxy URL to test
 * @returns {boolean} True if proxy is reachable
 */
function testProxyConnectivity(proxyUrl) {
  try {
    // Try to parse proxy URL
    const url = new URL(proxyUrl);

    // Use curl to test proxy connectivity (cross-platform)
    const testCmd = isWindows
      ? `curl -s -o NUL -w "%{http_code}" --proxy ${proxyUrl} --max-time 5 https://pypi.org/simple/`
      : `curl -s -o /dev/null -w "%{http_code}" --proxy ${proxyUrl} --max-time 5 https://pypi.org/simple/`;

    const result = spawnSync(isWindows ? 'cmd' : 'sh',
      isWindows ? ['/c', testCmd] : ['-c', testCmd],
      {
        stdio: 'pipe',
        encoding: 'utf-8',
        timeout: 6000
      }
    );

    const httpCode = result.stdout?.trim();
    return httpCode === '200' || httpCode === '301' || httpCode === '302';
  } catch (e) {
    return false;
  }
}

/**
 * Test if PyPI is directly accessible (without proxy)
 * @returns {boolean} True if PyPI is accessible
 */
function testDirectPyPIAccess() {
  try {
    const testCmd = isWindows
      ? 'curl -s -o NUL -w "%{http_code}" --max-time 5 https://pypi.org/simple/'
      : 'curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://pypi.org/simple/';

    const result = spawnSync(isWindows ? 'cmd' : 'sh',
      isWindows ? ['/c', testCmd] : ['-c', testCmd],
      {
        stdio: 'pipe',
        encoding: 'utf-8',
        timeout: 6000
      }
    );

    const httpCode = result.stdout?.trim();
    return httpCode === '200' || httpCode === '301' || httpCode === '302';
  } catch (e) {
    return false;
  }
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
    stdio: ['ignore', 'pipe', 'inherit']
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
 * Show helpful guidance for proxy-related installation failures
 */
function showProxyTroubleshooting(activeProxies, canAccessDirectly, proxyWorks) {
  console.error('\n' + '='.repeat(70));
  console.error(colors.bold + colors.yellow + 'INSTALLATION FAILED - NETWORK CONFIGURATION ISSUE' + colors.reset);
  console.error('='.repeat(70));

  // Check npm and pip config
  const npmProxy = checkNpmProxy();
  const pipProxy = checkPipProxy();

  if (npmProxy.found) {
    console.error('\n' + colors.red + '⚠️  FOUND PROXY IN NPM CONFIG!' + colors.reset);
    console.error(colors.cyan + npmProxy.config + colors.reset);
    console.error('\n' + colors.yellow + 'This is likely the cause of your issue!' + colors.reset);
    console.error('\n' + colors.bold + 'FIX (run these commands):' + colors.reset);
    console.error(colors.cyan + '  npm config delete proxy' + colors.reset);
    console.error(colors.cyan + '  npm config delete https-proxy' + colors.reset);
    console.error(colors.cyan + '  npm config delete http-proxy' + colors.reset);
    console.error(colors.cyan + '  npm config --global delete proxy' + colors.reset);
    console.error(colors.cyan + '  npm config --global delete https-proxy' + colors.reset);
    console.error('\nThen run your command again.\n');
  }

  if (pipProxy.found) {
    console.error('\n' + colors.red + '⚠️  FOUND PROXY IN PIP CONFIG!' + colors.reset);
    console.error(colors.cyan + pipProxy.config + colors.reset);
    console.error('\n' + colors.bold + 'FIX (run these commands):' + colors.reset);
    console.error(colors.cyan + '  pip3 config unset global.proxy' + colors.reset);
    console.error(colors.cyan + '  pip3 config unset user.proxy' + colors.reset);
    console.error('\nOr edit/delete: ~/.config/pip/pip.conf\n');
  }

  if (Object.keys(activeProxies).length > 0) {
    console.error('\n📡 Active proxy environment variables found:');
    for (const [key, value] of Object.entries(activeProxies)) {
      console.error(`   ${colors.cyan}${key}${colors.reset} = ${value}`);
    }

    if (!proxyWorks && canAccessDirectly) {
      // Proxy is set but doesn't work, and direct access works
      console.error('\n' + colors.red + '❌ Proxy is NOT reachable' + colors.reset);
      console.error(colors.green + '✓ Direct internet access IS available' + colors.reset);
      console.error('\n' + colors.yellow + '⚠️  You\'re on a PUBLIC network but have proxy settings from a corporate/VPN network!' + colors.reset);
      console.error('\n💡 SOLUTION:\n');
      console.error(colors.bold + 'Remove the proxy settings:' + colors.reset);
      console.error(colors.cyan + '   unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy' + colors.reset);
      console.error('   Then run the command again.\n');

    } else if (proxyWorks && !canAccessDirectly) {
      // Proxy works, direct access doesn't
      console.error('\n' + colors.green + '✓ Proxy IS reachable' + colors.reset);
      console.error(colors.red + '❌ Direct internet access is NOT available' + colors.reset);
      console.error('\n' + colors.blue + 'You\'re on a CORPORATE network - proxy is required.' + colors.reset);
      console.error('\n💡 SOLUTION:\n');
      console.error('The proxy should work. The error may be due to:');
      console.error('1. SSL certificate issues - contact your IT department');
      console.error('2. Authentication required - check if proxy needs username/password');
      console.error('3. Specific packages blocked - contact your IT department\n');

    } else if (!proxyWorks && !canAccessDirectly) {
      // Neither works
      console.error('\n' + colors.red + '❌ Proxy is NOT reachable' + colors.reset);
      console.error(colors.red + '❌ Direct internet access is NOT available' + colors.reset);
      console.error('\n💡 SOLUTIONS:\n');
      console.error('1. Check your internet connection');
      console.error('2. If on corporate network, verify proxy settings with IT');
      console.error('3. Try a different network (mobile hotspot, home WiFi)');
      console.error('4. Check firewall/antivirus settings\n');

    } else {
      // Both work (unusual case)
      console.error('\n' + colors.green + '✓ Proxy IS reachable' + colors.reset);
      console.error(colors.green + '✓ Direct internet access IS available' + colors.reset);
      console.error('\nThe issue may be:');
      console.error('1. SSL certificate problems');
      console.error('2. Intermittent connectivity');
      console.error('3. Package-specific blocking\n');
    }

    console.error(colors.bold + 'Additional options:' + colors.reset);
    console.error('• Check system proxy settings:');
    if (!isWindows) {
      console.error('  macOS: System Settings → Network → Advanced → Proxies');
    } else {
      console.error('  Windows: Settings → Network & Internet → Proxy');
    }
    console.error('• Try manual installation (see TROUBLESHOOTING.md)');

  } else {
    console.error('\n💡 No proxy environment variables detected.\n');
    console.error('POSSIBLE CAUSES:');
    console.error('• Network connectivity issues');
    console.error('• Firewall blocking PyPI access');
    console.error('• DNS resolution problems');
    console.error('• System-level proxy (not in environment variables)\n');

    console.error('SOLUTIONS TO TRY:');
    console.error('1. Check your internet connection');
    console.error('2. Try: curl https://pypi.org/simple/');
    console.error('3. Check firewall/antivirus settings');
    console.error('4. Check system proxy settings (not environment variables)\n');
  }

  console.error('='.repeat(70) + '\n');
}

/**
 * Install Python dependencies with smart proxy detection
 * @param {string} venvPath - Path to virtual environment
 */
function installDependencies(venvPath) {
  const { pip } = getVenvPaths(venvPath);
  const wheelsPath = path.join(projectRoot, 'wheels');
  const requirementsPath = path.join(projectRoot, 'requirements.txt');

  console.error('Installing Python dependencies...');

  // Check if wheels directory exists (pre-packaged wheels)
  if (fs.existsSync(wheelsPath)) {
    console.error('Using pre-packaged wheels (no internet required)...');

    const installReqs = spawnSync(pip, [
      'install',
      '--no-index',
      '--find-links', wheelsPath,
      '-r', requirementsPath
    ], {
      cwd: projectRoot,
      stdio: ['ignore', 'pipe', 'inherit']
    });

    if (installReqs.status !== 0) {
      error('Failed to install from wheels');
      process.exit(1);
    }

    log('✓ Requirements installed', 'green');
  } else {
    // Need network - detect proxy configuration intelligently
    console.error('Downloading from PyPI...');

    const activeProxies = detectProxyConfig();
    const hasProxyVars = Object.keys(activeProxies).length > 0;

    let proxyToUse = null;
    let useNoProxy = false;

    if (hasProxyVars) {
      const proxyUrl = process.env.HTTP_PROXY || process.env.http_proxy ||
                       process.env.HTTPS_PROXY || process.env.https_proxy;

      info('Proxy environment variables detected. Testing connectivity...');

      // Test proxy connectivity
      const proxyWorks = proxyUrl && proxyUrl.startsWith('http') && testProxyConnectivity(proxyUrl);
      const directWorks = testDirectPyPIAccess();

      if (proxyWorks && !directWorks) {
        // Corporate network - use proxy
        info('Corporate network detected. Using proxy.');
        proxyToUse = proxyUrl;
      } else if (!proxyWorks && directWorks) {
        // Public network with stale proxy vars - ignore proxy
        warning('Proxy unreachable but direct access available. Ignoring proxy settings.');
        useNoProxy = true;
      } else if (proxyWorks && directWorks) {
        // Both work - prefer direct
        info('Both proxy and direct access available. Using direct connection.');
        useNoProxy = true;
      } else {
        // Neither works - will fail but try direct
        warning('Neither proxy nor direct access working. Attempting direct connection...');
        useNoProxy = true;
      }
    }

    // Build pip arguments
    const pipArgs = ['install', '-r', requirementsPath];

    // Trusted hosts for SSL-friendly installation
    const trustedHostArgs = [
      '--trusted-host', 'pypi.org',
      '--trusted-host', 'pypi.python.org',
      '--trusted-host', 'files.pythonhosted.org'
    ];
    pipArgs.push(...trustedHostArgs);

    // Add proxy if needed
    if (proxyToUse && !useNoProxy) {
      info(`Using proxy: ${proxyToUse}`);
      pipArgs.push('--proxy', proxyToUse);
    }

    // Set up environment (potentially removing proxy vars)
    const pipEnv = { ...process.env };
    if (useNoProxy) {
      // Remove proxy environment variables for this pip call
      delete pipEnv.HTTP_PROXY;
      delete pipEnv.HTTPS_PROXY;
      delete pipEnv.http_proxy;
      delete pipEnv.https_proxy;
      delete pipEnv.ALL_PROXY;
      delete pipEnv.all_proxy;
    }

    const installReqs = spawnSync(pip, pipArgs, {
      cwd: projectRoot,
      stdio: ['ignore', 'pipe', 'inherit'],
      env: pipEnv
    });

    if (installReqs.status !== 0) {
      error('Failed to install dependencies from PyPI');

      // Show intelligent troubleshooting
      const proxyUrl = process.env.HTTP_PROXY || process.env.http_proxy;
      const proxyWorks = proxyUrl ? testProxyConnectivity(proxyUrl) : false;
      const directWorks = testDirectPyPIAccess();

      showProxyTroubleshooting(activeProxies, directWorks, proxyWorks);
      process.exit(1);
    }

    log('✓ Requirements installed', 'green');
  }

  // Install package itself
  console.error('Installing jenkins-mcp-server package...');

  // Verify pyproject.toml exists
  const pyprojectPath = path.join(projectRoot, 'pyproject.toml');
  if (!fs.existsSync(pyprojectPath)) {
    error('pyproject.toml not found in project root');
    console.error('\nProject root:', projectRoot);
    console.error('Expected file:', pyprojectPath);
    console.error('\nThis may be due to npx cache issues with special characters.');
    console.error('Try clearing npx cache: npx clear-npx-cache');
    process.exit(1);
  }

  const packageArgs = ['install', '-e', '.'];

  const installPkg = spawnSync(pip, packageArgs, {
    cwd: projectRoot,
    stdio: ['ignore', 'pipe', 'inherit']
  });

  if (installPkg.status !== 0) {
    error('Failed to install package');
    console.error('\nProject root:', projectRoot);
    console.error('Files in project root:');
    try {
      const files = fs.readdirSync(projectRoot);
      console.error(files.join(', '));
    } catch (e) {
      console.error('Could not list files');
    }

    console.error('\n💡 TROUBLESHOOTING:');
    console.error('1. The npx cache may have issues with the @ symbol in package name');
    console.error('2. Try: npx clear-npx-cache && rm -rf ~/.npm/_npx');
    console.error('3. Or install globally: npm install -g @rishibhushan/jenkins-mcp-server');
    console.error('   Then run: jenkins-mcp-server --env-file /path/to/.env');
    process.exit(1);
  }

  log('✓ Package installed successfully', 'green');
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
    PYTHONUNBUFFERED: '1'
  };

  const serverArgs = [...entryPoint.args, ...args];

  // All logging to stderr (stdout reserved for JSON-RPC)
  console.error('=== NODE WRAPPER DEBUG ===');
  console.error('Project root:', projectRoot);
  console.error('Python path:', python);
  console.error('Entry point:', entryPoint);
  console.error('Server args:', serverArgs);
  console.error('PYTHONPATH:', env.PYTHONPATH);
  console.error('=== ATTEMPTING TO START PYTHON ===');

  log('Starting Jenkins MCP Server...', 'green');
  log(`Command: ${python} ${serverArgs.join(' ')}`, 'blue');

  // CRITICAL: stdin=pipe, stdout=inherit (for JSON-RPC), stderr=inherit (for logs)
  const server = spawn(python, serverArgs, {
    cwd: projectRoot,
    stdio: ['pipe', 'inherit', 'inherit'],
    env: env,
    shell: isWindows
  });

  server.on('error', (err) => {
    console.error('=== SPAWN ERROR ===', err);
    error(`Failed to start server: ${err.message}`);
    process.exit(1);
  });

  server.on('spawn', () => {
    console.error('=== PYTHON PROCESS SPAWNED ===');
  });

  server.on('close', (code, signal) => {
    console.error(`=== PYTHON PROCESS CLOSED: code=${code}, signal=${signal} ===`);
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
      console.error('Jenkins MCP Server - Node.js Wrapper');
      console.error('\nUsage: jenkins-mcp-server [options]');
      console.error('\nOptions:');
      console.error('  --env-file PATH    Path to custom .env file');
      console.error('  --verbose, -v      Enable verbose logging');
      console.error('  --no-vscode        Skip loading VS Code settings');
      console.error('  --version          Show version');
      console.error('  --help, -h         Show this help message');
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