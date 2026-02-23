
# 🧠 Jenkins MCP Server

![Build Status](https://img.shields.io/github/actions/workflow/status/rishibhushan/jenkins_mcp_server/docker-publish.yml?branch=main)
![npm version](https://img.shields.io/npm/v/@rishibhushan/jenkins-mcp-server)
![Docker](https://img.shields.io/badge/docker-ghcr.io%2Frishibhushan%2Fjenkins--mcp--server-blue)

**Jenkins MCP Server** is an AI-enabled Model Context Protocol (MCP) server that exposes Jenkins automation through natural-language commands.

Designed to work seamlessly with automation clients such as:
- 🖥️ **VS Code MCP** - Direct integration with Claude in VS Code
- 🖥️ **Claude Desktop** - AI-powered Jenkins automation
- 🔌 **Any MCP-compatible client** - Universal compatibility

## ✨ What's New in v1.1.16

### 🚀 Latest Improvements (v1.1.16)
- ⚡ **Instant startup** - Server initialization in <1 second (previously 30-60s)
- 🔧 **Simplified architecture** - Streamlined Node.js wrapper for better reliability
- 🌐 **Universal compatibility** - Works seamlessly with VSCode, Claude Desktop, and all MCP clients
- 🐛 **Critical fixes** - Resolved initialization timeouts and network blocking issues

### 🚀 Performance Enhancements (v1.1.0)
- ⚡ **10x faster** - Client connection caching for repeated operations
- 📊 **Smart caching** - Job list caching with 30-60s TTL (5-10x improvement)
- 🎯 **Optimized queries** - Reduced API calls by 33-83%

### 🛡️ Reliability Improvements
- ✅ **86% validation coverage** - Input validation on 18/21 tools
- ⏱️ **Configurable timeouts** - No more hanging API calls
- 💬 **Better error messages** - Clear troubleshooting steps
- 🏥 **Health check tool** - Instant diagnostics

### 🎛️ Advanced Features
- 📦 **Batch operations** - Trigger up to 20 builds at once
- 📈 **Metrics & telemetry** - Track tool usage and performance
- 🗂️ **Cache management** - Monitor and control caching
- 📊 **Console improvements** - Line-based truncation with tail mode
- 🎨 **Structured logging** - Better debugging with JSON logs


## ✨ About codebase

- ✅ **Codebase** - cleaner, more maintainable
- ✅ **Error messages** - Know exactly what's wrong and how to fix it
- ✅ **Flexible configuration** - Multiple ways to configure (VS Code, .env, environment)
- ✅ **Cross-platform** - Seamless support for Windows, macOS, and Linux
- ✅ **Logging** - Professional logging with `--verbose` flag
- ✅ **Dependency management** - Automatic detection and installation
- ✅ **Performance** - 10x faster with intelligent caching and optimization
- ✅ **Reliability** - Comprehensive input validation and error handling


## 📦 Features

This project includes:
- 🐍 Python backend powered by `python-jenkins`
- 📦 Node.js `npx` wrapper for zero-install execution
- 🔄 Automatic virtual environment creation + dependency installation
- 🌐 Corporate proxy/certificate auto-detection support
- 🪟 Windows, macOS, and Linux support
- 🛠️ **26 Jenkins management tools** (upgraded from 20!)

### 🧩 Build Operations
| Tool Name | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `trigger-build` | Trigger a Jenkins job build with optional parameters | `job_name` | `parameters` |
| `stop-build` | Stop a running Jenkins build | `job_name`, `build_number` | *(none)* |
| `trigger-multiple-builds` | **NEW!** Trigger builds for multiple jobs at once | `job_names` | `parameters`, `wait_for_start` |

### 📊 Job Information
| Tool Name | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `list-jobs` | List all Jenkins jobs with optional filtering **and caching** | *(none)* | `filter`, `use_cache` |
| `get-job-details` | Get detailed information about a Jenkins job | `job_name` | `max_recent_builds` |

### 🛠️ Build Information
| Tool Name | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `get-build-info` | Get information about a specific build | `job_name`, `build_number` | *(none)* |
| `get-build-console` | Get console output with **smart truncation** | `job_name`, `build_number` | `max_lines`, `tail_only` |
| `get-last-build-number` | Get the last build number for a job | `job_name` | *(none)* |
| `get-last-build-timestamp` | Get the timestamp of the last build | `job_name` | *(none)* |

### 🧩 Job Management
| Tool Name | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `create-job` | Create a new Jenkins job with XML configuration | `job_name`, `config_xml` | *(none)* |
| `create-job-from-copy` | Create a new job by copying an existing one | `new_job_name`, `source_job_name` | *(none)* |
| `create-job-from-data` | Create a job from structured data (auto-generated XML) | `job_name`, `config_data` | `root_tag` |
| `delete-job` | Delete an existing job | `job_name` | *(none)* |
| `enable-job` | Enable a disabled Jenkins job | `job_name` | *(none)* |
| `disable-job` | Disable a Jenkins job | `job_name` | *(none)* |
| `rename-job` | Rename an existing Jenkins job | `job_name`, `new_name` | *(none)* |

### ⚙️ Job Configuration
| Tool Name | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `get-job-config` | Fetch job XML configuration | `job_name` | *(none)* |
| `update-job-config` | Update job XML configuration | `job_name`, `config_xml` | *(none)* |

### 🖥️ System Information
| Tool Name | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `get-queue-info` | Get Jenkins build queue info | *(none)* | *(none)* |
| `list-nodes` | List all Jenkins nodes | *(none)* | *(none)* |
| `get-node-info` | Get information about a Jenkins node | `node_name` | *(none)* |
| `health-check` | **NEW!** Run diagnostics on Jenkins connection | *(none)* | *(none)* |

### 📊 Monitoring & Management
| Tool Name | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `get-cache-stats` | **NEW!** Get cache statistics and information | *(none)* | *(none)* |
| `clear-cache` | **NEW!** Clear all cached data | *(none)* | *(none)* |
| `get-metrics` | **NEW!** Get usage metrics and performance stats | *(none)* | `tool_name` |
| `configure-webhook` | **NEW!** Configure webhook notifications | `job_name`, `webhook_url`, `events` | *(none)* |

For detailed technical documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).


## 🚀 Quick Start

### Prerequisites

**Node.js** (v14 or higher) is required for the npx wrapper.

<details>
<summary><b>Windows Installation</b></summary>

```powershell
# Using winget (recommended)
winget install OpenJS.NodeJS.LTS

# Verify installation
node -v
npm -v
```

Or download manually from https://nodejs.org/
</details>

<details>
<summary><b>macOS Installation</b></summary>

```bash
# Install nvm (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Reload shell
source ~/.nvm/nvm.sh

# Install Node LTS
nvm install --lts
nvm use --lts

# Verify installation
node -v
npm -v
```
</details>

<details>
<summary><b>Linux Installation</b></summary>

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Fedora/RHEL
curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
sudo dnf install -y nodejs

# Verify installation
node -v
npm -v
```
</details>


## ⚙️ Configuration

Jenkins MCP Server supports multiple configuration methods. Choose the one that works best for you:

### Option 1: VS Code Settings (Recommended)

Add to your VS Code `settings.json`:

```json
{
  "jenkins-mcp-server": {
    "jenkins": {
      "url": "http://jenkins.example.com:8080",
      "username": "your-username",
      "token": "your-api-token"
    }
  }
}
```

**Where to find settings.json:**
- **Windows**: `%APPDATA%\Code\User\settings.json`
- **macOS**: `~/Library/Application Support/Code/User/settings.json`
- **Linux**: `~/.config/Code/User/settings.json`

### Option 2: Environment File (.env)

Create a file `.env` in your local:

```bash
JENKINS_URL=http://jenkins.example.com:8080
JENKINS_USERNAME=your-username
JENKINS_TOKEN=your-api-token
```

**Note**: Use API token instead of password for better security.

### Option 3: Environment Variables

```bash
# Linux/macOS
export JENKINS_URL=http://jenkins.example.com:8080
export JENKINS_USERNAME=your-username
export JENKINS_TOKEN=your-api-token

# Windows (PowerShell)
$env:JENKINS_URL="http://jenkins.example.com:8080"
$env:JENKINS_USERNAME="your-username"
$env:JENKINS_TOKEN="your-api-token"
```

### Configuration Priority

Settings are loaded in this order (later overrides earlier):
1. Default `.env` file
2. Environment variables
3. Custom `.env` file (via `--env-file`)
4. VS Code settings
5. Direct parameters

### Getting Your Jenkins API Token

1. Log into Jenkins
2. Click your name (top right) → **Configure**
3. Scroll to **API Token** section
4. Click **Add new Token**
5. Give it a name and click **Generate**
6. Copy the token (⚠️ it won't be shown again!)


## 🚀 Installation/Running the Server

### Option 1: Using npx (No Installation Required)
```bash
# if .env file is located in the current directory
npx @rishibhushan/jenkins-mcp-server --env-file .env

# OR if .env file is located in /path/to/.env
npx @rishibhushan/jenkins-mcp-server --env-file /path/to/.env
```
**NPX Usage:**
- Always use `--yes` flag with npx for automatic package installation
- First run may take 10-20 seconds to set up Python environment
- Subsequent runs are instant (environment is cached)

**Example:**
````bash
npx --yes @rishibhushan/jenkins-mcp-server --env-file .env
````

### Option 2: Global Installation
```bash
# Install globally
npm install -g @rishibhushan/jenkins-mcp-server

# Run
jenkins-mcp-server --env-file .env
```

### Option 3: From GitHub
```bash
npx github:rishibhushan/jenkins_mcp_server --env-file .env
```

This automatically:
- ✅ Installs all dependencies
- ✅ Starts the Jenkins MCP server

---

### Method 2: Direct Python Execution

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m jenkins_mcp_server --env-file /path/to/.env
```

### Command-Line Options

```
jenkins-mcp-server [options]

Options:
  --env-file PATH    Path to custom .env file
  --verbose, -v      Enable verbose/debug logging
  --no-vscode        Skip loading VS Code settings
  --version          Show version information
  --help, -h         Show help message
```

## 🐳 Run with Docker (Standalone / CI / Headless environments)

Docker support allows you to run the MCP server without installing Node
or Python locally.

### 📦 Build the image

``` bash
docker build -t jenkins-mcp-server .
```




### ▶️ Run the container

``` bash
docker run -it --rm \
  -p 3000:3000 \
  -e JENKINS_URL=http://your-jenkins:8080 \
  -e JENKINS_USERNAME=your_username \
  -e JENKINS_TOKEN=your_token \
  jenkins-mcp-server
```

### 📥 Pull Prebuilt Image (Recommended)

Instead of building locally, you can pull the official image:

```bash
docker pull ghcr.io/rishibhushan/jenkins-mcp-server:latest
```

### 🔌 MCP Client Configuration (Docker)

Example configuration for MCP clients:

```json
{
  "jenkins": {
    "command": "docker",
    "args": [
      "run",
      "-i",
      "--rm",
      "-e",
      "JENKINS_URL",
      "-e",
      "JENKINS_USERNAME",
      "-e",
      "JENKINS_TOKEN",
      "ghcr.io/rishibhushan/jenkins-mcp-server:latest"
    ]
  }
}
```

### 🔑 Required Environment Variables
| Variable | Description |
|---|---|
|  JENKINS_URL  |  Jenkins base URL  |
|  JENKINS_USERNAME  |  Jenkins username  |
|  JENKINS_TOKEN  |  API token (recommended) |
|  JENKINS_PASSWORD  |  Password (if not using token)  |

### 🧠 When to use Docker

Docker is recommended when running the MCP server:

-   In CI/CD pipelines
-   On Jenkins agents
-   As a shared service
-   Outside VS Code
-   In production-like environments



## ⚙️ Configuration Priority

The server resolves configuration in this order:

1️⃣ Environment variables\
2️⃣ `.env` file\
3️⃣ VS Code `settings.json`



## 🧪 Verify Server is Running

After starting, you should see logs indicating:

-   Jenkins configuration loaded
-   MCP server started
-   Listening on port `3000`

## 🔌 Integration with VSCode

1. **Install VSCode MCP Extension** (if not already installed)

2. **Configure the server** in your workspace or user settings:

**Option A: Using `mcp.json` (Recommended)**

```json
{
  "servers": {
    "jenkins": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "@rishibhushan/jenkins-mcp-server"
      ]
    }
  }
}
```

**Option B: Using settings.json**

Add to your VSCode `settings.json`. With `.env` file, `--verbose`, and proxy settings:
```json
{
  "mcp": {
    "servers": {
      "jenkins": {
        "type": "stdio",
        "command": "npx",
        "args": [
          "@rishibhushan/jenkins-mcp-server",
          "--verbose",
          "--env-file",
          "/absolute/path/to/your/.env"
        ],
        "env": {
          "HTTP_PROXY": "http://proxy.example.com:8080",
          "HTTPS_PROXY": "http://proxy.example.com:8080",
          "NO_PROXY": "localhost,127.0.0.1,.example.com"
        }
      }
    }
  }
}
```
**Important:**
- Always use **absolute paths** for the `--env-file` parameter
- Restart VSCode completely after configuration changes
- Check Output → Model Context Protocol for connection status

3. **Verify connection:**
   - Open Command Palette (Cmd/Ctrl+Shift+P)
   - Type "MCP" to see available commands
   - Should see "Discovered 26 tools" in Output panel

#### Troubleshooting VSCode Connection

If VSCode shows "Waiting for initialize response":
1. Ensure `.env` file path is **absolute**, not relative
2. Verify `.env` file has correct Jenkins credentials
3. Restart VSCode completely (quit and reopen)
4. Check Output → Model Context Protocol for error messages
5. Try running manually first: `npx --yes @rishibhushan/jenkins-mcp-server --env-file /path/to/.env`

## 🤖 Integration with Claude Desktop

1. **Locate Claude Desktop config:**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

   
2. **Add server configuration:**

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "npx",
      "args": [
        "@rishibhushan/jenkins-mcp-server",
        "--env-file",
        "/absolute/path/to/your/.env"
      ]
    }
  }
}
```

3. **Restart Claude Desktop** completely

4. **Verify:**
   - You should see a 🔌 icon in Claude's input area
   - Click it to see "jenkins" server with 26 tools

#### Troubleshooting Claude Desktop
Common issues:
- **Server disconnects after 60s:** Make sure you're on VPN if Jenkins requires it
- **No tools appear:** Check the config file path and restart Claude Desktop
- **Connection timeout:** Verify Jenkins URL is accessible from your network



## 🏢 Corporate Network / Proxy Setup

If you're behind a corporate proxy or firewall:

### Option 1: Set Environment Variables (Recommended)
```bash
# Set proxy environment variables
export HTTP_PROXY=http://your-proxy:8080
export HTTPS_PROXY=http://your-proxy:8080
export NO_PROXY=localhost,127.0.0.1

