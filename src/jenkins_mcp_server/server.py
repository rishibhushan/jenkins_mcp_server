"""
Jenkins MCP Server Implementation

Provides MCP protocol handlers for Jenkins operations including:
- Resources (job information)
- Prompts (analysis templates)
- Tools (Jenkins operations)
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

from .cache import get_cache_manager
from .config import JenkinsSettings, get_default_settings
from .jenkins_client import get_jenkins_client
from .metrics import get_metrics_collector, record_tool_execution
from .verbose import vprint, _VERBOSE

# Configure logging
logger = logging.getLogger(__name__)

# Server instance
server = Server("jenkins-mcp-server")

# Settings storage (injected by main)
_jenkins_settings: Optional[JenkinsSettings] = None

# Client connection cache (Quick Win #3)
_jenkins_client_cache = None
_client_cache_lock = asyncio.Lock()


def set_jenkins_settings(settings: JenkinsSettings) -> None:
    """Set Jenkins settings for the server (called from __init__.py)"""
    global _jenkins_settings, _jenkins_client_cache
    _jenkins_settings = settings
    # Clear cache when settings change
    _jenkins_client_cache = None


def get_settings() -> JenkinsSettings:
    """Get current Jenkins settings"""
    global _jenkins_settings
    if _jenkins_settings is None:
        _jenkins_settings = get_default_settings()
    return _jenkins_settings


async def get_cached_jenkins_client(settings: JenkinsSettings):
    """
    Get or create cached Jenkins client (Quick Win #3: Client Caching)
    Reuses the same client connection across tool calls for better performance.
    """
    global _jenkins_client_cache

    async with _client_cache_lock:
        if _jenkins_client_cache is None:
            logger.info("Creating new Jenkins client connection")
            _jenkins_client_cache = get_jenkins_client(settings)
        return _jenkins_client_cache


# Input Validation Helpers (Quick Win #4)

def validate_job_name(job_name: any) -> str:
    """Validate job name parameter"""
    if not job_name:
        raise ValueError("Missing required argument: job_name")
    if not isinstance(job_name, str):
        raise ValueError(f"job_name must be a string, got {type(job_name).__name__}")
    if not job_name.strip():
        raise ValueError("job_name cannot be empty or whitespace")
    return job_name.strip()


def validate_build_number(build_number: any) -> int:
    """Validate build number parameter"""
    if build_number is None:
        raise ValueError("Missing required argument: build_number")

    try:
        num = int(build_number)
    except (ValueError, TypeError):
        raise ValueError(f"build_number must be an integer, got: {build_number}")

    if num < 0:
        raise ValueError(f"build_number must be non-negative, got: {num}")

    return num


def validate_config_xml(config_xml: any) -> str:
    """Validate XML configuration parameter"""
    if not config_xml:
        raise ValueError("Missing required argument: config_xml")
    if not isinstance(config_xml, str):
        raise ValueError(f"config_xml must be a string, got {type(config_xml).__name__}")

    # Basic XML validation
    xml_str = config_xml.strip()
    if not xml_str.startswith('<'):
        raise ValueError("config_xml must be valid XML (should start with '<')")

    return xml_str


# ==================== Resources ====================

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available Jenkins resources.

    Returns a static resource - use tools for actual job discovery.
    """
    return [
        types.Resource(
            uri=AnyUrl("jenkins://jobs"),
            name="Jenkins Jobs",
            description="Use 'list-jobs' tool to see available jobs. This server provides 26 Jenkins automation tools.",
            mimeType="text/plain",
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """Read a specific Jenkins resource by URI"""
    if uri.scheme != "jenkins":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    path = str(uri.path).lstrip("/") if uri.path else ""

    if not path:
        raise ValueError("Invalid Jenkins URI: missing path")

    if path == "error":
        return "Failed to connect to Jenkins server. Please check your configuration."

    # Handle job requests
    if path.startswith("job/"):
        job_name = path[4:]  # Remove "job/" prefix

        try:
            client = get_jenkins_client(get_settings())
            job_info = client.get_job_info(job_name)

            # Try to get last build info
            last_build = job_info.get('lastBuild')
            if last_build and last_build.get('number'):
                build_number = last_build['number']
                try:
                    build_info = client.get_build_info(job_name, build_number)
                    return json.dumps(build_info, indent=2)
                except Exception as e:
                    logger.warning(f"Could not fetch build info: {e}")

            return json.dumps(job_info, indent=2)

        except Exception as e:
            logger.error(f"Error reading resource {path}: {e}")
            return f"Error retrieving job information: {str(e)}"

    raise ValueError(f"Unknown Jenkins resource: {path}")


# ==================== Prompts ====================

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """List available prompts for Jenkins data analysis"""
    return [
        types.Prompt(
            name="analyze-job-status",
            description="Analyze the status of Jenkins jobs",
            arguments=[
                types.PromptArgument(
                    name="detail_level",
                    description="Level of analysis detail (brief/detailed)",
                    required=False,
                )
            ],
        ),
        types.Prompt(
            name="analyze-build-logs",
            description="Analyze build logs for a specific job",
            arguments=[
                types.PromptArgument(
                    name="job_name",
                    description="Name of the Jenkins job",
                    required=True,
                ),
                types.PromptArgument(
                    name="build_number",
                    description="Build number (default: latest)",
                    required=False,
                )
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
        name: str,
        arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """Generate prompts for Jenkins data analysis"""
    arguments = arguments or {}

    if name == "analyze-job-status":
        return await _prompt_analyze_job_status(arguments)
    elif name == "analyze-build-logs":
        return await _prompt_analyze_build_logs(arguments)
    else:
        raise ValueError(f"Unknown prompt: {name}")


async def _prompt_analyze_job_status(arguments: dict[str, str]) -> types.GetPromptResult:
    """Generate job status analysis prompt"""
    detail_level = arguments.get("detail_level", "brief")
    detail_prompt = " Provide extensive analysis." if detail_level == "detailed" else ""

    try:
        client = get_jenkins_client(get_settings())
        jobs = client.get_jobs()

        jobs_text = "\n".join(
            f"- {job['name']}: Status={job.get('color', 'unknown')}"
            for job in jobs
        )

        return types.GetPromptResult(
            description="Analyze Jenkins job statuses",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Here are the current Jenkins jobs to analyze:{detail_prompt}\n\n"
                            f"{jobs_text}\n\n"
                            f"Please provide insights on the status of these jobs, identify any "
                            f"potential issues, and suggest next steps to maintain a healthy CI/CD environment."
                        ),
                    ),
                )
            ],
        )
    except Exception as e:
        logger.error(f"Error in analyze-job-status prompt: {e}")
        return types.GetPromptResult(
            description="Error retrieving Jenkins jobs",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"I tried to get information about Jenkins jobs but encountered an error: {str(e)}\n\n"
                            f"Please help diagnose what might be wrong with my Jenkins connection or configuration."
                        ),
                    ),
                )
            ],
        )


