# 🧠 Jenkins MCP Server

**Jenkins MCP Server** is an AI-enabled Model Context Protocol (MCP) server that exposes Jenkins automation through natural-language commands.

Designed to work seamlessly with automation clients such as:
- 🖥️ **VS Code MCP** - Direct integration with Claude in VS Code
- 🔌 **Any MCP-compatible client** - Universal compatibility

## ✨ About codebase

- ✅ **Codebase** - cleaner, more maintainable
- ✅ **Error messages** - Know exactly what's wrong and how to fix it
- ✅ **Flexible configuration** - Multiple ways to configure (VS Code, .env, environment)
- ✅ **Cross-platform** - Seamless support for Windows, macOS, and Linux
- ✅ **Logging** - Professional logging with `--verbose` flag
- ✅ **Dependency management** - Automatic detection and installation

---

## 📦 Features

This project includes:
- 🐍 Python backend powered by `python-jenkins`
- 📦 Node.js `npx` wrapper for zero-install execution
- 🔄 Automatic virtual environment creation + dependency installation
- 🌐 Corporate proxy/certificate auto-detection support
- 🪟 Windows, macOS, and Linux support
- 🛠️ **20+ Jenkins management tools**

### 🧩 Job Management Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `create-job` | Create a new job with XML config | `job_name`, `config_xml` |
| `create-job-from-copy` | Clone an existing job | `new_job_name`, `source_job_name` |
| `create-job-from-data` | Create job from structured data | `job_name`, `config_data` |
| `delete-job` | Delete a job | `job_name` |
| `enable-job` | Enable a disabled job | `job_name` |
| `disable-job` | Disable a job | `job_name` |
| `rename-job` | Rename a job | `job_name`, `new_name` |
| `trigger-build` | Trigger a build (with optional params) | `job_name`, `parameters?` |
| `stop-build` | Stop a running build | `job_name`, `build_number` |

### 📊 Information & Monitoring Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list-jobs` | List all Jenkins jobs | *(none)* |
| `get-job-details` | Get detailed job information | `job_name` |
| `get-build-info` | Get specific build information | `job_name`, `build_number` |
| `get-build-console` | Retrieve console output/logs | `job_name`, `build_number` |
| `get-last-build-number` | Get latest build number | `job_name` |
| `get-last-build-timestamp` | Get last build timestamp | `job_name` |
| `get-queue-info` | Inspect the build queue | *(none)* |
| `list-nodes` | List all Jenkins nodes/agents | *(none)* |
| `get-node-info` | Get node/agent information | `node_name` |

### ⚙️ Configuration Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get-job-config` | Fetch job configuration XML | `job_name` |
| `update-job-config` | Update job configuration XML | `job_name`, `config_xml` |

---

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

---

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

Create a `.env` file in your project directory:

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

---

## 🎯 Running the Server

### Method 1: Using npx (Recommended - Zero Setup)

**With VS Code settings:**
```bash
npx github:rishibhushan/jenkins_mcp_server
```

**With custom .env file:**
```bash
npx github:rishibhushan/jenkins_mcp_server --env-file /path/to/.env
```

**With verbose logging:**
```bash
npx github:rishibhushan/jenkins_mcp_server --verbose
```

**Skip VS Code settings:**
```bash
npx github:rishibhushan/jenkins_mcp_server --no-vscode
```

This automatically:
- ✅ Detects Python 3 installation
- ✅ Creates isolated virtual environment (`.venv`)
- ✅ Installs all dependencies
- ✅ Starts the MCP server

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

---

## 🔌 Integration Examples

### VS Code MCP Client

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "jenkins": {
        "type": "stdio",
        "command": "npx",
        "args": [
          "github:rishibhushan/jenkins_mcp_server"
        ]
      }
    }
  }
}
```

**With .env file and proxy settings:**
```json
{
  "mcp": {
    "servers": {
      "jenkins": {
        "type": "stdio",
        "command": "npx",
        "args": [
          "github:rishibhushan/jenkins_mcp_server",
          "--verbose",
          "--env-file",
          "/path/to/.env"
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

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "npx",
      "args": [
        "github:rishibhushan/jenkins_mcp_server"
      ]
    }
  }
}
```

**Where to find claude_desktop_config.json:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

---

## 💡 Usage Examples

### Natural Language Commands

Once configured, you can use natural language with your MCP client:

```
"List all Jenkins jobs"
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
jobs = client.get_jobs()
for job in jobs:
    print(f"Job: {job['name']} - Status: {job['color']}")

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

---

## 🔧 Troubleshooting

### Python Not Found
```
Error: Python 3 is required but not found.
```
**Solution**: Install Python 3.8+ from https://www.python.org/downloads/

### Configuration Issues
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

### Connection Failed
```
Failed to connect to Jenkins at http://localhost:8080
```
**Solution**: 
1. Verify Jenkins is running: `curl http://localhost:8080/api/json`
2. Check firewall settings
3. Verify URL is correct (include port if needed)
4. Test authentication credentials

### Dependency Installation Failed
```
Failed to install dependencies
```
**Solution**:
1. Check internet connection
2. If behind a proxy, set `HTTP_PROXY` and `HTTPS_PROXY` environment variables
3. Try manual installation: `.venv/bin/pip install -r requirements.txt`

### Enable Debug Logging

Run with verbose flag to see detailed logs:
```bash
jenkins-mcp-server --verbose
```

---

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

---

## 📚 Project Structure

```
jenkins_mcp_server/
├── bin/
│   └── jenkins-mcp.js          # Node.js wrapper script
├── src/
│   └── jenkins_mcp_server/
│       ├── __init__.py         # Package initialization & main()
│       ├── __main__.py         # Entry point for python -m
│       ├── config.py           # Configuration management
│       ├── jenkins_client.py   # Jenkins API client
│       └── server.py           # MCP server implementation
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
├── package.json               # Node.js configuration
└── README.md                  # This file
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use API tokens**, not passwords - More secure and revocable
3. **Rotate tokens regularly** - Generate new tokens periodically
4. **Use environment-specific configs** - Separate dev/staging/prod credentials
5. **Review permissions** - Only grant necessary Jenkins permissions
6. **Keep dependencies updated** - Run `pip install --upgrade -r requirements.txt`

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Powered by [python-jenkins](https://python-jenkins.readthedocs.io/)
- Inspired by the need for AI-powered DevOps automation

---

## 📞 Support

- **Issues**: https://github.com/rishibhushan/jenkins_mcp_server/issues
- **Discussions**: https://github.com/rishibhushan/jenkins_mcp_server/discussions
- **Email**: rishibharat2007@gmail.com

---

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