# Run the server (wrapper will auto-detect proxy)
npx @rishibhushan/jenkins-mcp-server --env-file .env
```

### Option 2: Configure npm and pip
```bash
# Configure npm proxy
npm config set proxy http://your-proxy:8080
npm config set https-proxy http://your-proxy:8080

# Configure pip proxy (for SSL issues)
pip config set global.proxy http://your-proxy:8080
pip config set global.trusted-host "pypi.org pypi.python.org files.pythonhosted.org"

# Run the server
npx @rishibhushan/jenkins-mcp-server --env-file .env
```

### Option 3: Claude Desktop with Proxy

Add proxy settings to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "npx",
      "args": [
        "@rishibhushan/jenkins-mcp-server",
        "--env-file",
        "/path/to/.env"
      ],
      "env": {
        "HTTP_PROXY": "http://your-proxy:8080",
        "HTTPS_PROXY": "http://your-proxy:8080",
        "NO_PROXY": "localhost,127.0.0.1"
      }
    }
  }
}
```

### SSL Certificate Issues

If you encounter SSL certificate errors:
```bash
# Disable SSL verification for pip (one-time setup)
pip config set global.trusted-host "pypi.org pypi.python.org files.pythonhosted.org"

# Or use environment variable
export PIP_TRUSTED_HOST="pypi.org pypi.python.org files.pythonhosted.org"
```

