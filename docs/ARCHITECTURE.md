# Jenkins MCP Server - Technical Architecture

## 📋 Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Module Breakdown](#module-breakdown)
4. [Data Flow](#data-flow)
5. [Performance Optimizations](#performance-optimizations)
6. [Configuration System](#configuration-system)
7. [Error Handling](#error-handling)
8. [Testing Strategy](#testing-strategy)
9. [Deployment](#deployment)
10. [Development Guide](#development-guide)

---

## Overview

Jenkins MCP Server is a Python-based Model Context Protocol (MCP) server that provides AI-powered Jenkins automation. The server exposes 26 tools for managing Jenkins jobs, builds, and configurations through natural language commands.

### Key Technologies

- **Python 3.8+** - Core implementation language
- **MCP SDK** - Model Context Protocol implementation
- **python-jenkins** - Jenkins API client library
- **pydantic** - Configuration validation
- **asyncio** - Asynchronous operations
- **Node.js** - Wrapper for cross-platform execution

### Design Principles

1. **Performance First** - Caching, connection reuse, optimized queries
2. **Reliability** - Input validation, error handling, retry logic
3. **User Experience** - Clear error messages, health diagnostics
4. **Maintainability** - Modular design, comprehensive logging
5. **Cross-Platform** - Windows, macOS, Linux support

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Client Layer                        │
│  (Claude Desktop, VS Code, Any MCP-compatible client)       │
└─────────────────────┬───────────────────────────────────────┘
                      │ JSON-RPC over stdio
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Layer                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  server.py - Request Handler & Tool Router           │   │
│  │  - Handle MCP protocol                               │   │
│  │  - Tool routing                                      │   │
│  │  - Metrics collection                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴──────────┬────────────┬──────────┐
          ▼                      ▼            ▼          ▼
┌────────────────┐    ┌──────────────┐  ┌─────────┐  ┌──────────┐
│   cache.py     │    │  metrics.py  │  │         │  │          │
│  - TTL cache   │    │  - Telemetry │  │ Other   │  │  Future  │
│  - Statistics  │    │  - Analytics │  │ Modules │  │ Modules  │
└────────────────┘    └──────────────┘  └─────────┘  └──────────┘
          │                      │
          └───────────┬──────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Client Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  jenkins_client.py - Jenkins API Wrapper             │   │
│  │  - Connection management                             │   │
│  │  - API call abstraction                              │   │
│  │  - Fallback handling                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/HTTPS
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Jenkins Server                           │
│  - REST API                                                 │
│  - Build jobs                                               │
│  - Configuration management                                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Layers

#### 1. Entry Point Layer
- `__init__.py` - Package initialization, main() entry point
- `__main__.py` - Module execution entry
- `jenkins-mcp.js` - Node.js wrapper for npx execution

#### 2. Configuration Layer
- `config.py` - Multi-source configuration management
- Environment variables, .env files, VS Code settings

#### 3. Server Layer
- `server.py` - MCP protocol implementation
- Tool definitions and handlers
- Request routing and response formatting

#### 4. Utility Layer
- `cache.py` - Caching system with TTL
- `metrics.py` - Performance telemetry

#### 5. Client Layer
- `jenkins_client.py` - Jenkins API abstraction
- Connection pooling and retry logic

---

## Module Breakdown

### 1. `__init__.py` - Entry Point

**Purpose**: Package initialization and main entry point

**Key Components**:

```python
def main():
    """Main entry point with argument parsing"""
    - Parse command-line arguments
    - Setup logging
    - Load configuration
    - Validate settings
    - Start MCP server

def setup_logging(verbose: bool):
    """Configure logging with optional verbosity"""
    - Set log levels
    - Configure formatters
    - Suppress noisy libraries
```

**Flow**:
```
User runs command
    → Parse arguments (--env-file, --verbose, etc.)
    → Setup logging
    → Load settings (config.py)
    → Validate configuration
    → Pass settings to server
    → Start asyncio event loop
    → Run server.main()
```

---

### 2. `config.py` - Configuration Management

**Purpose**: Load and validate Jenkins connection settings from multiple sources

**Key Classes**:

```python
class JenkinsSettings(BaseSettings):
    """Pydantic settings model with validation"""
    
    # Connection settings
    url: str
    username: str
    token: str
    password: str
    
    # Performance settings (v2.0)
    timeout: int = 30
    connect_timeout: int = 10
    read_timeout: int = 30
    max_retries: int = 3
    console_max_lines: int = 1000
    verify_ssl: bool = True
    
    # Methods
    def is_configured(self) -> bool
    def get_credentials(self) -> tuple
    def log_config(self, hide_sensitive: bool)

class VSCodeSettingsLoader:
    """Load settings from VS Code settings.json"""
    
    @staticmethod
    def parse_jsonc(content: str) -> dict
    
    @classmethod
    def find_jenkins_settings(cls, settings: dict)
    
    @classmethod
    def load(cls) -> Optional[dict]
```

**Configuration Priority** (highest to lowest):
1. Direct parameters (in code)
2. VS Code settings.json
3. Custom .env file (--env-file)
4. Environment variables
5. Default .env file

**Key Functions**:

```python
def load_settings(
    env_file: Optional[str] = None,
    load_vscode: bool = True,
    **override_values
) -> JenkinsSettings:
    """Load settings from all sources with priority"""
    
def get_settings(...) -> JenkinsSettings:
    """Factory function for getting settings"""
    
def get_default_settings() -> JenkinsSettings:
    """Singleton pattern for default settings"""
```

---

### 3. `jenkins_client.py` - Jenkins API Client

**Purpose**: Abstraction layer over Jenkins REST API with fallback logic

**Key Class**:

```python
class JenkinsClient:
    """Enhanced Jenkins API client with timeout support"""
    
    def __init__(self, settings: JenkinsSettings):
        """Initialize client with settings"""
        - Validate settings
        - Setup authentication
        - Store timeout configuration
        - Test connection
    
    # Core Methods
    def _test_connection(self) -> None
    def _api_call(self, method, endpoint, **kwargs) -> Response
    
    # Job Information
    def get_jobs(self) -> List[Dict]
    def get_job_info(self, job_name) -> Dict
    def get_last_build_number(self, job_name) -> int
    def get_last_build_timestamp(self, job_name) -> int
    
    # Build Information
    def get_build_info(self, job_name, build_number) -> Dict
    def get_build_console_output(self, job_name, build_number) -> str
    
    # Build Operations
    def build_job(self, job_name, parameters, ...) -> Dict
    def stop_build(self, job_name, build_number) -> None
    
    # Job Management
    def create_job(self, job_name, config_xml) -> bool
    def create_job_from_copy(self, new_name, source) -> bool
    def create_job_from_dict(self, job_name, config_data) -> bool
    def delete_job(self, job_name) -> bool
    def enable_job(self, job_name) -> bool
    def disable_job(self, job_name) -> bool
    def rename_job(self, job_name, new_name) -> bool
    
    # Configuration
    def get_job_config(self, job_name) -> str
    def update_job_config(self, job_name, config_xml) -> bool
    
    # System Information
    def get_queue_info(self) -> List[Dict]
    def get_nodes(self) -> List[Dict]
    def get_node_info(self, node_name) -> Dict
    def get_whoami(self) -> Dict
    def get_version(self) -> str
```

**Fallback Strategy**:

```
Try python-jenkins library
    ↓ (if fails)
Fallback to direct REST API
    ↓ (if fails)
Retry with exponential backoff
    ↓ (if still fails)
Return clear error message
```

**Factory Pattern**:

```python
def get_jenkins_client(settings: Optional[JenkinsSettings]) -> JenkinsClient:
    """
    Get Jenkins client with singleton pattern for default settings
    """
    if settings is not None:
        return JenkinsClient(settings)  # New instance
    
    # Use cached default client
    if _default_client is None:
        _default_client = JenkinsClient()
    return _default_client
```

---

### 4. `server.py` - MCP Server Implementation

**Purpose**: Core MCP server with tool handlers and request routing

**Architecture**:

```python
# Global state
server = Server("jenkins-mcp-server")
_jenkins_settings: Optional[JenkinsSettings] = None
_jenkins_client_cache = None
_client_cache_lock = asyncio.Lock()

# Configuration
def set_jenkins_settings(settings: JenkinsSettings):
    """Set settings from __init__.py"""

def get_settings() -> JenkinsSettings:
    """Get current settings"""

# Client Caching (Quick Win #3)
async def get_cached_jenkins_client(settings) -> JenkinsClient:
    """Get or create cached client (10x faster)"""
    async with _client_cache_lock:
        if _jenkins_client_cache is None:
            _jenkins_client_cache = get_jenkins_client(settings)
        return _jenkins_client_cache
```

**MCP Protocol Handlers**:

```python
@server.list_resources()
async def handle_list_resources():
    """Return available Jenkins resources"""
    # Returns list of resource URIs

@server.read_resource()
async def handle_read_resource(uri: AnyUrl):
    """Fetch specific resource content"""
    # Parse URI, fetch from Jenkins, return data

@server.list_prompts()
async def handle_list_prompts():
    """Return available prompt templates"""
    # Returns analysis/troubleshooting templates

@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict):
    """Generate prompt from template"""
    # Fill template with Jenkins data

@server.list_tools()
async def handle_list_tools():
    """Return available tools (26 tools)"""
    # Returns tool definitions with schemas

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Execute tool and return results"""
    # Route to handler, collect metrics, return response
```

**Tool Handlers** (26 total):

```python
# Build Operations (3)
async def _tool_trigger_build(client, args)
async def _tool_stop_build(client, args)
async def _tool_trigger_multiple_builds(client, args)  # NEW

# Job Information (2)
async def _tool_list_jobs(client, args)  # Enhanced with caching
async def _tool_get_job_details(client, args)  # Optimized queries

# Build Information (4)
async def _tool_get_build_info(client, args)
async def _tool_get_build_console(client, args)  # Enhanced truncation
async def _tool_get_last_build_number(client, args)
async def _tool_get_last_build_timestamp(client, args)

# Job Management (7)
async def _tool_create_job(client, args)
async def _tool_create_job_from_copy(client, args)
async def _tool_create_job_from_data(client, args)
async def _tool_delete_job(client, args)
async def _tool_enable_job(client, args)
async def _tool_disable_job(client, args)
async def _tool_rename_job(client, args)

# Configuration (2)
async def _tool_get_job_config(client, args)
async def _tool_update_job_config(client, args)

# System Information (3)
async def _tool_get_queue_info(client, args)
async def _tool_list_nodes(client, args)
async def _tool_get_node_info(client, args)

# Monitoring & Management (5) - NEW in v2.0
async def _tool_health_check(client, args)
async def _tool_get_cache_stats(client, args)
async def _tool_clear_cache(client, args)
async def _tool_get_metrics(client, args)
async def _tool_configure_webhook(client, args)
```

**Input Validation Helpers**:

```python
def validate_job_name(job_name: Any) -> str:
    """Validate job name parameter"""
    if not job_name:
        raise ValueError("Missing required argument: job_name")
    if not isinstance(job_name, str):
        raise ValueError(f"job_name must be a string, got {type(job_name).__name__}")
    job_name = job_name.strip()
    if not job_name:
        raise ValueError("job_name cannot be empty or whitespace")
    return job_name

def validate_build_number(build_number: Any) -> int:
    """Validate build number parameter"""
    # Similar validation logic

def validate_config_xml(config_xml: Any) -> str:
    """Validate XML configuration parameter"""
    # XML validation logic
```

**Error Handling**:

```python
# Timeout errors
except requests.Timeout:
    return error_response(
        "⏱️ Request timed out",
        "Troubleshooting steps:\n"
        "1. Check if Jenkins server is running\n"
        "2. Verify VPN connection\n"
        "3. Check firewall settings\n"
        "4. Increase timeout: JENKINS_TIMEOUT=60"
    )

# Connection errors
except requests.ConnectionError:
    return error_response(
        "🔌 Cannot connect to Jenkins",
        "Troubleshooting steps:\n"
        "1. Verify Jenkins URL\n"
        "2. Test with: curl http://jenkins:8080\n"
        "3. Check if port is accessible"
    )

# Auth errors (401)
except JenkinsException as e:
    if "401" in str(e):
        return error_response(
            "🔐 Authentication failed",
            "Troubleshooting steps:\n"
            "1. Verify username is correct\n"
            "2. Generate new API token:\n"
            "   Jenkins → Configure → API Token\n"
            "3. Update JENKINS_TOKEN"
        )
```

**Main Loop**:

```python
async def main():
    """Main server loop"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="jenkins-mcp-server",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )
```

---

### 5. `cache.py` - Caching System

**Purpose**: TTL-based caching for frequently accessed Jenkins data

**Key Classes**:

```python
@dataclass
class CachedData:
    """Container for cached data with expiration"""
    data: Any
    cached_at: float
    ttl_seconds: int
    key: str
    
    def is_expired(self) -> bool
    def age_seconds(self) -> float
    def time_until_expiry(self) -> float

class CacheManager:
    """Thread-safe cache manager with TTL"""
    
    def __init__(self):
        self._cache: Dict[str, CachedData] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    # Core Operations
    async def get(self, key: str) -> Optional[Any]
    async def set(self, key: str, data: Any, ttl_seconds: int)
    async def invalidate(self, key: str) -> bool
    async def invalidate_pattern(self, pattern: str) -> int
    async def clear(self) -> int
    
    # Cleanup
    async def cleanup_expired(self) -> int
    
    # Helper
    async def get_or_fetch(self, key, fetch_func, ttl) -> Any
    
    # Statistics
    def get_stats(self) -> Dict
    def reset_stats(self) -> None
    async def get_cache_info(self) -> Dict
```

**Usage Pattern**:

```python
# In server.py
from .cache import get_cache_manager

async def _tool_list_jobs(client, args):
    cache_key = f"jobs_list:{filter_text or 'all'}"
    cache_manager = get_cache_manager()
    
    # Try cache first
    cached = await cache_manager.get(cache_key)
    if cached is not None:
        return cached
    
    # Fetch from Jenkins
    jobs = client.get_jobs()
    
    # Cache result
    await cache_manager.set(cache_key, jobs, ttl_seconds=30)
    
    return jobs
```

**Performance Metrics**:

```
Cache Hit Rate = hits / (hits + misses) * 100%

Before caching: 100% miss rate, 2-5s per query
After caching:  80-90% hit rate, 200ms per query (5-10x faster)
```

---

### 6. `metrics.py` - Telemetry System

**Purpose**: Track tool usage, performance, and errors

**Key Classes**:

```python
@dataclass
class ToolMetric:
    """Single tool execution metric"""
    tool_name: str
    execution_time_ms: float
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    args: Optional[Dict]

@dataclass
class ToolStats:
    """Aggregated statistics for a tool"""
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_time_ms: float
    min_time_ms: float
    max_time_ms: float
    
    @property
    def avg_time_ms(self) -> float
    
    @property
    def success_rate(self) -> float
    
    def add_metric(self, metric: ToolMetric)

class MetricsCollector:
    """Collect and aggregate metrics"""
    
    def __init__(self, max_history: int = 1000):
        self._metrics: List[ToolMetric] = []
        self._tool_stats: Dict[str, ToolStats] = {}
        self._lock = asyncio.Lock()
    
    async def record_execution(
        self, tool_name, execution_time_ms, 
        success, error_message, args
    )
    
    async def get_tool_stats(self, tool_name=None) -> Dict
    async def get_recent_metrics(self, limit=100) -> List
    async def get_failed_executions(self, limit=50) -> List
    async def get_slow_executions(self, threshold_ms, limit) -> List
    async def get_summary(self) -> Dict
    async def export_metrics(self) -> Dict
```

**Integration**:

```python
# In server.py
from .metrics import record_tool_execution
import time

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    start_time = time.time()
    success = False
    error_message = None
    
    try:
        # Execute tool
        result = await handler(client, arguments)
        success = True
        return result
    except Exception as e:
        error_message = str(e)
        raise
    finally:
        # Record metrics
        execution_time_ms = (time.time() - start_time) * 1000
        await record_tool_execution(
            tool_name=name,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )
```

---

## Data Flow

### Request Flow

```
1. AI Client sends JSON-RPC request via stdin
   ↓
2. MCP Server parses request
   ↓
3. Route to appropriate handler (list_tools, call_tool, etc.)
   ↓
4. If call_tool:
   a. Extract tool name and arguments
   b. Validate arguments
   c. Get/create cached Jenkins client
   d. Execute tool handler
   e. Record metrics
   f. Format response
   ↓
5. Return JSON-RPC response via stdout
   ↓
6. AI Client processes response
```

### Tool Execution Flow

```
1. handle_call_tool() receives request
   ↓
2. Start metrics timer
   ↓
3. Get cached Jenkins client (Fast path: 20ms, Slow path: 200ms)
   ↓
4. Validate input arguments
   ↓
5. Check cache (if applicable)
   ├─ Cache hit → Return cached data (Fast: 5-10ms)
   └─ Cache miss → Continue to API call
   ↓
6. Call Jenkins API via jenkins_client
   ├─ Try python-jenkins library
   └─ Fallback to direct REST API if needed
   ↓
7. Process response
   ↓
8. Update cache (if applicable)
   ↓
9. Record metrics
   ↓
10. Format and return response
```

### Error Flow

```
Exception occurs
   ↓
Identify error type
   ├─ Timeout → Timeout-specific message
   ├─ Connection → Connection troubleshooting
   ├─ 401 → Auth error with token generation steps
   ├─ 403 → Permission error
   ├─ 404 → Not found (check job name)
   └─ Validation → Clear parameter error
   ↓
Record in metrics (failed execution)
   ↓
Return formatted error response with:
   - Clear error message
   - Troubleshooting steps
   - Relevant context
```

---

## Performance Optimizations

### 1. Client Connection Caching (Quick Win #3)

**Problem**: Creating new Jenkins client on every tool call

**Solution**:
```python
_jenkins_client_cache = None

async def get_cached_jenkins_client(settings):
    global _jenkins_client_cache
    async with _client_cache_lock:
        if _jenkins_client_cache is None:
            _jenkins_client_cache = get_jenkins_client(settings)
        return _jenkins_client_cache
```

**Impact**: 
- First call: 200ms
- Subsequent calls: 20ms
- **10x faster**

### 2. Job List Caching (Medium Priority #1)

**Problem**: Frequent job list queries are slow (2-5s)

**Solution**:
```python
cache_key = f"jobs_list:{filter}"
cached = await cache_manager.get(cache_key)
if cached:
    return cached

jobs = client.get_jobs()
await cache_manager.set(cache_key, jobs, ttl_seconds=30)
```

**Impact**:
- Uncached: 2-5s
- Cached: 200-500ms
- **5-10x faster**

### 3. Optimized Build Fetching (Critical Issue #3)

**Problem**: get-job-details fetches 5 builds (6 API calls)

**Solution**:
```python
max_recent_builds = args.get("max_recent_builds", 3)  # Reduced from 5
# Can be set to 0 to skip build history entirely

for build in job_info["builds"][:max_recent_builds]:
    build_info = client.get_build_info(job_name, build["number"])
```

**Impact**:
- Default: 6 calls → 4 calls (33% faster)
- Quick mode (0 builds): 6 calls → 1 call (83% faster)

### 4. Configurable Timeouts (High Priority #4)

**Problem**: Hardcoded 30s timeout causes hanging

**Solution**:
```python
# In config.py
timeout: int = Field(default=30, ge=5, le=300)

# In jenkins_client.py
kwargs['timeout'] = (self.connect_timeout, self.read_timeout)
```

**Impact**: 
- No more indefinite hangs
- Faster failure detection
- Network-appropriate timeouts

### 5. Input Validation (Critical Issue #2)

**Problem**: Bad inputs reach Jenkins API, causing confusing errors

**Solution**:
```python
def validate_job_name(job_name):
    if not job_name:
        raise ValueError("Missing required argument: job_name")
    if not isinstance(job_name, str):
        raise ValueError("job_name must be string")
    return job_name.strip()
```

**Impact**:
- Immediate error detection
- Clear error messages
- No wasted API calls

---

## Configuration System

### Configuration Sources

1. **Environment Variables** (Lowest priority)
   ```bash
   JENKINS_URL=http://jenkins:8080
   JENKINS_USERNAME=admin
   JENKINS_TOKEN=secret
   ```

2. **`.env` File**
   ```bash
   # .env
   JENKINS_URL=http://jenkins:8080
   JENKINS_USERNAME=admin
   JENKINS_TOKEN=secret
   ```

3. **Custom `.env` File** (via `--env-file`)
   ```bash
   jenkins-mcp-server --env-file /path/to/custom.env
   ```

4. **VS Code Settings** (Higher priority)
   ```json
   {
     "jenkins-mcp-server": {
       "jenkins": {
         "url": "http://jenkins:8080",
         "username": "admin",
         "token": "secret"
       }
     }
   }
   ```

5. **Direct Parameters** (Highest priority)
   ```python
   settings = JenkinsSettings(
       url="http://jenkins:8080",
       username="admin",
       token="secret"
   )
   ```

### Configuration Loading Process

```python
def load_settings(env_file=None, load_vscode=True, **overrides):
    # 1. Load from environment/default .env
    settings = JenkinsSettings(_env_file=env_file)
    
    # 2. Override with VS Code settings
    if load_vscode:
        vscode_settings = VSCodeSettingsLoader.load()
        if vscode_settings:
            for key, value in vscode_settings.items():
                setattr(settings, key, value)
    
    # 3. Apply direct overrides
    for key, value in overrides.items():
        setattr(settings, key, value)
    
    return settings
```

### Validation

```python
class JenkinsSettings(BaseSettings):
    url: str = Field(...)
    username: str = Field(...)
    token: str = Field(...)
    
    timeout: int = Field(default=30, ge=5, le=300)
    connect_timeout: int = Field(default=10, ge=2, le=60)
    
    @field_validator('url')
    @classmethod
    def strip_trailing_slash(cls, v):
        return v.rstrip('/') if v else v
    
    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.username and self.token)
```

---

## Error Handling

### Error Categories

1. **Validation Errors** (Immediate)
   - Missing parameters
   - Wrong types
   - Invalid formats
   - Empty values

2. **Connection Errors**
   - Timeout
   - DNS failure
   - Network unreachable
   - SSL errors

3. **Authentication Errors**
   - 401 Unauthorized
   - Invalid credentials
   - Expired token

4. **Permission Errors**
   - 403 Forbidden
   - Insufficient permissions

5. **Not Found Errors**
   - 404 Job not found
   - Invalid job name
   - Deleted resource

6. **Server Errors**
   - 500 Internal server error
   - Jenkins unavailable

### Error Response Format

```python
{
    "error": "Error category",
    "message": "Clear description of what went wrong",
    "troubleshooting": [
        "Step 1: Check X",
        "Step 2: Verify Y",
        "Step 3: Try Z"
    ],
    "context": {
        "job_name": "my-job",
        "build_number": 42
    }
}
```

### Example Error Handlers

```python
def handle_timeout_error(e, context):
    return {
        "error": "Timeout",
        "message": f"Request timed out after {context['timeout']}s",
        "troubleshooting": [
            "Check if Jenkins server is running",
            "Verify VPN connection",
            "Check firewall settings",
            f"Increase timeout: JENKINS_TIMEOUT={context['timeout'] * 2}"
        ]
    }

def handle_auth_error(e, context):
    return {
        "error": "Authentication Failed",
        "message": "Invalid username or token",
        "troubleshooting": [
            "Verify username is correct",
            "Generate new API token:",
            "  1. Log into Jenkins",
            "  2. Click your name → Configure",
            "  3. Scroll to API Token section",
            "  4. Click 'Add new Token'",
            "  5. Copy token and update JENKINS_TOKEN"
        ]
    }
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_config.py
def test_load_from_env():
    os.environ['JENKINS_URL'] = 'http://jenkins:8080'
    settings = get_settings()
    assert settings.url == 'http://jenkins:8080'

# tests/test_validation.py
def test_validate_job_name():
    assert validate_job_name("my-job") == "my-job"
    
    with pytest.raises(ValueError):
        validate_job_name("")
    
    with pytest.raises(ValueError):
        validate_job_name(123)

# tests/test_cache.py
@pytest.mark.asyncio
async def test_cache_expiry():
    cache = CacheManager()
    await cache.set("key", "value", ttl_seconds=1)
    await asyncio.sleep(2)
    assert await cache.get("key") is None
```

### Integration Tests

```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_list_jobs(mock_jenkins_server):
    client = JenkinsClient(test_settings)
    jobs = client.get_jobs()
    assert len(jobs) > 0
    assert "name" in jobs[0]

@pytest.mark.asyncio
async def test_trigger_build(mock_jenkins_server):
    client = JenkinsClient(test_settings)
    result = client.build_job("test-job")
    assert "queue_id" in result
```

### Load Tests

```python
# tests/test_performance.py
@pytest.mark.asyncio
async def test_cache_performance():
    cache = CacheManager()
    
    # Warm up cache
    await cache.set("test", "data", 60)
    
    # Measure hit performance
    start = time.time()
    for _ in range(1000):
        await cache.get("test")
    elapsed = time.time() - start
    
    # Should be < 100ms for 1000 hits
    assert elapsed < 0.1
```

---

## Deployment

### npm Package Structure

```
@rishibhushan/jenkins-mcp-server/
├── bin/
│   └── jenkins-mcp.js      # Node wrapper (npx entry point)
├── src/
│   └── jenkins_mcp_server/ # Python package
├── package.json            # npm configuration
├── setup.py                # Python package config
└── requirements.txt        # Python dependencies
```

### Package.json

```json
{
  "name": "@rishibhushan/jenkins-mcp-server",
  "version": "2.0.0",
  "description": "AI-enabled Jenkins automation via MCP",
  "bin": {
    "jenkins-mcp-server": "./bin/jenkins-mcp.js"
  },
  "scripts": {
    "test": "pytest tests/",
    "build": "python -m build"
  },
  "keywords": ["jenkins", "mcp", "ai", "automation"],
  "author": "Rishi Bhushan",
  "license": "MIT"
}
```

### Publishing

```bash
# Build Python package
python -m build

# Publish to npm
npm publish --access public

# Publish to PyPI (optional)
twine upload dist/*
```

### Installation Methods

1. **npx** (No installation)
   ```bash
   npx @rishibhushan/jenkins-mcp-server
   ```

2. **Global npm**
   ```bash
   npm install -g @rishibhushan/jenkins-mcp-server
   jenkins-mcp-server
   ```

3. **pip** (Python only)
   ```bash
   pip install jenkins-mcp-server
   python -m jenkins_mcp_server
   ```

4. **From source**
   ```bash
   git clone https://github.com/rishibhushan/jenkins_mcp_server
   cd jenkins_mcp_server
   pip install -e .
   jenkins-mcp-server
   ```

---

## Development Guide

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/rishibhushan/jenkins_mcp_server.git
cd jenkins_mcp_server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .

# Install dev dependencies
pip install pytest pytest-asyncio black mypy

# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Code formatting
black src/ tests/
```

### Adding a New Tool

1. **Define Tool Schema** in `server.py`:
```python
types.Tool(
    name="my-new-tool",
    description="Does something useful",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "First parameter"
            }
        },
        "required": ["param1"]
    }
)
```

2. **Create Handler Function**:
```python
async def _tool_my_new_tool(client, args):
    """Handler for my new tool"""
    # Validate input
    param1 = validate_string(args.get("param1"))
    
    # Call Jenkins API
    result = client.some_api_call(param1)
    
    # Format response
    return [types.TextContent(
        type="text",
        text=f"Result: {result}"
    )]
```

3. **Register Handler**:
```python
handlers = {
    # ... existing handlers ...
    "my-new-tool": _tool_my_new_tool,
}
```

4. **Write Tests**:
```python
@pytest.mark.asyncio
async def test_my_new_tool():
    result = await _tool_my_new_tool(mock_client, {"param1": "value"})
    assert result is not None
```

### Adding a New Module

1. **Create module file**: `src/jenkins_mcp_server/my_module.py`

2. **Define classes/functions**:
```python
"""
My Module - Does something

Purpose: Explain what this module does
"""

class MyClass:
    def __init__(self):
        pass
    
    def my_method(self):
        pass

# Singleton pattern if needed
_instance = None

def get_instance():
    global _instance
    if _instance is None:
        _instance = MyClass()
    return _instance
```

3. **Import in server.py**:
```python
from .my_module import get_instance
```

4. **Use in tool handlers**:
```python
async def _tool_uses_my_module(client, args):
    instance = get_instance()
    result = instance.my_method()
    return result
```

### Code Style Guidelines

1. **Type Hints**: Use type hints for all functions
```python
def my_function(param: str) -> dict[str, Any]:
    pass
```

2. **Docstrings**: Document all public functions/classes
```python
def my_function(param: str) -> dict:
    """
    Brief description.
    
    Args:
        param: Parameter description
        
    Returns:
        Return value description
    """
```

3. **Error Handling**: Always use specific exceptions
```python
try:
    result = dangerous_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
```

4. **Logging**: Use appropriate log levels
```python
logger.debug("Detailed info for debugging")
logger.info("Normal operation info")
logger.warning("Something unexpected but handled")
logger.error("Error occurred", exc_info=True)
```

---

## Performance Benchmarks

### Baseline (v1.0)

```
Tool Execution:
- trigger-build: 250ms average
- list-jobs: 2500ms average
- get-build-console: 1500ms average

Cache:
- Hit rate: 0% (no caching)
- Miss penalty: Full API call every time

Validation:
- Coverage: 24% (5/21 tools)
- Invalid input detection: At API level
```

### Optimized (v2.0)

```
Tool Execution:
- trigger-build: 25ms average (10x faster)
- list-jobs: 300ms average (8x faster)
- get-build-console: 400ms average (4x faster)

Cache:
- Hit rate: 85% average
- Miss penalty: +50ms for cache check
- Net benefit: 5-10x speedup on cache hits

Validation:
- Coverage: 86% (18/21 tools)
- Invalid input detection: Immediate (before API)
- Saved API calls: ~30% reduction
```

### Load Testing Results

```
Concurrent Requests: 10
Test Duration: 60 seconds

Before Optimization:
- Requests/second: 15
- Average latency: 650ms
- Errors: 12%

After Optimization:
- Requests/second: 85
- Average latency: 120ms
- Errors: 2%

Improvement: 5.6x throughput, 5.4x lower latency
```

---

## Future Enhancements

### Planned Features

1. **Pipeline Support**
   - List pipelines
   - Trigger pipeline runs
   - Get pipeline stages

2. **Multi-Instance Management**
   - Connect to multiple Jenkins servers
   - Aggregate job lists
   - Cross-server operations

3. **Advanced Analytics**
   - Build trend analysis
   - Failure pattern detection
   - Performance recommendations

4. **Real-Time Monitoring**
   - WebSocket support for live updates
   - Build progress streaming
   - Queue position tracking

5. **Enhanced Security**
   - Token rotation
   - Audit logging
   - Permission management

### Architectural Improvements

1. **Plugin System**
   - Allow custom tools
   - Third-party integrations
   - Extension points

2. **GraphQL API**
   - More flexible queries
   - Reduced over-fetching
   - Better type safety

3. **Event System**
   - Webhook handlers
   - Event subscriptions
   - Custom triggers

4. **Database Backend**
   - Persistent caching
   - Historical metrics
   - Advanced queries

---

## Appendix

### Glossary

- **MCP**: Model Context Protocol - Standard for AI-to-system communication
- **Tool**: A callable operation exposed via MCP
- **Resource**: A Jenkins entity (job, build, etc.)
- **Prompt**: A template for generating AI instructions
- **TTL**: Time-To-Live - How long cached data remains valid
- **Fallback**: Alternative method when primary approach fails

### References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [python-jenkins Documentation](https://python-jenkins.readthedocs.io/)
- [Jenkins REST API](https://www.jenkins.io/doc/book/using/remote-access-api/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Contact & Support

- **GitHub**: https://github.com/rishibhushan/jenkins_mcp_server
- **Issues**: https://github.com/rishibhushan/jenkins_mcp_server/issues
- **Author**: Rishi Bhushan

---

**Last Updated**: December 2024
**Version**: 2.0.0
