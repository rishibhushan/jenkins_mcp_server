#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

// choose python binary; allow override
const pythonCmd = process.env.PYTHON_CMD || (process.platform === 'win32' ? 'python' : 'python3');

// Path to project root (directory containing this cli.js)
const projectRoot = path.dirname(__filename);

// Path to src where your python package lives
const srcPath = path.join(projectRoot, 'src');

// Build PYTHONPATH: prepend src so the package is importable
const existingPyPath = process.env.PYTHONPATH || '';
const joinedPyPath = srcPath + (existingPyPath ? path.delimiter + existingPyPath : '');

// Build args: run module
const args = ['-m', 'jenkins_mcp_server', ...process.argv.slice(2)];

// Prepare env forwarded from parent but with modified PYTHONPATH
const env = Object.assign({}, process.env, { PYTHONPATH: joinedPyPath });

// Spawn child, inherit stdio so output shows to user
const p = spawn(pythonCmd, args, {
  stdio: 'inherit',
  env: env,
  cwd: process.cwd()
});

p.on('exit', (code) => {
  process.exit(code);
});
p.on('error', (err) => {
  console.error('Failed to start python process:', err);
  process.exit(1);
});