The Node.js wrapper automatically handles SSL certificate issues when it detects proxy environment variables.


## 💡 Usage Examples

### Natural Language Commands

Once configured, you can use natural language with your MCP client:

```
"List all Jenkins jobs"
"List jobs with 'backend' in the name"  - # Filter jobs containing "backend"
"Show me all production jobs"  - # Filter jobs containing "prod"
"Show me the last build of my-project"
"Trigger a build for deploy-prod with parameter env=production"
"What's in the build queue?"
"Show me the console output of build #42 for backend-service"
"Create a new job called test-job by copying prod-job"
"Disable the old-job"
```

### Programmatic Usage (Python)

```python
from config import get_settings
from jenkins_client import get_jenkins_client

# Load settings
settings = get_settings()

# Create client
client = get_jenkins_client(settings)

# List jobs
all_jobs = client.get_jobs()
for job in all_jobs:
    print(f"Job: {job['name']} - Status: {job['color']}")

# Filter in Python
backend_jobs = [job for job in all_jobs if 'backend' in job['name'].lower()]

# Trigger a build
result = client.build_job(
    "my-job",
    parameters={"BRANCH": "main", "ENV": "staging"}
)
print(f"Build queued: {result['queue_id']}")
print(f"Build number: {result['build_number']}")

# Get console output
if result['build_number']:
    output = client.get_build_console_output(
        "my-job",
        result['build_number']
    )
    print(output)
```


