"""
Jenkins MCP Server Package

Main entry point for the Jenkins MCP Server.
"""

import argparse
import asyncio
import logging
import sys

from .config import get_settings, get_default_settings
from . import server


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging"""
    import structlog

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not verbose else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def main():
    """
    Main entry point for the Jenkins MCP Server.

    Parses command-line arguments, configures settings, and starts the server.
    """

    print("=== Jenkins MCP Server: Entry point called ===", file=sys.stderr, flush=True)
    parser = argparse.ArgumentParser(
        description='Jenkins MCP Server - AI-enabled Jenkins automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default .env file
  %(prog)s --env-file /path/to/.env           # Use custom .env file
  %(prog)s --verbose                          # Enable debug logging
  %(prog)s --env-file custom.env --verbose    # Combined options

Environment Variables:
  JENKINS_URL         Jenkins server URL (e.g., http://localhost:8080)
  JENKINS_USERNAME    Jenkins username
  JENKINS_TOKEN       Jenkins API token (recommended)
  JENKINS_PASSWORD    Jenkins password (alternative to token)

Configuration Priority:
  1. Command-line arguments (--env-file)
  2. VS Code settings.json
  3. Environment variables
  4. Default .env file
        """
    )

    parser.add_argument(
        '--env-file',
        metavar='PATH',
        help='Path to custom .env file with Jenkins credentials'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose/debug logging'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='jenkins-mcp-server 1.0.0'
    )

    parser.add_argument(
        '--no-vscode',
        action='store_true',
        help='Skip loading settings from VS Code (use only .env/environment)'
    )

    print("=== Parsing arguments ===", file=sys.stderr, flush=True)
    args = parser.parse_args()
    print(f"=== Args parsed: env_file={args.env_file}, verbose={args.verbose} ===", file=sys.stderr, flush=True)

    # Setup logging first
    print("=== Setting up logging ===", file=sys.stderr, flush=True)
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    print("=== Logging configured ===", file=sys.stderr, flush=True)

    try:
        # Load settings based on arguments
        print("=== Loading Jenkins configuration ===", file=sys.stderr, flush=True)
        logger.info("Loading Jenkins configuration...")

        settings = get_settings(
            env_file=args.env_file,
            load_vscode=not args.no_vscode
        )
        print(f"=== Settings loaded: url={settings.url}, configured={settings.is_configured} ===", file=sys.stderr, flush=True)

        # Validate configuration
        if not settings.is_configured:
            logger.error("Jenkins configuration is incomplete!")
            logger.error("Required: URL, username, and (token or password)")
            logger.error("\nPlease configure via:")
            logger.error("  1. .env file (JENKINS_URL, JENKINS_USERNAME, JENKINS_TOKEN)")
            logger.error("  2. VS Code settings.json")
            logger.error("  3. Environment variables")
            logger.error("\nFor help, run: %(prog)s --help" % {'prog': parser.prog})
            sys.exit(1)

        # Log configuration summary
        print("=== Configuration validated ===", file=sys.stderr, flush=True)
        logger.info(f"Jenkins server: {settings.url}")
        logger.info(f"Username: {settings.username}")
        logger.info(f"Authentication: {settings.auth_method}")

        # Pass settings to server module
        print("=== Setting server settings ===", file=sys.stderr, flush=True)
        server.set_jenkins_settings(settings)
        print("=== Server settings configured ===", file=sys.stderr, flush=True)

        # Run the server
        print("=== Starting asyncio server ===", file=sys.stderr, flush=True)
        logger.info("Starting Jenkins MCP Server...")
        asyncio.run(server.main())

    except KeyboardInterrupt:
        print("=== Server stopped by user ===", file=sys.stderr, flush=True)
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"=== EXCEPTION: {e} ===", file=sys.stderr, flush=True)
        logger.error(f"Failed to start server: {e}", exc_info=args.verbose)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


# Package metadata
__version__ = "1.0.0"
__all__ = ['main', 'server']