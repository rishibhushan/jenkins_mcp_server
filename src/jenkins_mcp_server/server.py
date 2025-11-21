"""
Jenkins MCP Server Implementation

Provides MCP protocol handlers for Jenkins operations including:
- Resources (job information)
- Prompts (analysis templates)
- Tools (Jenkins operations)
"""

import json
import logging
import sys
from typing import Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

from .config import JenkinsSettings, get_default_settings
from .jenkins_client import get_jenkins_client, JenkinsConnectionError

# Configure logging
logger = logging.getLogger(__name__)

# Server instance
server = Server("jenkins-mcp-server")

# Settings storage (injected by main)
_jenkins_settings: Optional[JenkinsSettings] = None


def set_jenkins_settings(settings: JenkinsSettings) -> None:
    """Set Jenkins settings for the server (called from __init__.py)"""
    global _jenkins_settings
    _jenkins_settings = settings


def get_settings() -> JenkinsSettings:
    """Get current Jenkins settings"""
    global _jenkins_settings
    if _jenkins_settings is None:
        _jenkins_settings = get_default_settings()
    return _jenkins_settings


# ==================== Resources ====================

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available Jenkins resources.
    Each job is exposed as a resource with jenkins:// URI scheme.
    """
    try:
        client = get_jenkins_client(get_settings())
        jobs = client.get_jobs()

        return [
            types.Resource(
                uri=AnyUrl(f"jenkins://job/{job['name']}"),
                name=f"Job: {job['name']}",
                description=f"Jenkins job: {job['name']} (status: {job.get('color', 'unknown')})",
                mimeType="application/json",
            )
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Failed to list resources: {e}")
        return [
            types.Resource(
                uri=AnyUrl("jenkins://error"),
                name="Error connecting to Jenkins",
                description=f"Error: {str(e)}",
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


# ==================== Tools ====================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for interacting with Jenkins"""
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
                    "job_name": {"type": "string"},
                    "build_number": {"type": "integer"},
                },
                "required": ["job_name", "build_number"],
            },
        ),

        # Job Information
        types.Tool(
            name="list-jobs",
            description="List all Jenkins jobs with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Filter jobs by name (case-insensitive partial match)"
                    }
                }
            },
        ),
        types.Tool(
            name="get-job-details",
            description="Get detailed information about a Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {"job_name": {"type": "string"}},
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
                    "job_name": {"type": "string"},
                    "build_number": {"type": "integer"},
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
                    "job_name": {"type": "string"},
                    "build_number": {"type": "integer"},
                },
                "required": ["job_name", "build_number"],
            },
        ),
        types.Tool(
            name="get-last-build-number",
            description="Get the last build number for a job",
            inputSchema={
                "type": "object",
                "properties": {"job_name": {"type": "string"}},
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="get-last-build-timestamp",
            description="Get the timestamp of the last build",
            inputSchema={
                "type": "object",
                "properties": {"job_name": {"type": "string"}},
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
                    "job_name": {"type": "string"},
                    "config_xml": {"type": "string", "description": "Job configuration XML"},
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
                    "new_job_name": {"type": "string"},
                    "source_job_name": {"type": "string"},
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
                    "job_name": {"type": "string"},
                    "config_data": {"type": "object"},
                    "root_tag": {"type": "string", "default": "project"},
                },
                "required": ["job_name", "config_data"],
            },
        ),
        types.Tool(
            name="delete-job",
            description="Delete an existing Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {"job_name": {"type": "string"}},
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="enable-job",
            description="Enable a disabled Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {"job_name": {"type": "string"}},
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="disable-job",
            description="Disable a Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {"job_name": {"type": "string"}},
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="rename-job",
            description="Rename an existing Jenkins job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string"},
                    "new_name": {"type": "string"},
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
                "properties": {"job_name": {"type": "string"}},
                "required": ["job_name"],
            },
        ),
        types.Tool(
            name="update-job-config",
            description="Update the configuration XML for a job",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string"},
                    "config_xml": {"type": "string"},
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
                "properties": {"node_name": {"type": "string"}},
                "required": ["node_name"],
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
    """Handle tool execution requests"""
    arguments = arguments or {}

    try:
        client = get_jenkins_client(get_settings())

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
        }

        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(client, arguments)

    except Exception as e:
        logger.error(f"Tool execution failed for {name}: {e}", exc_info=True)
        return [
            types.TextContent(
                type="text",
                text=f"Error executing {name}: {str(e)}"
            )
        ]


# ==================== Tool Handlers ====================

# Build Operations

async def _tool_trigger_build(client, args):
    """Trigger a Jenkins build"""
    job_name = args.get("job_name")
    parameters = args.get("parameters", {})

    if not job_name:
        raise ValueError("Missing required argument: job_name")

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
    job_name = args.get("job_name")
    build_number = args.get("build_number")

    if not job_name or build_number is None:
        raise ValueError("Missing required arguments: job_name and build_number")

    client.stop_build(job_name, build_number)

    return [
        types.TextContent(
            type="text",
            text=f"Successfully stopped build #{build_number} for job '{job_name}'."
        )
    ]


# Job Information