## 🔍 Quick Troubleshooting

### Server won't start
```bash
# Test if server works manually
npx --yes @rishibhushan/jenkins-mcp-server --env-file /path/to/.env

# Should start and wait for input (Ctrl+C to exit)
```

### VSCode/Claude Desktop can't connect
- ✅ Use **absolute paths** for `--env-file`
- ✅ Include `--yes` flag with npx
- ✅ Restart application completely after config changes
- ✅ Check if Jenkins is accessible (try in browser)
- ✅ Verify `.env` file has correct credentials

### Server connects but times out
- ✅ Connect to VPN if Jenkins is on private network
- ✅ Check firewall settings
- ✅ Verify Jenkins URL is correct
- ✅ Test with: `curl -I http://your-jenkins-url:8080`

### "Module not found" errors
- ✅ Delete `.venv` folder and let it reinstall
- ✅ Clear npm cache: `npm cache clean --force`
- ✅ Try with latest version: `npx --yes @rishibhushan/jenkins-mcp-server@latest`


## 🔧 Troubleshooting

### Common Issues

#### Python Not Found
```
Error: Python 3 is required but not found.
```
**Solution**: Install Python 3.8+ from https://www.python.org/downloads/

#### Configuration Issues
```
ERROR: Jenkins configuration is incomplete!
```
**Solution**: Verify you have set `JENKINS_URL`, `JENKINS_USERNAME`, and `JENKINS_TOKEN`

