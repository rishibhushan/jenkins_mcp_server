#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const projectRoot = path.join(__dirname, '..');
const args = process.argv.slice(2);

function checkPython() {
  const pythonCommands = process.platform === 'win32'
    ? ['python', 'py', 'python3']
    : ['python3', 'python'];

  for (const cmd of pythonCommands) {
    try {
      const result = require('child_process').spawnSync(cmd, ['--version'], {
        stdio: 'pipe',
        encoding: 'utf-8'
      });

      if (result.status === 0 && result.stdout.includes('Python 3')) {
        return cmd;
      }
    } catch (e) {
      continue;
    }
  }

  console.error('Error: Python 3 is required but not found.');
  console.error('Please install Python 3 from https://python.org');
  process.exit(1);
}

function setupVenv() {
  const pythonCmd = checkPython();
  const venvPath = path.join(projectRoot, '.venv');

  if (!fs.existsSync(venvPath)) {
    console.log('Creating Python virtual environment...');
    const createVenv = require('child_process').spawnSync(
      pythonCmd,
      ['-m', 'venv', venvPath],
      {
        cwd: projectRoot,
        stdio: 'inherit'
      }
    );

    if (createVenv.status !== 0) {
      console.error('Failed to create virtual environment');
      process.exit(1);
    }

    installDependencies(pythonCmd, venvPath);
  } else {
    // Check if dependencies are installed
    const pipPath = process.platform === 'win32'
      ? path.join(venvPath, 'Scripts', 'pip.exe')
      : path.join(venvPath, 'bin', 'pip');

    const check = require('child_process').spawnSync(
      pipPath,
      ['list'],
      { stdio: 'pipe' }
    );

    if (!check.stdout.toString().includes('python-jenkins')) {
      installDependencies(pythonCmd, venvPath);
    } else {
      runServer(pythonCmd, venvPath);
    }
  }
}

function installDependencies(pythonCmd, venvPath) {
  console.log('Installing Python dependencies...');

  const pipPath = process.platform === 'win32'
    ? path.join(venvPath, 'Scripts', 'pip.exe')
    : path.join(venvPath, 'bin', 'pip');

  const install = require('child_process').spawnSync(
    pipPath,
    ['install', '-r', path.join(projectRoot, 'requirements.txt')],
    {
      cwd: projectRoot,
      stdio: 'inherit'
    }
  );

  if (install.status !== 0) {
    console.error('Failed to install dependencies');
    process.exit(1);
  }

  runServer(pythonCmd, venvPath);
}

function runServer(pythonCmd, venvPath) {
  const pythonPath = process.platform === 'win32'
    ? path.join(venvPath, 'Scripts', 'python.exe')
    : path.join(venvPath, 'bin', 'python');

  // Determine the correct Python file to run
  let pythonArgs;
  const mainPyPath = path.join(projectRoot, 'src', 'jenkins_mcp_server', '__main__.py');
  const serverPyPath = path.join(projectRoot, 'src', 'server.py');

  // Set PYTHONPATH to include src directory
  const env = {
    ...process.env,
    PYTHONPATH: path.join(projectRoot, 'src')
  };

  // Try different approaches based on your structure
  if (fs.existsSync(mainPyPath)) {
    // Option 1: Module with __main__.py
    pythonArgs = ['-m', 'jenkins_mcp_server', ...args];
  } else if (fs.existsSync(serverPyPath)) {
    // Option 2: Direct script execution
    pythonArgs = [serverPyPath, ...args];
  } else {
    // Option 3: Look for main entry point
    const possibleEntries = [
      path.join(projectRoot, 'src', 'main.py'),
      path.join(projectRoot, 'src', 'jenkins_mcp_server.py'),
      path.join(projectRoot, 'main.py')
    ];

    const entryPoint = possibleEntries.find(p => fs.existsSync(p));

    if (!entryPoint) {
      console.error('Error: Could not find Python entry point');
      console.error('Please ensure one of these files exists:');
      console.error('  - src/jenkins_mcp_server/__main__.py');
      console.error('  - src/server.py');
      console.error('  - src/main.py');
      process.exit(1);
    }

    pythonArgs = [entryPoint, ...args];
  }

  console.log(`Starting Jenkins MCP Server...`);

  const server = spawn(pythonPath, pythonArgs, {
    cwd: projectRoot,
    stdio: 'inherit',
    env: env,
    shell: process.platform === 'win32' // Use shell on Windows
  });

  server.on('error', (err) => {
    console.error('Failed to start server:', err);
    process.exit(1);
  });

  server.on('close', (code) => {
    process.exit(code || 0);
  });

  // Handle cleanup
  process.on('SIGINT', () => server.kill('SIGINT'));
  process.on('SIGTERM', () => server.kill('SIGTERM'));
}

// Start
setupVenv();