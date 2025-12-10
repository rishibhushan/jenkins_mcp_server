# Jenkins MCP Server - API Reference

Complete reference for all 26 tools available in the Jenkins MCP Server.

## Table of Contents

- [Build Operations](#build-operations)
- [Job Information](#job-information)
- [Build Information](#build-information)
- [Job Management](#job-management)
- [Job Configuration](#job-configuration)
- [System Information](#system-information)
- [Monitoring & Management](#monitoring--management)

---

## Build Operations

### trigger-build

Trigger a Jenkins job build with optional parameters.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job to trigger |
| `parameters` | object | ❌ | Build parameters as key-value pairs |

**Returns:**

```json
{
  "queue_id": 12345,
  "build_number": 42,
  "message": "Build triggered successfully"
}
```

**Example Usage:**

```
"Trigger a build for api-service"
"Start a build for frontend-app with parameter ENV=production"
"Run my-job with parameters: VERSION=1.2.3, BRANCH=main"
```

**Example Response:**

```
✅ Build triggered for 'api-service'

Queue ID: 12345
Build Number: 42 (started)

You can check the build status with:
"Get build info for api-service #42"
```

**Possible Errors:**

- `ValidationError`: Invalid job_name or parameters
- `404 Not Found`: Job doesn't exist
- `403 Forbidden`: Insufficient permissions
- `ConnectionError`: Cannot reach Jenkins server

---

### stop-build

Stop a running Jenkins build.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |
| `build_number` | integer | ✅ | Build number to stop |

**Returns:**

```json
{
  "message": "Successfully stopped build #42 for job 'api-service'"
}
```

**Example Usage:**

```
"Stop build 42 for api-service"
"Cancel the running build #100 of frontend-app"
```

**Example Response:**

```
✅ Successfully stopped build #42 for job 'api-service'.
```

**Possible Errors:**

- `ValidationError`: Invalid job_name or build_number
- `404 Not Found`: Job or build doesn't exist
- `400 Bad Request`: Build is not running

---

### trigger-multiple-builds

**NEW in v2.0!** Trigger builds for multiple jobs at once (batch operation).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_names` | array[string] | ✅ | List of job names (max 20) |
| `parameters` | object | ❌ | Common parameters for all builds |
| `wait_for_start` | boolean | ❌ | Wait for builds to start (default: false) |

**Returns:**

```json
{
  "total": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "job": "api-service",
      "status": "triggered",
      "queue_id": 12345,
      "build_number": 42
    },
    {
      "job": "web-app",
      "status": "triggered",
      "queue_id": 12346,
      "build_number": 103
    },
    {
      "job": "worker-service",
      "status": "triggered",
      "queue_id": 12347,
      "build_number": 25
    }
  ]
}
```

**Example Usage:**

```
"Trigger builds for api-service, web-app, and worker-service"
"Start builds for all microservices with parameter ENV=staging"
"Batch trigger: service1, service2, service3"
```

**Example Response:**

```
✅ Batch Build Trigger Complete

Total Jobs: 3
Successful: 3
Failed: 0

Details:
- api-service: ✅ Triggered (queue_id: 12345, build: #42)
- web-app: ✅ Triggered (queue_id: 12346, build: #103)
- worker-service: ✅ Triggered (queue_id: 12347, build: #25)
```

**Possible Errors:**

- `ValidationError`: Invalid job_names array or exceeds 20 jobs
- `PartialSuccess`: Some jobs triggered, some failed (returns details)

---

## Job Information

### list-jobs

List all Jenkins jobs with optional filtering and caching.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `filter` | string | ❌ | Filter jobs by name (case-insensitive partial match) |
| `use_cache` | boolean | ❌ | Use cached results if available (default: true) |

**Returns:**

```json
{
  "jobs": [
    {
      "name": "api-service",
      "url": "http://jenkins.example.com/job/api-service/",
      "status": "blue"
    },
    {
      "name": "web-app",
      "url": "http://jenkins.example.com/job/web-app/",
      "status": "red"
    }
  ],
  "total": 2,
  "cached": true
}
```

**Status Colors:**

- `blue` - Success
- `red` - Failure
- `yellow` - Unstable
- `grey` - Never built
- `disabled` - Disabled
- `aborted` - Aborted
- `notbuilt` - Not built

**Example Usage:**

```
"List all Jenkins jobs"
"Show me jobs containing 'service'"
"List jobs without using cache"
```

**Example Response:**

```
Jenkins Jobs (42 total):

1. api-service [blue]
2. web-app [red]
3. worker-service [blue]
...

💡 Tip: Results are cached for 30 seconds
```

**Possible Errors:**

- `ConnectionError`: Cannot reach Jenkins server
- `AuthenticationError`: Invalid credentials

---

### get-job-details

Get detailed information about a Jenkins job including recent builds.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |
| `max_recent_builds` | integer | ❌ | Number of recent builds to fetch (0-10, default: 3) |

**Returns:**

```json
{
  "name": "api-service",
  "url": "http://jenkins.example.com/job/api-service/",
  "description": "API service for the platform",
  "buildable": true,
  "lastBuild": {
    "number": 42,
    "url": "http://jenkins.example.com/job/api-service/42/"
  },
  "lastSuccessfulBuild": {
    "number": 42,
    "url": "http://jenkins.example.com/job/api-service/42/"
  },
  "lastFailedBuild": {
    "number": 40,
    "url": "http://jenkins.example.com/job/api-service/40/"
  },
  "recentBuilds": [
    {
      "number": 42,
      "result": "SUCCESS",
      "timestamp": 1703001600000,
      "duration_seconds": 125.4
    },
    {
      "number": 41,
      "result": "SUCCESS",
      "timestamp": 1703001000000,
      "duration_seconds": 132.1
    },
    {
      "number": 40,
      "result": "FAILURE",
      "timestamp": 1703000400000,
      "duration_seconds": 45.2
    }
  ],
  "recentBuildsCount": 3
}
```

**Example Usage:**

```
"Get details for api-service"
"Show me info about web-app with 5 recent builds"
"Get job details for worker-service without build history"
```

**Example Response:**

```
Job details for 'api-service':

📋 Basic Info:
  Name: api-service
  Buildable: Yes
  Description: API service for the platform

🔨 Recent Builds:
  #42: SUCCESS (2m 5s) - 10 minutes ago
  #41: SUCCESS (2m 12s) - 20 minutes ago
  #40: FAILURE (45s) - 30 minutes ago

💡 Tip: Set max_recent_builds=0 to skip build history (83% faster)
```

**Possible Errors:**

- `ValidationError`: Invalid job_name or max_recent_builds
- `404 Not Found`: Job doesn't exist

---

## Build Information

### get-build-info

Get information about a specific build.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |
| `build_number` | integer | ✅ | Build number to get info for |

**Returns:**

```json
{
  "number": 42,
  "result": "SUCCESS",
  "duration": 125400,
  "timestamp": 1703001600000,
  "url": "http://jenkins.example.com/job/api-service/42/",
  "building": false,
  "queueId": 12345,
  "builtOn": "jenkins-node-1",
  "changeSet": {
    "kind": "git",
    "items": [
      {
        "commitId": "abc123",
        "msg": "Fix bug in authentication",
        "author": "John Doe"
      }
    ]
  }
}
```

**Example Usage:**

```
"Get build info for api-service #42"
"Show me details about build 100 of web-app"
```

**Example Response:**

```
Build info for api-service #42:

Status: SUCCESS ✅
Duration: 2m 5s
Started: 2024-12-10 14:30:00
Node: jenkins-node-1

Changes:
  - abc123: Fix bug in authentication (John Doe)

URL: http://jenkins.example.com/job/api-service/42/
```

**Possible Errors:**

- `ValidationError`: Invalid job_name or build_number
- `404 Not Found`: Job or build doesn't exist

---

### get-build-console

Get console output from a build with smart truncation.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |
| `build_number` | integer | ✅ | Build number |
| `max_lines` | integer | ❌ | Maximum lines to return (10-10000, default: 1000) |
| `tail_only` | boolean | ❌ | Return last N lines instead of first N (default: false) |

**Returns:**

```
[Showing first 1000 of 5247 lines - 4247 later lines truncated]

Console output for api-service #42:

```
Started by user John Doe
Running as SYSTEM
Building in workspace /var/jenkins_home/workspace/api-service
...
(console output)
...
```

💡 Tip: Set tail_only=true to see last 1000 lines, or increase max_lines (current: 1000, max: 10000)
```

**Example Usage:**

```
"Show me the console output from build 42"
"Get the last 500 lines of api-service build #42"
"Show first 200 lines from web-app build #100"
```

**Example Response:**

```
[Showing last 500 of 3421 lines - 2921 earlier lines omitted]

Console output for api-service #42:

...
[INFO] BUILD SUCCESS
[INFO] Total time: 2:05 min
[INFO] Finished at: 2024-12-10T14:32:05Z
Finished: SUCCESS

💡 Tip: Use max_lines parameter to see more lines (current: 500, max: 10000)
```

**Possible Errors:**

- `ValidationError`: Invalid parameters
- `404 Not Found`: Job or build doesn't exist
- `TimeoutError`: Console output too large and timed out

---

### get-last-build-number

Get the last build number for a job.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |

**Returns:**

```json
{
  "job_name": "api-service",
  "last_build_number": 42
}
```

**Example Usage:**

```
"What's the last build number for api-service?"
"Get the latest build number of web-app"
```

**Example Response:**

```
Last build number for 'api-service': 42
```

**Possible Errors:**

- `ValidationError`: Invalid job_name
- `404 Not Found`: Job doesn't exist or has no builds

---

### get-last-build-timestamp

Get the timestamp of the last build.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |

**Returns:**

```json
{
  "job_name": "api-service",
  "last_build_timestamp": 1703001600000,
  "last_build_timestamp_human": "2024-12-10 14:30:00"
}
```

**Example Usage:**

```
"When was the last build of api-service?"
"Get the timestamp of web-app's latest build"
```

**Example Response:**

```
Last build timestamp for 'api-service': 1703001600000
(2024-12-10 14:30:00 UTC)
```

**Possible Errors:**

- `ValidationError`: Invalid job_name
- `404 Not Found`: Job doesn't exist or has no builds

---

## Job Management

### create-job

Create a new Jenkins job with XML configuration.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name for the new job |
| `config_xml` | string | ✅ | Complete Jenkins job XML configuration |

**Returns:**

```json
{
  "message": "Successfully created job 'new-job'",
  "url": "http://jenkins.example.com/job/new-job/"
}
```

**Example Usage:**

```
"Create a job named test-job with this XML configuration: <project>...</project>"
```

**Example Response:**

```
✅ Successfully created job 'test-job'

URL: http://jenkins.example.com/job/test-job/
```

**Possible Errors:**

- `ValidationError`: Invalid job_name or config_xml
- `400 Bad Request`: Invalid XML configuration
- `409 Conflict`: Job already exists

---

### create-job-from-copy

Create a new job by copying an existing one.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `new_job_name` | string | ✅ | Name for the new job |
| `source_job_name` | string | ✅ | Name of the job to copy from |

**Returns:**

```json
{
  "message": "Successfully created job 'new-job' from 'source-job'",
  "url": "http://jenkins.example.com/job/new-job/"
}
```

**Example Usage:**

```
"Copy api-service to create api-service-staging"
"Create new-job by copying existing-job"
```

**Example Response:**

```
✅ Successfully created job 'api-service-staging' from 'api-service'

The new job has been created with the same configuration.
You may want to update parameters or triggers.

URL: http://jenkins.example.com/job/api-service-staging/
```

**Possible Errors:**

- `ValidationError`: Invalid job names
- `404 Not Found`: Source job doesn't exist
- `409 Conflict`: New job name already exists

---

### create-job-from-data

Create a job from structured data (simplified XML generation).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name for the new job |
| `config_data` | object | ✅ | Job configuration as dictionary |
| `root_tag` | string | ❌ | Root XML tag (default: "project") |

**Returns:**

```json
{
  "message": "Successfully created job 'new-job'",
  "url": "http://jenkins.example.com/job/new-job/"
}
```

**Example Usage:**

```
"Create a simple job named test-job with description 'Test Job'"
```

**Example Response:**

```
✅ Successfully created job 'test-job'

URL: http://jenkins.example.com/job/test-job/

⚠️  Note: For complex configurations, use create-job with full XML
   or create-job-from-copy instead.
```

**Possible Errors:**

- `ValidationError`: Invalid job_name or config_data
- `400 Bad Request`: Invalid configuration structure

---

### delete-job

Delete an existing Jenkins job.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the job to delete |

**Returns:**

```json
{
  "message": "Successfully deleted job 'old-job'"
}
```

**Example Usage:**

```
"Delete the job named old-job"
"Remove test-job from Jenkins"
```

**Example Response:**

```
⚠️  Successfully deleted job 'old-job'

This action cannot be undone. The job and all its build history have been removed.
```

**Possible Errors:**

- `ValidationError`: Invalid job_name
- `404 Not Found`: Job doesn't exist

---

### enable-job

Enable a disabled Jenkins job.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the job to enable |

**Returns:**

```json
{
  "message": "Successfully enabled job 'my-job'"
}
```

**Example Usage:**

```
"Enable the job api-service"
"Re-enable disabled-job"
```

**Example Response:**

```
✅ Successfully enabled job 'api-service'

The job can now be triggered manually or by triggers.
```

**Possible Errors:**

- `ValidationError`: Invalid job_name
- `404 Not Found`: Job doesn't exist

---

### disable-job

Disable a Jenkins job.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the job to disable |

**Returns:**

```json
{
  "message": "Successfully disabled job 'my-job'"
}
```

**Example Usage:**

```
"Disable the job api-service"
"Stop running test-job"
```

**Example Response:**

```
✅ Successfully disabled job 'api-service'

The job will not be triggered by automatic triggers until re-enabled.
Running builds will complete normally.
```

**Possible Errors:**

- `ValidationError`: Invalid job_name
- `404 Not Found`: Job doesn't exist

---

### rename-job

Rename an existing Jenkins job.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Current name of the job |
| `new_name` | string | ✅ | New name for the job |

**Returns:**

```json
{
  "message": "Successfully renamed job: old-name -> new-name",
  "new_url": "http://jenkins.example.com/job/new-name/"
}
```

**Example Usage:**

```
"Rename api-service to api-service-v2"
"Change the name of old-job to new-job"
```

**Example Response:**

```
✅ Successfully renamed job: api-service -> api-service-v2

New URL: http://jenkins.example.com/job/api-service-v2/

⚠️  Note: Update any references to the old job name in:
   - Build scripts
   - Pipeline dependencies
   - External integrations
```

**Possible Errors:**

- `ValidationError`: Invalid job names
- `404 Not Found`: Source job doesn't exist
- `409 Conflict`: New name already exists

---

## Job Configuration

### get-job-config

Fetch job XML configuration.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |

**Returns:**

```xml
<?xml version='1.1' encoding='UTF-8'?>
<project>
  <description>API service for the platform</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <scm class="hudson.plugins.git.GitSCM">
    <configVersion>2</configVersion>
    <userRemoteConfigs>
      <hudson.plugins.git.UserRemoteConfig>
        <url>https://github.com/example/api-service.git</url>
      </hudson.plugins.git.UserRemoteConfig>
    </userRemoteConfigs>
    <branches>
      <hudson.plugins.git.BranchSpec>
        <name>*/main</name>
      </hudson.plugins.git.BranchSpec>
    </branches>
  </scm>
  <builders>
    <hudson.tasks.Shell>
      <command>npm install &amp;&amp; npm test</command>
    </hudson.tasks.Shell>
  </builders>
</project>
```

**Example Usage:**

```
"Get the configuration for api-service"
"Show me the XML config of web-app"
```

**Example Response:**

```
Job configuration for 'api-service':

```xml
<?xml version='1.1' encoding='UTF-8'?>
<project>
  ...
</project>
```

💡 Tip: Use this to backup or modify job configurations
```

**Possible Errors:**

- `ValidationError`: Invalid job_name
- `404 Not Found`: Job doesn't exist

---

### update-job-config

Update job XML configuration.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Name of the Jenkins job |
| `config_xml` | string | ✅ | New complete XML configuration |

**Returns:**

```json
{
  "message": "Successfully updated config for job 'my-job'"
}
```

**Example Usage:**

```
"Update api-service configuration with this XML: <project>...</project>"
```

**Example Response:**

```
✅ Successfully updated config for job 'api-service'

⚠️  Important:
   - Changes take effect immediately
   - Running builds use the old configuration
   - Test the job after updating
```

**Possible Errors:**

- `ValidationError`: Invalid job_name or config_xml
- `404 Not Found`: Job doesn't exist
- `400 Bad Request`: Invalid XML configuration

---

## System Information

### get-queue-info

Get Jenkins build queue information.

**Parameters:**

None.

**Returns:**

```json
{
  "items": [
    {
      "id": 12345,
      "task": {
        "name": "api-service",
        "url": "http://jenkins.example.com/job/api-service/"
      },
      "why": "Waiting for next available executor",
      "blocked": false,
      "buildable": true,
      "stuck": false,
      "inQueueSince": 1703001600000
    }
  ],
  "total": 1
}
```

**Example Usage:**

```
"What's in the build queue?"
"Show me queued builds"
"Check Jenkins queue"
```

**Example Response:**

```
Jenkins Build Queue (1 item):

1. api-service
   Reason: Waiting for next available executor
   In queue since: 2024-12-10 14:30:00
   Blocked: No
   Stuck: No
```

**Possible Errors:**

- `ConnectionError`: Cannot reach Jenkins server

---

### list-nodes

List all Jenkins nodes (agents).

**Parameters:**

None.

**Returns:**

```json
{
  "nodes": [
    {
      "displayName": "master",
      "offline": false,
      "numExecutors": 2
    },
    {
      "displayName": "jenkins-node-1",
      "offline": false,
      "numExecutors": 4
    },
    {
      "displayName": "jenkins-node-2",
      "offline": true,
      "numExecutors": 4
    }
  ],
  "total": 3
}
```

**Example Usage:**

```
"List all Jenkins nodes"
"Show me available build agents"
"What nodes are online?"
```

**Example Response:**

```
Jenkins Nodes (3 total):

1. master
   Status: Online ✅
   Executors: 2

2. jenkins-node-1
   Status: Online ✅
   Executors: 4

3. jenkins-node-2
   Status: Offline ❌
   Executors: 4
```

**Possible Errors:**

- `ConnectionError`: Cannot reach Jenkins server

---

### get-node-info

Get information about a specific Jenkins node.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `node_name` | string | ✅ | Name of the Jenkins node |

**Returns:**

```json
{
  "displayName": "jenkins-node-1",
  "offline": false,
  "offlineCauseReason": null,
  "numExecutors": 4,
  "busyExecutors": 2,
  "idleExecutors": 2,
  "monitorData": {
    "hudson.node_monitors.ArchitectureMonitor": "Linux (amd64)",
    "hudson.node_monitors.ResponseTimeMonitor": {
      "average": 50
    }
  }
}
```

**Example Usage:**

```
"Get info about jenkins-node-1"
"Show me details for node master"
```

**Example Response:**

```
Node information for 'jenkins-node-1':

Status: Online ✅
Architecture: Linux (amd64)
Response Time: 50ms

Executors:
  Total: 4
  Busy: 2
  Idle: 2

The node is healthy and processing builds.
```

**Possible Errors:**

- `ValidationError`: Invalid node_name
- `404 Not Found`: Node doesn't exist

---

## Monitoring & Management

### health-check

**NEW in v2.0!** Run diagnostics on Jenkins connection.

**Parameters:**

None.

**Returns:**

```json
{
  "overall_status": "healthy",
  "checks": {
    "reachability": {
      "status": "pass",
      "message": "Server is reachable",
      "response_time_ms": 45
    },
    "authentication": {
      "status": "pass",
      "message": "Authentication successful"
    },
    "api_responsiveness": {
      "status": "pass",
      "message": "API responding normally",
      "response_time_ms": 120
    }
  },
  "jenkins_version": "2.401.3",
  "timestamp": "2024-12-10T14:30:00Z"
}
```

**Example Usage:**

```
"Run a health check"
"Check if Jenkins is healthy"
"Test the connection to Jenkins"
```

**Example Response:**

```
🏥 Jenkins Health Check

Overall Status: HEALTHY ✅

Checks:
  ✅ Reachability: Pass (45ms)
  ✅ Authentication: Pass
  ✅ API Responsiveness: Pass (120ms)

Jenkins Version: 2.401.3
Timestamp: 2024-12-10 14:30:00 UTC

All systems operational!
```

**Possible Errors:**

All errors are reported as failed health checks with detailed troubleshooting steps.

---

### get-cache-stats

**NEW in v2.0!** Get cache statistics and information.

**Parameters:**

None.

**Returns:**

```json
{
  "size": 5,
  "hits": 85,
  "misses": 15,
  "evictions": 3,
  "total_requests": 100,
  "hit_rate_percent": 85.0,
  "entries": [
    {
      "key": "jobs_list:all",
      "age_seconds": 12.5,
      "ttl_seconds": 30,
      "expires_in_seconds": 17.5,
      "is_expired": false,
      "cached_at": "2024-12-10T14:29:47Z"
    }
  ]
}
```

**Example Usage:**

```
"Show cache statistics"
"What's the cache hit rate?"
"Get cache info"
```

**Example Response:**

```
📊 Cache Statistics

═══════════════════════════════════════
OVERVIEW
═══════════════════════════════════════
Cache Size:      5 entries
Total Requests:  100
Cache Hits:      85
Cache Misses:    15
Hit Rate:        85.0%
Evictions:       3

═══════════════════════════════════════
CACHED ENTRIES
═══════════════════════════════════════

jobs_list:all
  Status: ✅ Valid
  Age: 12.5s
  TTL: 30s
  Expires in: 17.5s
```

**Possible Errors:**

None (always returns current state).

---

### clear-cache

**NEW in v2.0!** Clear all cached data.

**Parameters:**

None.

**Returns:**

```json
{
  "message": "Cache cleared: 5 entries removed",
  "entries_cleared": 5
}
```

**Example Usage:**

```
"Clear the cache"
"Invalidate all cached data"
"Reset cache"
```

**Example Response:**

```
✅ Cache cleared: 5 entries removed

The next queries will fetch fresh data from Jenkins.
```

**Possible Errors:**

None (always succeeds).

---

### get-metrics

**NEW in v2.0!** Get usage metrics and performance statistics.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tool_name` | string | ❌ | Specific tool name (returns all if not specified) |

**Returns:**

```json
{
  "summary": {
    "uptime_seconds": 3600,
    "uptime_human": "1:00:00",
    "total_executions": 150,
    "successful_executions": 145,
    "failed_executions": 5,
    "success_rate_percent": 96.67,
    "avg_execution_time_ms": 125.5,
    "unique_tools_used": 12,
    "most_used_tool": "list-jobs",
    "slowest_tool": "get-build-console"
  },
  "tool_stats": {
    "list-jobs": {
      "total_calls": 50,
      "successful_calls": 50,
      "failed_calls": 0,
      "success_rate_percent": 100.0,
      "avg_time_ms": 45.2,
      "min_time_ms": 20.5,
      "max_time_ms": 2500.0,
      "total_time_ms": 2260.0
    }
  }
}
```

**Example Usage:**

```
"Show me the metrics"
"Get performance statistics"
"What are the metrics for trigger-build?"
"Show me failed operations"
```

**Example Response:**

```
📊 Jenkins MCP Server Metrics

═══════════════════════════════════════
SUMMARY
═══════════════════════════════════════
Uptime:              1:00:00
Total Executions:    150
Successful:          145
Failed:              5
Success Rate:        96.67%
Avg Execution Time:  125.5ms
Unique Tools Used:   12
Most Used Tool:      list-jobs
Slowest Tool:        get-build-console

═══════════════════════════════════════
PER-TOOL STATISTICS
═══════════════════════════════════════
list-jobs:
  Calls: 50
  Success Rate: 100%
  Avg Time: 45.2ms
  Min: 20.5ms, Max: 2500ms
```

**Possible Errors:**

None (always returns current metrics).

---

### configure-webhook

**NEW in v2.0!** Configure webhook notifications for Jenkins events.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_name` | string | ✅ | Job to configure webhook for |
| `webhook_url` | string | ✅ | URL to receive webhook notifications |
| `events` | array[string] | ✅ | Events to trigger webhook |

**Supported Events:**

- `build_started` - When a build starts
- `build_completed` - When a build completes (any result)
- `build_failed` - When a build fails
- `build_success` - When a build succeeds

**Returns:**

```json
{
  "message": "Webhook configured for 'api-service'",
  "webhook_url": "https://hooks.example.com/jenkins",
  "events": ["build_started", "build_completed"]
}
```

**Example Usage:**

```
"Configure a webhook for api-service to https://hooks.example.com/jenkins"
"Set up webhook notifications for build failures on web-app"
```

**Example Response:**

```
✅ Webhook configured for 'api-service'

URL: https://hooks.example.com/jenkins
Events: build_started, build_completed

⚠️  Note: Requires Generic Webhook Trigger plugin in Jenkins

The webhook will be triggered when these events occur.
```

**Possible Errors:**

- `ValidationError`: Invalid parameters or events
- `404 Not Found`: Job doesn't exist
- `PluginRequired`: Generic Webhook Trigger plugin not installed

---

## Error Responses

All tools may return errors in this format:

```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "troubleshooting": [
    "Step 1: Check X",
    "Step 2: Verify Y"
  ],
  "context": {
    "tool": "tool-name",
    "parameters": {...}
  }
}
```

### Common Error Types:

- `ValidationError` - Invalid parameters
- `ConnectionError` - Cannot reach Jenkins
- `TimeoutError` - Request timed out
- `AuthenticationError` - Invalid credentials (401)
- `PermissionError` - Insufficient permissions (403)
- `NotFoundError` - Resource not found (404)
- `ServerError` - Jenkins internal error (500)

---

## Rate Limits

There are no built-in rate limits in the MCP server. However:

- **Caching** reduces API calls automatically
- **Batch operations** are limited to 20 jobs per request
- **Jenkins** may have its own rate limiting

---

## Best Practices

### 1. Use Caching

For frequently accessed data like job lists, leverage caching:

```
"List all jobs"  # First call - fetches from Jenkins
"List all jobs"  # Second call - uses cache (5-10x faster!)
```

### 2. Optimize Build Queries

For job details, adjust `max_recent_builds` based on your needs:

```
"Get job details with 0 recent builds"    # Fastest (83% faster)
"Get job details"                          # Default (3 builds)
"Get job details with 10 recent builds"   # Detailed (slower)
```

### 3. Use Tail Mode for Logs

When debugging, use tail mode to see recent output:

```
"Show me the last 100 lines of the console"  # Faster, more relevant
```

### 4. Batch Operations

Trigger multiple builds at once instead of one by one:

```
"Trigger builds for service1, service2, service3"  # Batch (faster)
```

### 5. Monitor Performance

Use metrics to identify bottlenecks:

```
"Show me the metrics"
"What are the slowest tools?"
```

---

## Version History

### v2.0.0 (2024-12)
- Added 6 new tools (26 total)
- Enhanced existing tools with caching
- Improved console output handling
- Added metrics and monitoring

### v1.0.0 (2024-11)
- Initial release with 20 tools
- Basic Jenkins operations
- MCP protocol support

---

**Last Updated**: December 2024  
**API Version**: 2.0.0