Check your configuration:
```bash
# View .env file
cat .env

# Check environment variables
env | grep JENKINS

# Check VS Code settings
cat ~/.config/Code/User/settings.json | grep jenkins
```

#### Connection Failed
```
Failed to connect to Jenkins at http://localhost:8080
```
**Solution**: 
1. Verify Jenkins is running: `curl http://localhost:8080/api/json`
2. Check firewall settings
3. Verify URL is correct (include port if needed)
4. Test authentication credentials

#### Dependency Installation Failed
```
Failed to install dependencies
```
**Solution**:
1. Check internet connection
2. If behind a proxy, set `HTTP_PROXY` and `HTTPS_PROXY` environment variables
3. Try manual installation: `.venv/bin/pip install -r requirements.txt`

---

### 🚨 VPN & Corporate Network Issues

If you're experiencing timeout issues with Claude Desktop or other MCP clients when using a VPN or corporate network, this section provides step-by-step solutions.

#### Symptom: Request Timeout After 60 Seconds

**Error in logs:**
```
McpError: MCP error -32001: Request timed out
Server transport closed unexpectedly
```

**Root Cause**: The Python process spawned by `npx` may not properly inherit VPN network routing, causing it to fail when connecting to internal Jenkins servers.

---

### Solution 1: Bypass Proxy for PyPI (For Dependency Installation Issues)

If you're getting proxy errors during dependency installation:

**Add to your `claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "npx",
      "args": [
        "@rishibhushan/jenkins-mcp-server",
        "--env-file",
        "/path/to/.env"
      ],
      "env": {
        "NO_PROXY": "pypi.org,pypi.python.org,files.pythonhosted.org",
        "PIP_NO_PROXY": "pypi.org,pypi.python.org,files.pythonhosted.org"
      }
    }
  }
}
```

---

### Solution 2: Use Direct Python Execution (Recommended for VPN)

This bypasses the `npx` wrapper entirely and uses Python directly, which properly inherits your system's network routing.

#### Step 1: Locate the Installed Package

**For macOS/Linux:**
```bash
# Find the npx cache directory
PACKAGE_DIR=$(find ~/.npm/_npx -name "jenkins-mcp-server" -type d 2>/dev/null | head -1)
echo $PACKAGE_DIR
```

**For Windows (PowerShell):**
```powershell
# Find the npx cache directory
$PACKAGE_DIR = Get-ChildItem -Path "$env:LOCALAPPDATA\npm-cache\_npx" -Recurse -Directory -Filter "jenkins-mcp-server" | Select-Object -First 1 -ExpandProperty FullName
Write-Host $PACKAGE_DIR
```

The output will be something like:
- **macOS/Linux**: `/Users/username/.npm/_npx/<hash>/node_modules/@rishibhushan/jenkins-mcp-server`
- **Windows**: `C:\Users\username\AppData\Local\npm-cache\_npx\<hash>\node_modules\@rishibhushan\jenkins-mcp-server`

#### Step 2: Update Claude Desktop Configuration