async def _tool_list_jobs(client, args):
    """List all Jenkins jobs with optional filtering"""
    jobs = client.get_jobs()
    filter_text = args.get("filter", "").strip()

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
    job_name = args.get("job_name")

    if not job_name:
        raise ValueError("Missing required argument: job_name")

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

    # Add recent builds
    if "builds" in job_info:
        recent_builds = []
        for build in job_info["builds"][:5]:
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
    job_name = args.get("job_name")
    build_number = args.get("build_number")

    if not job_name or build_number is None:
        raise ValueError("Missing required arguments: job_name and build_number")

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
    """Get build console output"""
    job_name = args.get("job_name")
    build_number = args.get("build_number")

    if not job_name or build_number is None:
        raise ValueError("Missing required arguments: job_name and build_number")

    console_output = client.get_build_console_output(job_name, build_number)

    # Limit output size
    max_length = 10000
    if len(console_output) > max_length:
        console_output = console_output[:max_length] + "\n... (output truncated)"

    return [
        types.TextContent(
            type="text",
            text=f"Console output for {job_name} #{build_number}:\n\n```\n{console_output}\n```"
        )
    ]


async def _tool_get_last_build_number(client, args):
    """Get last build number"""
    job_name = args.get("job_name")
    if not job_name:
        raise ValueError("Missing required argument: job_name")

    num = client.get_last_build_number(job_name)
    return [types.TextContent(type="text", text=f"Last build number for '{job_name}': {num}")]


async def _tool_get_last_build_timestamp(client, args):
    """Get last build timestamp"""
    job_name = args.get("job_name")
    if not job_name:
        raise ValueError("Missing required argument: job_name")

    ts = client.get_last_build_timestamp(job_name)
    return [types.TextContent(type="text", text=f"Last build timestamp for '{job_name}': {ts}")]


# Job Management

async def _tool_create_job(client, args):
    """Create a new job"""
    job_name = args.get("job_name")
    config_xml = args.get("config_xml")

    if not job_name or not config_xml:
        raise ValueError("Missing required arguments: job_name and config_xml")

    client.create_job(job_name, config_xml)
    return [types.TextContent(type="text", text=f"Successfully created job '{job_name}'")]


async def _tool_create_job_from_copy(client, args):
    """Create job from copy"""
    new_job_name = args.get("new_job_name")
    source_job_name = args.get("source_job_name")

    if not new_job_name or not source_job_name:
        raise ValueError("Missing required arguments: new_job_name and source_job_name")

    client.create_job_from_copy(new_job_name, source_job_name)
    return [types.TextContent(type="text", text=f"Successfully created job '{new_job_name}' from '{source_job_name}'")]


async def _tool_create_job_from_data(client, args):
    """Create job from data"""
    job_name = args.get("job_name")
    config_data = args.get("config_data")
    root_tag = args.get("root_tag", "project")

    if not job_name or config_data is None:
        raise ValueError("Missing required arguments: job_name and config_data")

    client.create_job_from_dict(job_name, config_data, root_tag)
    return [types.TextContent(type="text", text=f"Successfully created job '{job_name}' from data")]


async def _tool_delete_job(client, args):
    """Delete a job"""
    job_name = args.get("job_name")
    if not job_name:
        raise ValueError("Missing required argument: job_name")

    client.delete_job(job_name)
    return [types.TextContent(type="text", text=f"Successfully deleted job '{job_name}'")]


async def _tool_enable_job(client, args):
    """Enable a job"""
    job_name = args.get("job_name")
    if not job_name:
        raise ValueError("Missing required argument: job_name")

    client.enable_job(job_name)
    return [types.TextContent(type="text", text=f"Successfully enabled job '{job_name}'")]


async def _tool_disable_job(client, args):
    """Disable a job"""
    job_name = args.get("job_name")
    if not job_name:
        raise ValueError("Missing required argument: job_name")

    client.disable_job(job_name)
    return [types.TextContent(type="text", text=f"Successfully disabled job '{job_name}'")]


async def _tool_rename_job(client, args):
    """Rename a job"""
    job_name = args.get("job_name")
    new_name = args.get("new_name")

    if not job_name or not new_name:
        raise ValueError("Missing required arguments: job_name and new_name")

    client.rename_job(job_name, new_name)
    return [types.TextContent(type="text", text=f"Successfully renamed job '{job_name}' to '{new_name}'")]


# Job Configuration

async def _tool_get_job_config(client, args):
    """Get job configuration"""
    job_name = args.get("job_name")
    if not job_name:
        raise ValueError("Missing required argument: job_name")

    config = client.get_job_config(job_name)
    return [types.TextContent(type="text", text=config)]


async def _tool_update_job_config(client, args):
    """Update job configuration"""
    job_name = args.get("job_name")
    config_xml = args.get("config_xml")

    if not job_name or not config_xml:
        raise ValueError("Missing required arguments: job_name and config_xml")

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
    node_name = args.get("node_name")

    if not node_name:
        raise ValueError("Missing required argument: node_name")

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


# ==================== Main Server Entry Point ====================

async def main():
    """Run the Jenkins MCP server"""
    try:
        # Verify settings are configured
        settings = get_settings()
        if not settings.is_configured:
            logger.error("Jenkins settings not configured!")
            sys.exit(1)

        logger.info(f"Starting Jenkins MCP Server v1.0.0")
        logger.info(f"Connected to: {settings.url}")

        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="jenkins-mcp-server",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)