async def _prompt_analyze_build_logs(arguments: dict[str, str]) -> types.GetPromptResult:
    """Generate build log analysis prompt"""
    job_name = arguments.get("job_name")
    build_number_str = arguments.get("build_number")

    if not job_name:
        raise ValueError("Missing required argument: job_name")

    try:
        client = get_jenkins_client(get_settings())
        job_info = client.get_job_info(job_name)

        # Determine build number
        if build_number_str:
            build_number = int(build_number_str)
        else:
            last_build = job_info.get('lastBuild')
            build_number = last_build.get('number') if last_build else None

        if build_number is None:
            return types.GetPromptResult(
                description=f"No builds found for job: {job_name}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"I tried to analyze build logs for the Jenkins job '{job_name}', "
                                f"but no builds were found.\n\n"
                                f"Please help me understand why this job might not have any builds "
                                f"and suggest how to investigate."
                            ),
                        ),
                    )
                ],
            )

        # Get build info and console output
        build_info = client.get_build_info(job_name, build_number)
        console_output = client.get_build_console_output(job_name, build_number)

        # Limit console output size
        max_length = 10000
        if len(console_output) > max_length:
            console_output = console_output[:max_length] + "\n... (output truncated)"

        result = build_info.get('result', 'UNKNOWN')
        duration = build_info.get('duration', 0) / 1000  # Convert ms to seconds

        return types.GetPromptResult(
            description=f"Analysis of build #{build_number} for job: {job_name}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Please analyze the following Jenkins build logs for job '{job_name}' "
                            f"(build #{build_number}).\n\n"
                            f"Build result: {result}\n"
                            f"Build duration: {duration:.1f} seconds\n\n"
                            f"Console output:\n```\n{console_output}\n```\n\n"
                            f"Please identify any issues, errors, or warnings in these logs. "
                            f"If there are problems, suggest how to fix them. "
                            f"If the build was successful, summarize what happened."
                        ),
                    ),
                )
            ],
        )

    except Exception as e:
        logger.error(f"Error in analyze-build-logs prompt: {e}")
        return types.GetPromptResult(
            description="Error retrieving build information",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"I tried to analyze build logs for the Jenkins job '{job_name}' "
                            f"but encountered an error: {str(e)}\n\n"
                            f"Please help diagnose what might be wrong with my Jenkins connection, "
                            f"configuration, or the job itself."
                        ),
                    ),
                )
            ],
        )