Replace `<PACKAGE_DIR>` with the path from Step 1:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "<PACKAGE_DIR>/.venv/bin/python",
      "args": [
        "-m",
        "jenkins_mcp_server",
        "--env-file",
        "/path/to/your/.env"
      ],
      "env": {
        "PYTHONPATH": "<PACKAGE_DIR>/src"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "<PACKAGE_DIR>\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "jenkins_mcp_server",
        "--env-file",
        "C:\\path\\to\\your\\.env"
      ],
      "env": {
        "PYTHONPATH": "<PACKAGE_DIR>\\src"
      }
    }
  }
}
```

#### Step 3: Example Configuration

**Complete example for macOS:**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "/Users/username/.npm/_npx/a88b5f55f40c4229/node_modules/@rishibhushan/jenkins-mcp-server/.venv/bin/python",
      "args": [
        "-m",
        "jenkins_mcp_server",
        "--env-file",
        "/Users/username/projects/jenkins_mcp_server/.env"
      ],
      "env": {
        "PYTHONPATH": "/Users/username/.npm/_npx/a88b5f55f40c4229/node_modules/@rishibhushan/jenkins-mcp-server/src"
      }
    }
  }
}
```

#### Step 4: Restart Claude Desktop

1. **Connect to your VPN first**
2. Quit Claude Desktop completely
3. Start Claude Desktop
4. Check the MCP server connection in settings

---

### Solution 3: Use Local Git Clone (Best for Development)

If you're developing or frequently updating, use a local clone:

#### Step 1: Clone and Setup
```bash
# Clone the repository
git clone https://github.com/rishibhushan/jenkins_mcp_server.git
cd jenkins_mcp_server

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Step 2: Configure Claude Desktop

**macOS/Linux:**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "/path/to/jenkins_mcp_server/.venv/bin/python",
      "args": [
        "-m",
        "jenkins_mcp_server",
        "--env-file",
        "/path/to/jenkins_mcp_server/.env"
      ],
      "env": {
        "PYTHONPATH": "/path/to/jenkins_mcp_server/src"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "C:\\path\\to\\jenkins_mcp_server\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "jenkins_mcp_server",
        "--env-file",
        "C:\\path\\to\\jenkins_mcp_server\\.env"
      ],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\jenkins_mcp_server\\src"
      }
    }
  }
}
```
---

### Solution 4: Use Global Installation with Direct Python Path

If you prefer to use global installation but still face VPN/timeout issues, you can combine both approaches.

#### Step 1: Install Globally

**Disconnect from VPN first** (to avoid proxy issues during installation):
```bash
# Install globally
npm install -g @rishibhushan/jenkins-mcp-server

# Verify installation
jenkins-mcp-server --version
```

#### Step 2: Locate Global Installation Directory

**For macOS/Linux:**
```bash
# Find the global npm directory
npm root -g

# This typically returns something like:
# /usr/local/lib/node_modules
# or
# /Users/username/.npm-global/lib/node_modules

# Your package will be at:
# <npm-root>/@rishibhushan/jenkins-mcp-server
```

**For Windows (PowerShell):**
```powershell
# Find the global npm directory
npm root -g

# This typically returns something like:
# C:\Users\username\AppData\Roaming\npm\node_modules

# Your package will be at:
# <npm-root>\@rishibhushan\jenkins-mcp-server
```

#### Step 3: Find the Python Path

Once you know the installation directory:

**macOS/Linux:**
```bash
# If npm root -g shows: /usr/local/lib/node_modules
# Your Python path will be:
/usr/local/lib/node_modules/@rishibhushan/jenkins-mcp-server/.venv/bin/python

# Verify it exists:
ls -la /usr/local/lib/node_modules/@rishibhushan/jenkins-mcp-server/.venv/bin/python
```

**Windows:**
```powershell
# If npm root -g shows: C:\Users\username\AppData\Roaming\npm\node_modules
# Your Python path will be:
C:\Users\username\AppData\Roaming\npm\node_modules\@rishibhushan\jenkins-mcp-server\.venv\Scripts\python.exe

# Verify it exists:
Test-Path "C:\Users\username\AppData\Roaming\npm\node_modules\@rishibhushan\jenkins-mcp-server\.venv\Scripts\python.exe"
```

#### Step 4: Configure Your MCP Client

