#!/usr/bin/env python3
"""
Main entry point for running the Jenkins MCP Server as a module.

Usage:
    python -m jenkins_mcp_server [options]
    
Options:
    --env-file PATH    Path to custom .env file
    --verbose, -v      Enable verbose logging
    --no-vscode        Skip loading VS Code settings
    --version          Show version and exit
    --help, -h         Show help message
"""

from . import main

if __name__ == "__main__":
    main()