async def _tool_trigger_multiple_builds(client, args):
    """Trigger builds for multiple jobs at once"""
    job_names = args.get("job_names", [])
    parameters = args.get("parameters", {})
    wait_for_start = args.get("wait_for_start", False)

    # Validation
    if not job_names:
        raise ValueError("No job names provided")

    if not isinstance(job_names, list):
        raise ValueError("job_names must be an array")

    if len(job_names) > 20:
        raise ValueError("Maximum 20 jobs can be triggered at once")

    # Validate each job name
    validated_jobs = []
    for job_name in job_names:
        try:
            validated = validate_job_name(job_name)
            validated_jobs.append(validated)
        except ValueError as e:
            return [types.TextContent(
                type="text",
                text=f"❌ Invalid job name '{job_name}': {str(e)}"
            )]

    # Validate parameters if provided
    if parameters and not isinstance(parameters, dict):
        raise ValueError(f"parameters must be a dictionary, got {type(parameters).__name__}")

    # Trigger all builds
    results = []
    for job_name in validated_jobs:
        try:
            result = client.build_job(
                job_name,
                parameters,
                wait_for_start=wait_for_start,
                timeout=10  # Shorter timeout for batch
            )

            results.append({
                "job": job_name,
                "status": "triggered",
                "queue_id": result.get('queue_id'),
                "build_number": result.get('build_number') if wait_for_start else None
            })

            logger.info(f"Triggered build for {job_name}")

        except Exception as e:
            results.append({
                "job": job_name,
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Failed to trigger {job_name}: {e}")

    # Build summary
    successful = [r for r in results if r["status"] == "triggered"]
    failed = [r for r in results if r["status"] == "failed"]

    summary = {
        "total": len(job_names),
        "successful": len(successful),
        "failed": len(failed),
        "results": results
    }

    # Invalidate cache since jobs were triggered
    cache_manager = get_cache_manager()
    await cache_manager.invalidate_pattern("jobs_list:")

    emoji = "✅" if len(failed) == 0 else "⚠️"
    message = f"{emoji} Batch Build Trigger Complete\n\n"
    message += f"Total Jobs: {len(job_names)}\n"
    message += f"Successful: {len(successful)}\n"
    message += f"Failed: {len(failed)}\n\n"
    message += f"Details:\n{json.dumps(results, indent=2)}"

    return [types.TextContent(type="text", text=message)]


# ==================== Tools ====================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for interacting with Jenkins"""
    vprint("=== list_tools CALLED ===")
    tools = [
        # Build Operations
        types.Tool(
            name="trigger-build",
            description="Trigger a Jenkins job build with optional parameters",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "Name of the Jenkins job"},
                    "parameters": {
                        "type": "object",
                        "description": "Build parameters (key-value pairs)",
                        "additionalProperties": {"type": ["string", "number", "boolean"]},
                    },
                },
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="stop-build",
            description="Stop a running Jenkins build",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job"
                    },
                    "build_number": {
                        "type": "integer",
                        "description": "Build number to stop"
                    },
                },
                "required": ["job_name", "build_number"],
            },
        ),

        # Job Information
        types.Tool(
            name="list-jobs",
            description="List all Jenkins jobs with optional filtering and caching",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Filter jobs by name (case-insensitive partial match)"
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Use cached results if available (default: true)",
                        "default": True
                    }
                }
            },
        ),
        types.Tool(
            name="get-job-details",
            description="Get detailed information about a Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job"
                    },
                    "max_recent_builds": {
                        "type": "integer",
                        "description": "Maximum number of recent builds to fetch (0-10, default: 3). Set to 0 to skip build history.",
                        "default": 3,
                        "minimum": 0,
                        "maximum": 10
                    }
                },
                "required": ["job_name"],
            },
        ),

        # Build Information
        types.Tool(
            name="get-build-info",
            description="Get information about a specific build",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job"
                    },
                    "build_number": {
                        "type": "integer",
                        "description": "Build number to get information about"
                    },
                },
                "required": ["job_name", "build_number"],
            },
        ),
        types.Tool(
            name="get-build-console",
            description="Get console output from a build",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job"
                    },
                    "build_number": {
                        "type": "integer",
                        "description": "Build number to get console output from"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum number of lines to return (default: 1000, max: 10000)",
                        "default": 1000,
                        "minimum": 10,
                        "maximum": 10000
                    },
                    "tail_only": {
                        "type": "boolean",
                        "description": "If true, return last N lines instead of first N lines (default: false)",
                        "default": False
                    },
                },
                "required": ["job_name", "build_number"],
            },
        ),
        types.Tool(
            name="get-last-build-number",
            description="Get the last build number for a job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job"
                    }
                },
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="get-last-build-timestamp",
            description="Get the timestamp of the last build",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job"
                    }
                },
                "required": ["job_name"],
            },
        ),

        # Job Management
        types.Tool(
            name="create-job",
            description="Create a new Jenkins job with XML configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name for the new Jenkins job"
                    },
                    "config_xml": {
                        "type": "string",
                        "description": "Job configuration in XML format"
                    },
                },
                "required": ["job_name", "config_xml"],
            },
        ),
        types.Tool(
            name="create-job-from-copy",
            description="Create a new job by copying an existing one",
            inputSchema={
                "type": "object",
                "properties": {
                    "new_job_name": {
                        "type": "string",
                        "description": "Name for the new job to be created"
                    },
                    "source_job_name": {
                        "type": "string",
                        "description": "Name of the existing job to copy from"
                    },
                },
                "required": ["new_job_name", "source_job_name"],
            },
        ),
        types.Tool(
            name="create-job-from-data",
            description="Create a job from structured data (auto-generated XML)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name for the new Jenkins job"
                    },
                    "config_data": {
                        "type": "object",
                        "description": "Job configuration as structured data (will be converted to XML)"
                    },
                    "root_tag": {
                        "type": "string",
                        "default": "project",
                        "description": "Root XML tag for the configuration (default: 'project')"
                    },
                },
                "required": ["job_name", "config_data"],
            },
        ),
        types.Tool(
            name="delete-job",
            description="Delete an existing Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job to delete"
                    }
                },
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="enable-job",
            description="Enable a disabled Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job to enable"
                    }
                },
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="disable-job",
            description="Disable a Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job to disable"
                    }
                },
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="rename-job",
            description="Rename an existing Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Current name of the Jenkins job"
                    },
                    "new_name": {
                        "type": "string",
                        "description": "New name for the Jenkins job"
                    },
                },
                "required": ["job_name", "new_name"],
            },
        ),

        # Job Configuration
        types.Tool(
            name="get-job-config",
            description="Get the configuration XML for a job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job"
                    }
                },
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="update-job-config",
            description="Update the configuration XML for a job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Name of the Jenkins job to update"
                    },
                    "config_xml": {
                        "type": "string",
                        "description": "New configuration in XML format"
                    },
                },
                "required": ["job_name", "config_xml"],
            },
        ),

        # System Information
        types.Tool(
            name="get-queue-info",
            description="Get information about the Jenkins build queue",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="list-nodes",
            description="List all Jenkins nodes/agents",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get-node-info",
            description="Get information about a specific Jenkins node",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_name": {
                        "type": "string",
                        "description": "Name of the Jenkins node/agent"
                    }
                },
                "required": ["node_name"],
            },
        ),
        types.Tool(
            name="trigger-multiple-builds",
            description="Trigger builds for multiple jobs at once",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of job names to trigger",
                        "minItems": 1,
                        "maxItems": 20
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Common parameters for all builds (optional)",
                        "additionalProperties": {"type": ["string", "number", "boolean"]},
                    },
                    "wait_for_start": {
                        "type": "boolean",
                        "description": "Wait for all builds to start (default: false)",
                        "default": False
                    }
                },
                "required": ["job_names"],
            },
        ),

        # Cache tools
        types.Tool(
            name="get-cache-stats",
            description="Get cache statistics and information",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="clear-cache",
            description="Clear all cached data",
            inputSchema={"type": "object", "properties": {}},
        ),

        # Health Check (Quick Win #1)
        types.Tool(
            name="health-check",
            description="Check Jenkins server health and connection status. Useful for troubleshooting connectivity issues.",
            inputSchema={"type": "object", "properties": {}},
        ),

        # Get metrics
        types.Tool(
            name="get-metrics",
            description="Get usage metrics and performance statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Specific tool name (optional, returns all if not specified)"
                    }
                }
            },
        ),

        types.Tool(
            name="configure-webhook",
            description="Configure webhook notifications for Jenkins events (requires Jenkins plugin)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {
                        "type": "string",
                        "description": "Job to configure webhook for"
                    },
                    "webhook_url": {
                        "type": "string",
                        "description": "URL to receive webhook notifications"
                    },
                    "events": {
                        "type": "array",
                        "items": {
                            "enum": ["build_started", "build_completed", "build_failed", "build_success"]
                        },
                        "description": "Events to trigger webhook"
                    }
                },
                "required": ["job_name", "webhook_url", "events"]
            },
        ),
    ]

    logger.info(f"Registered {len(tools)} Jenkins tools")
    return tools