**For Claude Desktop (macOS/Linux):**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "/usr/local/lib/node_modules/@rishibhushan/jenkins-mcp-server/.venv/bin/python",
      "args": [
        "-m",
        "jenkins_mcp_server",
        "--env-file",
        "/path/to/your/.env"
      ],
      "env": {
        "PYTHONPATH": "/usr/local/lib/node_modules/@rishibhushan/jenkins-mcp-server/src"
      }
    }
  }
}
```

**For Claude Desktop (Windows):**
```json
{
  "mcpServers": {
    "jenkins": {
      "command": "C:\\Users\\username\\AppData\\Roaming\\npm\\node_modules\\@rishibhushan\\jenkins-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "jenkins_mcp_server",
        "--env-file",
        "C:\\path\\to\\your\\.env"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\username\\AppData\\Roaming\\npm\\node_modules\\@rishibhushan\\jenkins-mcp-server\\src"
      }
    }
  }
}
```

**For Other MCP Clients:**

Use the same pattern - replace the `command` with the direct Python path and set the `PYTHONPATH` environment variable.

#### Step 5: Test and Use

1. **Connect to your VPN**
2. **Restart your MCP client** (Claude Desktop, VS Code, etc.)
3. **Verify the connection** works

#### Why This Solution Works

- ✅ **Persistent installation** - No need to download on each use
- ✅ **Proper network routing** - Python process inherits VPN routing
- ✅ **Works across sessions** - Survives VPN connect/disconnect cycles
- ✅ **Easy updates** - Just run `npm update -g @rishibhushan/jenkins-mcp-server`
- ✅ **Universal** - Works with any MCP client (Claude, VS Code, etc.)

#### Quick Reference Commands
```bash
# Find your global installation
npm root -g

# Update global installation
npm update -g @rishibhushan/jenkins-mcp-server

# Uninstall if needed
npm uninstall -g @rishibhushan/jenkins-mcp-server

