# 🧠 Jenkins MCP Server

**Jenkins MCP Server** is an AI-enabled command server built on top of [Jenkins](https://www.jenkins.io/) and the [python-jenkins](https://pypi.org/project/python-jenkins/) library.  
It enables automation clients (like Oracle SQLcl MCP, ChatGPT MCP, or any custom tools) to interact with Jenkins using structured or natural language commands.

This project provides:
- A Python backend to manage Jenkins operations (create/copy/build/manage jobs)
- A lightweight MCP-compatible interface
- A Node.js wrapper allowing you to launch it with `npx` (no manual setup)
- Auto-installation of dependencies for convenience

---

## 🚀 Features

### 🧩 Job Management
| Tool Name | Description |
|------------|-------------|
| `create-job` | Create a new Jenkins job using XML config |
| `create-job-from-copy` | Create a new job by copying an existing one |
| `create-job-from-dict` | Create a new job using a Python dict definition |
| `delete-job` | Delete an existing job |
| `enable-job` | Enable a disabled job |
| `disable-job` | Disable an enabled job |
| `rename-job` | Rename an existing job |

### 📊 Job Information
| Tool Name | Description |
|------------|-------------|
| `get-job-info` | Fetch job details |
| `get-build-info` | Fetch info about a specific build |
| `get-build-log` | Retrieve console output for a build |
| `get-last-build-number` | Get the most recent build number |
| `get-last-build-timestamp` | Get timestamp of the last build |

### ⚙️ Job Configuration
| Tool Name | Description |
|------------|-------------|
| `get-job-config` | Get the XML configuration of a job |
| `update-job-config` | Update job configuration XML |

### 🧠 Other Utilities
| Tool Name | Description |
|------------|-------------|
| `get-nodes` | List Jenkins nodes |
| `get-queue-info` | Get the Jenkins build queue |
| `stop-build` | Stop a running build |
| `build-job` | Trigger a build (returns queue and build IDs) |

---

## ⚙️ Environment Configuration

The `.env` file must define Jenkins connection info:

```bash
JENKINS_URL=http://your-jenkins:8080
JENKINS_USERNAME=your-user
JENKINS_TOKEN=your-api-token
```

Pass it to the server:
```bash
--env-file /path/to/.env
```

---

## 🧑‍💻 Running the Jenkins MCP Server

### Option 1 — Using Node.js + npx (Recommended)
No manual Python installation required.

```bash
npx github:rishibhushan/jenkins-mcp-server --env-file /path/to/.env
```

This automatically:
- Creates `.npx_venv`
- Installs Python dependencies
- Starts the MCP server

### Option 2 — Direct Python Execution
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python3 -m jenkins_mcp_server --env-file /path/to/.env
```

---

## 🧰 Example Usage

```bash
create-job-from-copy --new-job my-new-job --source-job base-job
build-job --job-name my-new-job --parameters '{"branch":"main"}'
get-build-info --job-name my-new-job --build-number 10
update-job-config --job-name my-new-job --xml-file ./config.xml
```

---

## 🔍 Debugging

Enable verbose output:
```bash
export LOG_LEVEL=DEBUG
npx github:rishibhushan/jenkins-mcp-server --env-file ./jenkins.env
```

---

## 📦 Dependencies

| Package | Purpose |
|----------|----------|
| python-jenkins | Jenkins REST API |
| requests | REST HTTP client |
| python-dotenv | Env file support |
| Node.js | Wrapper for easy execution |

---

## 🔐 Security Notes
- Never share your `.env` file.
- `.npx_venv` is isolated to protect your environment.
- Wrapper installs only from local `requirements.txt`.

---

## 🧾 License
License © 2025 Rishi Bhushan