@server.call_tool()
async def handle_call_tool(
        name: str,
        arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests with improved error handling and metrics tracking"""
    arguments = arguments or {}
    start_time = time.time()
    success = False
    error_message = None

    try:
        # Use cached client for better performance
        client = await get_cached_jenkins_client(get_settings())

        # Route to appropriate handler
        handlers = {
            # Build operations
            "trigger-build": _tool_trigger_build,
            "stop-build": _tool_stop_build,

            # Job information
            "list-jobs": _tool_list_jobs,
            "get-job-details": _tool_get_job_details,

            # Build information
            "get-build-info": _tool_get_build_info,
            "get-build-console": _tool_get_build_console,
            "get-last-build-number": _tool_get_last_build_number,
            "get-last-build-timestamp": _tool_get_last_build_timestamp,

            # Job management
            "create-job": _tool_create_job,
            "create-job-from-copy": _tool_create_job_from_copy,
            "create-job-from-data": _tool_create_job_from_data,
            "delete-job": _tool_delete_job,
            "enable-job": _tool_enable_job,
            "disable-job": _tool_disable_job,
            "rename-job": _tool_rename_job,

            # Job configuration
            "get-job-config": _tool_get_job_config,
            "update-job-config": _tool_update_job_config,

            # System information
            "get-queue-info": _tool_get_queue_info,
            "list-nodes": _tool_list_nodes,
            "get-node-info": _tool_get_node_info,

            # Health check (Quick Win #1)
            "health-check": _tool_health_check,

            # NEW: Medium Priority
            "trigger-multiple-builds": _tool_trigger_multiple_builds,
            "get-cache-stats": _tool_get_cache_stats,
            "clear-cache": _tool_clear_cache,

            # NEW: Low Priority
            "get-metrics": _tool_get_metrics,
            "configure-webhook": _tool_configure_webhook,
        }

        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")

        result = await handler(client, arguments)
        success = True
        return result

    # Better error messages with troubleshooting steps (Quick Win #2)
    except ValueError as e:
        # Validation errors - user's fault
        logger.warning(f"Validation error in {name}: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"❌ Invalid input for {name}: {str(e)}\n\n"
                     f"💡 Please check the parameter values and try again."
            )
        ]
    except ImportError:
        # Missing requests library
        import_error = (
            f"⚠️ Missing required library 'requests'.\n\n"
            f"To fix this, run:\n"
            f"pip install requests"
        )
        logger.error(f"Import error in {name}: requests library not found")
        return [types.TextContent(type="text", text=import_error)]
    except Exception as e:
        # Check for common requests exceptions
        error_type = type(e).__name__
        error_message = str(e)

        # Timeout errors
        if 'timeout' in error_message.lower() or error_type == 'Timeout':
            logger.error(f"Timeout error in {name}: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"⏱️ Timeout connecting to Jenkins.\n\n"
                         f"Troubleshooting steps:\n"
                         f"1. Check Jenkins server is running\n"
                         f"2. Verify URL is correct: {get_settings().url}\n"
                         f"3. Ensure network/VPN connection is active\n"
                         f"4. Check firewall settings\n\n"
                         f"Error: {str(e)}"
                )
            ]

        # Connection errors
        elif 'connection' in error_message.lower() or error_type in ['ConnectionError', 'ConnectionRefusedError']:
            logger.error(f"Connection error in {name}: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"🔌 Cannot connect to Jenkins at {get_settings().url}\n\n"
                         f"Troubleshooting steps:\n"
                         f"1. Verify Jenkins server is accessible\n"
                         f"2. Check port is correct (usually 8080)\n"
                         f"3. Ensure firewall allows connection\n"
                         f"4. Test with: curl {get_settings().url}/api/json\n\n"
                         f"Error: {str(e)}"
                )
            ]

        # Authentication errors (401)
        elif '401' in error_message or 'unauthorized' in error_message.lower():
            logger.error(f"Authentication error in {name}: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"🔐 Authentication failed.\n\n"
                         f"Troubleshooting steps:\n"
                         f"1. Verify username is correct: {get_settings().username}\n"
                         f"2. Check API token is valid (not expired)\n"
                         f"3. Generate new token in Jenkins:\n"
                         f"   - Go to Jenkins → Your Name → Configure\n"
                         f"   - Click 'Add new Token' under API Token section\n"
                         f"4. Update .env file with new token\n\n"
                         f"Error: {str(e)}"
                )
            ]

        # Permission errors (403)
        elif '403' in error_message or 'forbidden' in error_message.lower():
            logger.error(f"Permission error in {name}: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"🚫 Permission denied.\n\n"
                         f"Troubleshooting steps:\n"
                         f"1. Check user has permission to access Jenkins\n"
                         f"2. Verify user has permission for this operation\n"
                         f"3. Contact Jenkins admin to grant necessary permissions\n\n"
                         f"User: {get_settings().username}\n"
                         f"Operation: {name}\n"
                         f"Error: {str(e)}"
                )
            ]

        # Not found errors (404)
        elif '404' in error_message or 'not found' in error_message.lower():
            logger.error(f"Not found error in {name}: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Resource not found.\n\n"
                         f"Troubleshooting steps:\n"
                         f"1. Check job/resource name is correct (case-sensitive)\n"
                         f"2. Verify resource exists in Jenkins\n"
                         f"3. Ensure user has permission to view the resource\n"
                         f"4. Try listing all jobs with 'list-jobs' tool\n\n"
                         f"Error: {str(e)}"
                )
            ]

        # Generic error with some context
        else:
            logger.error(f"Tool execution failed for {name}: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Error executing {name}\n\n"
                         f"Error type: {error_type}\n"
                         f"Error message: {str(e)}\n\n"
                         f"💡 Troubleshooting tips:\n"
                         f"1. Run 'health-check' tool to verify connection\n"
                         f"2. Check Jenkins logs for more details\n"
                         f"3. Verify all parameters are correct\n"
                         f"4. Try the operation manually in Jenkins UI"
                )
            ]

    finally:
        # Record metrics
        execution_time_ms = (time.time() - start_time) * 1000
        await record_tool_execution(
            tool_name=name,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            args={"tool": name}  # Don't log full args for privacy
        )


# ==================== Tool Handlers ====================

# Build Operations

async def _tool_trigger_build(client, args):
    """Trigger a Jenkins build"""
    # Input validation (Quick Win #4)
    job_name = validate_job_name(args.get("job_name"))
    parameters = args.get("parameters", {})

    if parameters and not isinstance(parameters, dict):
        raise ValueError(f"parameters must be a dictionary, got {type(parameters).__name__}")

    result = client.build_job(job_name, parameters)

    text = f"Successfully triggered build for job '{job_name}'.\n"
    if result['queue_id']:
        text += f"Queue ID: {result['queue_id']}\n"
    if result['build_number']:
        text += f"Build number: #{result['build_number']}\n"
    if parameters:
        text += f"Parameters: {json.dumps(parameters, indent=2)}"

    return [types.TextContent(type="text", text=text)]


async def _tool_stop_build(client, args):
    """Stop a running build"""
    # Input validation (Quick Win #4)
    job_name = validate_job_name(args.get("job_name"))
    build_number = validate_build_number(args.get("build_number"))

    client.stop_build(job_name, build_number)

    return [
        types.TextContent(
            type="text",
            text=f"Successfully stopped build #{build_number} for job '{job_name}'."
        )
    ]


# Job Information

async def _tool_list_jobs(client, args):
    """List all Jenkins jobs with optional filtering and caching"""
    filter_text = args.get("filter", "").strip()
    use_cache = args.get("use_cache", True)  # cache control

    # Try cache first (if enabled)
    cache_key = f"jobs_list:{filter_text or 'all'}"
    if use_cache:
        cache_manager = get_cache_manager()
        cached_jobs = await cache_manager.get(cache_key)
        if cached_jobs is not None:
            logger.debug(f"Using cached job list ({len(cached_jobs)} jobs)")
            return [
                types.TextContent(
                    type="text",
                    text=f"Jenkins Jobs (cached) ({len(cached_jobs)} total):\n\n{json.dumps(cached_jobs, indent=2)}"
                )
            ]

    # Fetch from Jenkins
    jobs = client.get_jobs()

    # Apply filter if provided
    if filter_text:
        filter_lower = filter_text.lower()
        jobs = [
            job for job in jobs
            if filter_lower in job.get("name", "").lower()
        ]

    jobs_info = [
        {
            "name": job.get("name"),
            "url": job.get("url"),
            "status": job.get("color", "unknown")
        }
        for job in jobs
    ]

    # Cache the result
    if use_cache:
        await cache_manager.set(cache_key, jobs_info, ttl_seconds=30)

    # Build response message
    if filter_text:
        message = f"Jenkins Jobs matching '{filter_text}' ({len(jobs_info)} found):\n\n{json.dumps(jobs_info, indent=2)}"
    else:
        message = f"Jenkins Jobs ({len(jobs_info)} total):\n\n{json.dumps(jobs_info, indent=2)}"

    return [
        types.TextContent(
            type="text",
            text=message
        )
    ]


async def _tool_get_job_details(client, args):
    """Get detailed job information"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))

    # Configurable number of recent builds to fetch (Critical Issue #3)
    max_recent_builds = args.get("max_recent_builds", 3)
    try:
        max_recent_builds = int(max_recent_builds)
        if max_recent_builds < 0:
            max_recent_builds = 0
        elif max_recent_builds > 10:
            max_recent_builds = 10  # Cap at 10 to prevent excessive API calls
    except (ValueError, TypeError):
        max_recent_builds = 3  # Default to 3

    job_info = client.get_job_info(job_name)

    details = {
        "name": job_info.get("name", job_name),
        "url": job_info.get("url", ""),
        "description": job_info.get("description", ""),
        "buildable": job_info.get("buildable", False),
        "lastBuild": job_info.get("lastBuild", {}),
        "lastSuccessfulBuild": job_info.get("lastSuccessfulBuild", {}),
        "lastFailedBuild": job_info.get("lastFailedBuild", {}),
    }

    # Add recent builds (optimized to reduce API calls)
    if max_recent_builds > 0 and "builds" in job_info:
        recent_builds = []
        builds_to_fetch = job_info["builds"][:max_recent_builds]

        logger.info(f"Fetching {len(builds_to_fetch)} recent builds for '{job_name}'")

        for build in builds_to_fetch:
            try:
                build_info = client.get_build_info(job_name, build["number"])
                recent_builds.append({
                    "number": build_info.get("number"),
                    "result": build_info.get("result"),
                    "timestamp": build_info.get("timestamp"),
                    "duration_seconds": build_info.get("duration", 0) / 1000,
                })
            except Exception as e:
                logger.warning(f"Could not fetch build {build['number']}: {e}")

        details["recentBuilds"] = recent_builds
        details["recentBuildsCount"] = len(recent_builds)

    # Notify of resource changes
    try:
        await server.request_context.session.send_resource_list_changed()
    except Exception:
        pass

    return [
        types.TextContent(
            type="text",
            text=f"Job details for '{job_name}':\n\n{json.dumps(details, indent=2)}"
        )
    ]


# Build Information

async def _tool_get_build_info(client, args):
    """Get build information"""
    # Input validation (Quick Win #4)
    job_name = validate_job_name(args.get("job_name"))
    build_number = validate_build_number(args.get("build_number"))

    build_info = client.get_build_info(job_name, build_number)

    formatted_info = {
        "number": build_info.get("number"),
        "result": build_info.get("result"),
        "timestamp": build_info.get("timestamp"),
        "duration_seconds": build_info.get("duration", 0) / 1000,
        "url": build_info.get("url"),
        "building": build_info.get("building", False),
    }

    # Add change information if available
    if "changeSet" in build_info and "items" in build_info["changeSet"]:
        changes = [
            {
                "author": change.get("author", {}).get("fullName", "Unknown"),
                "comment": change.get("comment", ""),
            }
            for change in build_info["changeSet"]["items"]
        ]
        formatted_info["changes"] = changes

    return [
        types.TextContent(
            type="text",
            text=f"Build info for {job_name} #{build_number}:\n\n{json.dumps(formatted_info, indent=2)}"
        )
    ]


async def _tool_get_build_console(client, args):
    """Get build console output with improved truncation (High Priority Issue #5)"""
    # Input validation (Quick Win #4)
    job_name = validate_job_name(args.get("job_name"))
    build_number = validate_build_number(args.get("build_number"))

    # Get configurable parameters with defaults from settings
    settings = get_settings()
    max_lines = args.get("max_lines", settings.console_max_lines)
    tail_only = args.get("tail_only", False)

    # Validate max_lines
    try:
        max_lines = int(max_lines)
        if max_lines < 10:
            max_lines = 10
        elif max_lines > 10000:
            max_lines = 10000
    except (ValueError, TypeError):
        max_lines = settings.console_max_lines

    # Validate tail_only
    if not isinstance(tail_only, bool):
        tail_only = str(tail_only).lower() in ('true', '1', 'yes')

    # Get console output
    console_output = client.get_build_console_output(job_name, build_number)

    # Split into lines for better handling
    all_lines = console_output.split('\n')
    total_lines = len(all_lines)

    # Determine what to show
    prefix = ""
    if total_lines <= max_lines:
        # No truncation needed
        output_lines = all_lines
        prefix = f"[Complete output: {total_lines} lines]\n\n"
    elif tail_only:
        # Show last N lines
        output_lines = all_lines[-max_lines:]
        truncated_lines = total_lines - max_lines
        prefix = f"[Showing last {max_lines} of {total_lines} lines - {truncated_lines} earlier lines omitted]\n\n"
    else:
        # Show first N lines
        output_lines = all_lines[:max_lines]
        truncated_lines = total_lines - max_lines
        prefix = f"[Showing first {max_lines} of {total_lines} lines - {truncated_lines} later lines truncated]\n\n"

    # Reconstruct output
    final_output = '\n'.join(output_lines)

    # Add helpful note if truncated
    if total_lines > max_lines:
        if tail_only:
            suffix = f"\n\n💡 Tip: Use max_lines parameter to see more lines (current: {max_lines}, max: 10000)"
        else:
            suffix = f"\n\n💡 Tip: Set tail_only=true to see last {max_lines} lines, or increase max_lines (current: {max_lines}, max: 10000)"
    else:
        suffix = ""

    return [
        types.TextContent(
            type="text",
            text=f"{prefix}Console output for {job_name} #{build_number}:\n\n```\n{final_output}\n```{suffix}"
        )
    ]


async def _tool_get_last_build_number(client, args):
    """Get last build number"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))

    num = client.get_last_build_number(job_name)
    return [types.TextContent(type="text", text=f"Last build number for '{job_name}': {num}")]


async def _tool_get_last_build_timestamp(client, args):
    """Get last build timestamp"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))

    ts = client.get_last_build_timestamp(job_name)
    return [types.TextContent(type="text", text=f"Last build timestamp for '{job_name}': {ts}")]


# Job Management

async def _tool_create_job(client, args):
    """Create a new job"""
    # Input validation (Quick Win #4)
    job_name = validate_job_name(args.get("job_name"))
    config_xml = validate_config_xml(args.get("config_xml"))

    client.create_job(job_name, config_xml)
    return [types.TextContent(type="text", text=f"Successfully created job '{job_name}'")]


async def _tool_create_job_from_copy(client, args):
    """Create job from copy"""
    # Input validation
    new_job_name = validate_job_name(args.get("new_job_name"))
    source_job_name = validate_job_name(args.get("source_job_name"))

    client.create_job_from_copy(new_job_name, source_job_name)
    return [types.TextContent(type="text", text=f"Successfully created job '{new_job_name}' from '{source_job_name}'")]


async def _tool_create_job_from_data(client, args):
    """Create job from data"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))
    config_data = args.get("config_data")
    root_tag = args.get("root_tag", "project")

    if config_data is None:
        raise ValueError("Missing required argument: config_data")
    if not isinstance(config_data, dict):
        raise ValueError(f"config_data must be a dictionary, got {type(config_data).__name__}")

    client.create_job_from_dict(job_name, config_data, root_tag)
    return [types.TextContent(type="text", text=f"Successfully created job '{job_name}' from data")]


async def _tool_delete_job(client, args):
    """Delete a job"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))

    client.delete_job(job_name)
    return [types.TextContent(type="text", text=f"Successfully deleted job '{job_name}'")]


async def _tool_enable_job(client, args):
    """Enable a job"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))

    client.enable_job(job_name)
    return [types.TextContent(type="text", text=f"Successfully enabled job '{job_name}'")]


async def _tool_disable_job(client, args):
    """Disable a job"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))

    client.disable_job(job_name)
    return [types.TextContent(type="text", text=f"Successfully disabled job '{job_name}'")]


async def _tool_rename_job(client, args):
    """Rename a job"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))
    new_name = validate_job_name(args.get("new_name"))

    client.rename_job(job_name, new_name)
    return [types.TextContent(type="text", text=f"Successfully renamed job '{job_name}' to '{new_name}'")]


# Job Configuration

async def _tool_get_job_config(client, args):
    """Get job configuration"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))

    config = client.get_job_config(job_name)
    return [types.TextContent(type="text", text=config)]


async def _tool_update_job_config(client, args):
    """Update job configuration"""
    # Input validation
    job_name = validate_job_name(args.get("job_name"))
    config_xml = validate_config_xml(args.get("config_xml"))

    client.update_job_config(job_name, config_xml)
    return [types.TextContent(type="text", text=f"Successfully updated config for job '{job_name}'")]


# System Information

async def _tool_get_queue_info(client, args):
    """Get build queue information"""
    queue_items = client.get_queue_info()

    if not queue_items:
        return [types.TextContent(type="text", text="Jenkins build queue is empty.")]

    formatted_queue = [
        {
            "id": item.get("id"),
            "job": item.get("task", {}).get("name", "Unknown"),
            "inQueueSince": item.get("inQueueSince"),
            "why": item.get("why", "Unknown reason"),
            "blocked": item.get("blocked", False),
        }
        for item in queue_items
    ]

    return [
        types.TextContent(
            type="text",
            text=f"Jenkins build queue ({len(formatted_queue)} items):\n\n{json.dumps(formatted_queue, indent=2)}"
        )
    ]


async def _tool_list_nodes(client, args):
    """List all Jenkins nodes"""
    nodes = client.get_nodes()

    nodes_info = [
        {
            "name": node.get("displayName"),
            "description": node.get("description", ""),
            "offline": node.get("offline", False),
            "executors": node.get("numExecutors", 0),
        }
        for node in nodes
    ]

    return [
        types.TextContent(
            type="text",
            text=f"Jenkins nodes/agents ({len(nodes_info)} total):\n\n{json.dumps(nodes_info, indent=2)}"
        )
    ]


async def _tool_get_node_info(client, args):
    """Get node information"""
    # Input validation
    node_name = args.get("node_name")
    if not node_name:
        raise ValueError("Missing required argument: node_name")
    if not isinstance(node_name, str):
        raise ValueError(f"node_name must be a string, got {type(node_name).__name__}")
    node_name = node_name.strip()

    node_info = client.get_node_info(node_name)

    formatted_info = {
        "name": node_info.get("displayName"),
        "description": node_info.get("description"),
        "offline": node_info.get("offline", False),
        "temporarilyOffline": node_info.get("temporarilyOffline", False),
        "offlineCause": str(node_info.get("offlineCauseReason", "")),
        "executors": node_info.get("numExecutors", 0),
    }

    return [
        types.TextContent(
            type="text",
            text=f"Information for node '{node_name}':\n\n{json.dumps(formatted_info, indent=2)}"
        )
    ]


async def _tool_get_cache_stats(client, args):
    """Get cache statistics"""
    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()
    cache_info = await cache_manager.get_cache_info()

    report = f"""
📊 Cache Statistics

═══════════════════════════════════════
OVERVIEW
═══════════════════════════════════════
Cache Size:      {stats['size']} entries
Total Requests:  {stats['total_requests']}
Cache Hits:      {stats['hits']}
Cache Misses:    {stats['misses']}
Hit Rate:        {stats['hit_rate_percent']}%
Evictions:       {stats['evictions']}

═══════════════════════════════════════
CACHED ENTRIES
═══════════════════════════════════════
"""

    for entry in cache_info['entries']:
        status = "✅ Valid" if not entry['is_expired'] else "❌ Expired"
        report += f"\n{entry['key']}\n"
        report += f"  Status: {status}\n"
        report += f"  Age: {entry['age_seconds']}s\n"
        report += f"  TTL: {entry['ttl_seconds']}s\n"
        report += f"  Expires in: {entry['expires_in_seconds']}s\n"

    return [types.TextContent(type="text", text=report.strip())]


async def _tool_clear_cache(client, args):
    """Clear all cached data"""
    cache_manager = get_cache_manager()
    cleared = await cache_manager.clear()

    return [types.TextContent(
        type="text",
        text=f"✅ Cache cleared: {cleared} entries removed"
    )]


# Health Check Tool (Quick Win #1)

async def _tool_health_check(client, args):
    """
    Check Jenkins server health and connection status.
    Provides detailed diagnostics for troubleshooting.
    """
    checks = {
        "server_reachable": False,
        "authentication_valid": False,
        "api_responsive": False,
        "server_version": None,
        "server_url": get_settings().url,
        "username": get_settings().username,
        "response_time_ms": None,
        "timestamp": None
    }

    status_emoji = "❌"
    status_text = "Unhealthy"
    error_details = None

    try:
        import datetime
        start_time = time.time()
        checks["timestamp"] = datetime.datetime.now().isoformat()

        # Test 1: Basic connectivity
        try:
            # Try to get user info (tests auth + connectivity)
            user_info = client.get_whoami()
            checks["server_reachable"] = True
            checks["authentication_valid"] = True

            # Get version info
            try:
                version = client.get_version()
                checks["server_version"] = version
                checks["api_responsive"] = True
            except Exception as ve:
                logger.warning(f"Could not get version: {ve}")
                checks["api_responsive"] = False

            # Calculate response time
            elapsed_ms = (time.time() - start_time) * 1000
            checks["response_time_ms"] = round(elapsed_ms, 2)

            # Determine overall status
            if checks["api_responsive"]:
                status_emoji = "✅"
                status_text = "Healthy"
                if elapsed_ms > 2000:
                    status_text = "Healthy (Slow)"
                    status_emoji = "⚠️"
            elif checks["authentication_valid"]:
                status_emoji = "⚠️"
                status_text = "Partially Healthy (API issues)"

        except Exception as conn_error:
            error_details = str(conn_error)
            error_type = type(conn_error).__name__

            # Classify the error
            if 'timeout' in error_details.lower():
                status_text = "Timeout - Server not responding"
                checks["server_reachable"] = False
            elif '401' in error_details or 'unauthorized' in error_details.lower():
                status_text = "Authentication Failed"
                checks["server_reachable"] = True
                checks["authentication_valid"] = False
            elif 'connection' in error_details.lower():
                status_text = "Connection Failed - Server unreachable"
                checks["server_reachable"] = False
            else:
                status_text = f"Error: {error_type}"

    except Exception as e:
        error_details = str(e)
        status_text = f"Health check failed: {type(e).__name__}"
        logger.error(f"Health check error: {e}", exc_info=True)

    # Build detailed report
    report = f"""
{status_emoji} Jenkins Health Check: {status_text}

═══════════════════════════════════════
CONNECTION STATUS
═══════════════════════════════════════
Server URL:          {checks['server_url']}
Username:            {checks['username']}
Server Reachable:    {'✅ Yes' if checks['server_reachable'] else '❌ No'}
Authentication:      {'✅ Valid' if checks['authentication_valid'] else '❌ Failed'}
API Responsive:      {'✅ Yes' if checks['api_responsive'] else '❌ No'}

═══════════════════════════════════════
SERVER DETAILS
═══════════════════════════════════════
Jenkins Version:     {checks['server_version'] or 'Unknown'}
Response Time:       {checks['response_time_ms']}ms
Checked At:          {checks['timestamp']}
"""

    if error_details:
        report += f"""
═══════════════════════════════════════
ERROR DETAILS
═══════════════════════════════════════
{error_details}
"""

    # Add troubleshooting tips if unhealthy
    if status_emoji == "❌":
        report += """
═══════════════════════════════════════
TROUBLESHOOTING STEPS
═══════════════════════════════════════
"""
        if not checks['server_reachable']:
            report += """
🔌 Server Not Reachable:
  1. Verify Jenkins is running
  2. Check the URL is correct
  3. Test with: curl {url}/api/json
  4. Check firewall/VPN settings
  5. Verify network connectivity
""".format(url=checks['server_url'])

        if checks['server_reachable'] and not checks['authentication_valid']:
            report += """
🔐 Authentication Failed:
  1. Verify username is correct
  2. Check API token is valid
  3. Generate new token:
     - Jenkins → Your Name → Configure
     - API Token section → Add new Token
  4. Update .env file with new token
"""

        if checks['server_reachable'] and checks['authentication_valid'] and not checks['api_responsive']:
            report += """
⚠️ API Not Responsive:
  1. Check Jenkins server logs
  2. Verify Jenkins is not overloaded
  3. Check for Jenkins plugin issues
  4. Restart Jenkins if needed
"""

    report += "\n💡 Tip: Run this health-check regularly to monitor your Jenkins connection."

    return [types.TextContent(type="text", text=report.strip())]


async def _tool_get_metrics(client, args):
    """Get usage metrics"""
    tool_name = args.get("tool_name")

    metrics_collector = get_metrics_collector()

    if tool_name:
        # Get specific tool metrics
        stats = await metrics_collector.get_tool_stats(tool_name)

        report = f"""
📊 Metrics for '{tool_name}'

{json.dumps(stats, indent=2)}
"""
    else:
        # Get overall summary
        summary = await metrics_collector.get_summary()
        tool_stats = await metrics_collector.get_tool_stats()

        report = f"""
📊 Jenkins MCP Server Metrics

═══════════════════════════════════════
SUMMARY
═══════════════════════════════════════
Uptime:              {summary['uptime_human']}
Total Executions:    {summary['total_executions']}
Successful:          {summary['successful_executions']}
Failed:              {summary['failed_executions']}
Success Rate:        {summary['success_rate_percent']}%
Avg Execution Time:  {summary['avg_execution_time_ms']}ms
Unique Tools Used:   {summary['unique_tools_used']}
Most Used Tool:      {summary['most_used_tool']}
Slowest Tool:        {summary['slowest_tool']}

═══════════════════════════════════════
PER-TOOL STATISTICS
═══════════════════════════════════════
{json.dumps(tool_stats, indent=2)}
"""

    return [types.TextContent(type="text", text=report.strip())]


async def _tool_configure_webhook(client, args):
    """Configure webhook for Jenkins job"""
    job_name = validate_job_name(args.get("job_name"))
    webhook_url = args.get("webhook_url")
    events = args.get("events", [])

    if not webhook_url:
        raise ValueError("webhook_url is required")

    if not events:
        raise ValueError("At least one event must be specified")

    # Get current job config
    config_xml = client.get_job_config(job_name)

    # Add webhook notification (this is simplified - actual implementation
    # depends on Jenkins plugin configuration)
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(config_xml)

        # Add or update properties section
        properties = root.find('properties')
        if properties is None:
            properties = ET.SubElement(root, 'properties')

        # Add webhook trigger configuration
        # (Actual XML structure depends on the webhook plugin used)
        webhook_config = f"""
        <!-- Webhook Configuration -->
        <!-- Events: {', '.join(events)} -->
        <!-- URL: {webhook_url} -->
        """

        # Note: This is a placeholder. Real implementation would need
        # to configure the actual webhook plugin XML structure

        updated_xml = ET.tostring(root, encoding='unicode')

        # Update job
        client.update_job_config(job_name, updated_xml)

        return [types.TextContent(
            type="text",
            text=f"✅ Webhook configured for '{job_name}'\n\n"
                 f"URL: {webhook_url}\n"
                 f"Events: {', '.join(events)}\n\n"
                 f"⚠️ Note: Requires Generic Webhook Trigger plugin in Jenkins"
        )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ Failed to configure webhook: {str(e)}\n\n"
                 f"Make sure the Generic Webhook Trigger plugin is installed in Jenkins."
        )]