# Test the Python path works
/path/to/global/installation/.venv/bin/python -m jenkins_mcp_server --help
```

---

### 🧪 Testing Your Connection

Before configuring MCP clients, test your Jenkins connection manually:

#### Create a Test Script

Save this as `test_jenkins_connection.py`:

```python
#!/usr/bin/env python3
"""
Test Jenkins connectivity for MCP server troubleshooting
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

def test_connection():
    # Load environment
    env_file = '/path/to/your/.env'  # Update this path
    print(f"Loading environment from: {env_file}")
    load_dotenv(env_file)
    
    url = os.getenv('JENKINS_URL')
    username = os.getenv('JENKINS_USERNAME')
    token = os.getenv('JENKINS_TOKEN')
    
    print(f"\nJenkins Configuration:")
    print(f"  URL: {url}")
    print(f"  Username: {username}")
    print(f"  Token: {'***' if token else 'NOT SET'}")
    
    # Test 1: DNS Resolution
    print(f"\n[Test 1] Testing DNS resolution...")
    import socket
    try:
        hostname = url.split('://')[1].split(':')[0]
        ip = socket.gethostbyname(hostname)
        print(f"  ✓ DNS resolved: {hostname} -> {ip}")
    except Exception as e:
        print(f"  ✗ DNS resolution failed: {e}")
        return False
    
    # Test 2: Basic connectivity
    print(f"\n[Test 2] Testing basic HTTP connectivity...")
    try:
        start = time.time()
        response = requests.get(f"{url}/api/json", timeout=5)
        elapsed = time.time() - start
        print(f"  ✓ Connection successful (no auth): {response.status_code} in {elapsed:.2f}s")
    except requests.exceptions.Timeout:
        print(f"  ✗ Connection timed out after 5 seconds")
        return False
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False
    
    # Test 3: Authenticated request
    print(f"\n[Test 3] Testing authenticated request...")
    try:
        start = time.time()
        response = requests.get(
            f"{url}/api/json",
            auth=(username, token),
            timeout=10
        )
        elapsed = time.time() - start
        print(f"  ✓ Authenticated request: {response.status_code} in {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Jenkins version: {data.get('version', 'unknown')}")
            print(f"  ✓ Number of jobs: {len(data.get('jobs', []))}")
        elif response.status_code == 401:
            print(f"  ✗ Authentication failed - check username/token")
            return False
        elif response.status_code == 403:
            print(f"  ✗ Access forbidden - check permissions")
            return False
    except Exception as e:
        print(f"  ✗ Authenticated request failed: {e}")
        return False
    
    # Test 4: python-jenkins library
    print(f"\n[Test 4] Testing python-jenkins library...")
    try:
        import jenkins
        start = time.time()
        server = jenkins.Jenkins(url, username=username, password=token)
        user = server.get_whoami()
        elapsed = time.time() - start
        print(f"  ✓ python-jenkins connection: {user['fullName']} in {elapsed:.2f}s")
    except Exception as e:
        print(f"  ✗ python-jenkins failed: {e}")
        return False
    
    print(f"\n✓ All tests passed! Jenkins MCP Server should work.")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Jenkins MCP Server - Connection Diagnostic")
    print("=" * 60)
    
    success = test_connection()
    sys.exit(0 if success else 1)
```

#### Run the Test

```bash
# Connect to VPN first
# Then run:
cd /path/to/jenkins_mcp_server
source .venv/bin/activate
python test_jenkins_connection.py
```

**Expected output if everything works:**
```
============================================================
Jenkins MCP Server - Connection Diagnostic
============================================================

[Test 1] Testing DNS resolution...
  ✓ DNS resolved: jenkins.example.com -> 10.0.0.1

[Test 2] Testing basic HTTP connectivity...
  ✓ Connection successful (no auth): 200 in 0.45s

[Test 3] Testing authenticated request...
  ✓ Authenticated request: 200 in 0.52s
  ✓ Jenkins version: 2.401.3
  ✓ Number of jobs: 42

[Test 4] Testing python-jenkins library...
  ✓ python-jenkins connection: John Doe in 0.38s

✓ All tests passed! Jenkins MCP Server should work.
```

If all tests pass but MCP still fails, use Solution 2 (Direct Python Execution).

---

### 🆘 Still Having Issues?

If you're still experiencing problems after trying the solutions above:

1. **Check Claude Desktop logs:**
   - **macOS**: `~/Library/Logs/Claude/mcp-server-jenkins.log`
   - **Windows**: `%APPDATA%\Claude\logs\mcp-server-jenkins.log`
   - **Linux**: `~/.config/Claude/logs/mcp-server-jenkins.log`

2. **Enable verbose logging** by adding `--verbose` to args:
   ```json
   "args": [
     "-m",
     "jenkins_mcp_server",
     "--env-file",
     "/path/to/.env",
     "--verbose"
   ]
   ```

3. **Verify VPN is active** before starting Claude Desktop:
   ```bash
   # Test if you can reach your Jenkins server
   curl -I http://your-jenkins-server:8080
   ```

4. **Check if other tools can reach Jenkins** while on VPN:
   - Try accessing Jenkins in your browser
   - Try `curl` from terminal
   - If both work but MCP doesn't, use Solution 2

5. **Open an issue** with:
   - Your operating system
   - Claude Desktop log file
   - Output of the connection test script
   - Your configuration (with credentials redacted)

---

### Enable Debug Logging

Run with verbose flag to see detailed logs:
```bash
jenkins-mcp-server --verbose
```



## 🧪 Development & Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v
```

### Build Package
```bash
# Install build tools
pip install build

# Build distribution
python -m build

# This creates:
# - dist/jenkins_mcp_server-1.0.0.tar.gz
# - dist/jenkins_mcp_server-1.0.0-py3-none-any.whl
```

### Local Development
```bash
# Clone repository
git clone https://github.com/rishibhushan/jenkins_mcp_server.git
cd jenkins_mcp_server

# Install in editable mode
pip install -e .

# Make changes, then test
jenkins-mcp-server --verbose
```


## 📚 Project Structure

```
jenkins_mcp_server/
├── bin/
│   └── jenkins-mcp.js          # Simplified Node.js wrapper (v1.1.16+)
├── src/
│   └── jenkins_mcp_server/
│       ├── __init__.py         # Package initialization & main()
│       ├── __main__.py         # Entry point for python -m
│       ├── config.py           # Configuration management
│       ├── jenkins_client.py   # Jenkins API client (with caching)
│       ├── cache.py            # Smart caching layer
│       ├── metrics.py          # Performance telemetry
│       └── server.py           # MCP server implementation (26 tools)
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
├── package.json                # Node.js configuration (ES modules)
└── README.md                   # This file
```


## 🔒 Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use API tokens**, not passwords - More secure and revocable
3. **Rotate tokens regularly** - Generate new tokens periodically
4. **Use environment-specific configs** - Separate dev/staging/prod credentials
5. **Review permissions** - Only grant necessary Jenkins permissions
6. **Keep dependencies updated** - Run `pip install --upgrade -r requirements.txt`


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 🙏 Acknowledgments

- Built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Powered by [python-jenkins](https://python-jenkins.readthedocs.io/)
- Inspired by the need for AI-powered DevOps automation


## 📞 Support

- **Issues**: https://github.com/rishibhushan/jenkins_mcp_server/issues
- **Discussions**: https://github.com/rishibhushan/jenkins_mcp_server/discussions


## 🗺️ Roadmap

- [ ] Add pipeline support
- [ ] Multi-Jenkins instance management
- [ ] Build artifact management
- [ ] Advanced filtering and search
- [ ] Real-time build monitoring
- [ ] Webhook integration
- [ ] Docker container support

---

**Made with ❤️ by [Rishi Bhushan](https://github.com/rishibhushan)**
