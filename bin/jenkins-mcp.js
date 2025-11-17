#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Determine the project root (where package.json is)
const projectRoot = path.join(__dirname, '..');

// Parse command-line arguments
const args = process.argv.slice(2);

// Check if Python 3 is available
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
      
      if (result.status === 0) {
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

// Setup virtual environment
function setupVenv() {
  const pythonCmd = checkPython();
  const venvPath = path.join(projectRoot, '.venv');
  
  // Create venv if it doesn't exist
  if (!fs.existsSync(venvPath)) {
    console.log('Creating Python virtual environment...');
    const createVenv = spawn(pythonCmd, ['-m', 'venv', venvPath], {
      cwd: projectRoot,
      stdio: 'inherit'
    });
    
    createVenv.on('close', (code) => {
      if (code !== 0) {
        console.error('Failed to create virtual environment');
        process.exit(1);
      }
      installDependencies(pythonCmd, venvPath);
    });
  } else {
    runServer(pythonCmd, venvPath);
  }
}

// Install Python dependencies
function installDependencies(pythonCmd, venvPath) {
  console.log('Installing Python dependencies...');
  
  const pipPath = process.platform === 'win32'
    ? path.join(venvPath, 'Scripts', 'pip.exe')
    : path.join(venvPath, 'bin', 'pip');
  
  const install = spawn(pipPath, [
    'install',
    '-r',
    path.join(projectRoot, 'requirements.txt')
  ], {
    cwd: projectRoot,
    stdio: 'inherit'
  });
  
  install.on('close', (code) => {
    if (code !== 0) {
      console.error('Failed to install dependencies');
      process.exit(1);
    }
    runServer(pythonCmd, venvPath);
  });
}

// Run the Python server
function runServer(pythonCmd, venvPath) {
  const pythonPath = process.platform === 'win32'
    ? path.join(venvPath, 'Scripts', 'python.exe')
    : path.join(venvPath, 'bin', 'python');
  
  // Set PYTHONPATH to include the src directory
  const env = {
    ...process.env,
    PYTHONPATH: path.join(projectRoot, 'src')
  };
  
  const server = spawn(
    pythonPath,
    ['-m', 'jenkins_mcp_server', ...args],
    {
      cwd: projectRoot,
      stdio: 'inherit',
      env: env
    }
  );
  
  server.on('error', (err) => {
    console.error('Failed to start server:', err);
    process.exit(1);
  });
  
  server.on('close', (code) => {
    process.exit(code || 0);
  });
  
  // Handle cleanup on exit
  process.on('SIGINT', () => {
    server.kill('SIGINT');
  });
  
  process.on('SIGTERM', () => {
    server.kill('SIGTERM');
  });
}

// Start the setup process
setupVenv();