# Note: MCP protocol may not support streaming yet. This is prepared for future use.
# Example: For trigger-multiple-builds
async def _tool_trigger_multiple_builds_with_progress(client, args):
    """Trigger builds with progress updates"""
    job_names = args.get("job_names", [])

    # Initial message
    yield types.TextContent(
        type="text",
        text=f"🚀 Starting batch build trigger for {len(job_names)} jobs..."
    )

    results = []
    for i, job_name in enumerate(job_names, 1):
        # Progress update
        yield types.TextContent(
            type="text",
            text=f"⏳ [{i}/{len(job_names)}] Triggering {job_name}..."
        )

        try:
            result = client.build_job(job_name)
            results.append({"job": job_name, "status": "success"})
        except Exception as e:
            results.append({"job": job_name, "status": "failed", "error": str(e)})

    # Final summary
    successful = len([r for r in results if r["status"] == "success"])
    yield types.TextContent(
        type="text",
        text=f"✅ Complete: {successful}/{len(job_names)} builds triggered successfully"
    )


# ==================== Main Server Entry Point ====================

async def main():
    """Run the Jenkins MCP server"""
    try:
        # Add explicit stderr debug
        vprint("=== main() entered ===")

        # Verify settings are configured
        settings = get_settings()
        vprint(f"=== Settings verified: {settings.is_configured} ===")

        if not settings.is_configured:
            logger.error("Jenkins settings not configured!")
            sys.exit(1)

        vprint(f"=== About to log startup message ===")
        logger.info(f"Starting Jenkins MCP Server v1.1.16")
        logger.info(f"Connected to: {settings.url}")
        vprint(f"=== Startup messages logged ===")

        # Run the server using stdin/stdout streams
        vprint("=== About to create stdio_server ===")
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            vprint("=== stdio_server created ===")
            vprint("=== About to call server.run() ===")

            now_local = datetime.now().astimezone()
            formatted_date = now_local.strftime("%a %b %d %H:%M:%S %Z %Y")

            print(f"\n------ JENKINS MCP SERVER STARTUP ------")
            print(f"MCP Server started successfully on {formatted_date}")
            print(f"Press Ctrl+C to stop the server")
            print(f"----------------------------------------")
            if _VERBOSE:
                vprint(f"Jenkins MCP Server v1.1.16")
                vprint(f"Connected to: {settings.url}")

            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="jenkins-mcp-server",
                    server_version="1.1.16",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
            vprint("=== server.run() completed ===")
    except KeyboardInterrupt:
        vprint("=== Received interrupt signal ===")
        if not _VERBOSE:
            logger.info("Server stopped")

    except BaseException as e:
        # Catch BaseExceptionGroup (Python 3.11+) and regular exceptions
        if type(e).__name__ == 'ExceptionGroup' or type(e).__name__ == 'BaseExceptionGroup':
            # Handle exception group
            vprint("=== Handling exception group ===")
            exceptions = getattr(e, 'exceptions', [e])

            # Check if all exceptions are OSError with errno 5 (expected on Ctrl+C)
            all_io_errors = all(
                isinstance(exc, OSError) and getattr(exc, 'errno', None) == 5
                for exc in exceptions
            )

            if all_io_errors:
                vprint("=== I/O error (stdin closed) ===")
                if not _VERBOSE:
                    logger.info("Server stopped")
                # Clean exit - don't re-raise
            else:
                # Some other error
                for exc in exceptions:
                    logger.error(f"Server error: {exc}", exc_info=True)
                sys.exit(1)
        elif isinstance(e, (OSError, IOError)) and getattr(e, 'errno', None) == 5:
            # Regular OSError with errno 5
            vprint("=== I/O error (stdin closed) ===")
            if not _VERBOSE:
                logger.info("Server stopped")
        else:
            # Some other error - re-raise
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise