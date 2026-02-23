"""
Jenkins MCP Server Package

Main entry point for the Jenkins MCP Server.
"""

import argparse
import asyncio
import logging
import sys

from .config import get_settings, get_default_settings
from .verbose import set_verbose, vprint
from .version import __version__
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
        version=f'jenkins-mcp-server {__version__}'
    )

    parser.add_argument(
        '--no-vscode',
        action='store_true',
        help='Skip loading settings from VS Code (use only .env/environment)'
    )

    args = parser.parse_args()
    set_verbose(args.verbose)

    vprint(f"=== Args parsed: env_file={args.env_file}, verbose={args.verbose} ===")

    # Setup logging first
    vprint("=== Setting up logging ===")
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    vprint("=== Logging configured ===")

    try:
        # Load settings based on arguments
        vprint("=== Loading Jenkins configuration ===")
        logger.info("Loading Jenkins configuration...")

        settings = get_settings(
            env_file=args.env_file,
            load_vscode=not args.no_vscode
        )
        vprint(f"=== Settings loaded: url={settings.url}, configured={settings.is_configured} ===")

        # Validate configuration
        if not settings.is_configured:
            logger.error("Jenkins configuration is incomplete!")
            logger.error("Required: URL, username, and (token or password)")
            logger.error("\nPlease configure via:")
            logger.error("  1. .env file (JENKINS_URL, JENKINS_USERNAME, JENKINS_TOKEN)")
            logger.error("  2. VS Code settings.json")
            logger.error("  3. Environment variables")
            # logger.error("\nFor help, run: %(prog)s --help" % {'prog': parser.prog})
            logger.error("\nFor help, run: %(prog)s --help" % {'prog': "jenkins-mcp-server"})
            sys.exit(1)

        # Log configuration summary
        vprint("=== Configuration validated ===")
        logger.info(f"Jenkins server: {settings.url}")
        logger.info(f"Username: {settings.username}")
        logger.info(f"Authentication: {settings.auth_method}")

        # Pass settings to server module
        vprint("=== Setting server settings ===")
        server.set_jenkins_settings(settings)
        vprint("=== Server settings configured ===")

        # Run the server
        vprint("=== Starting asyncio server ===")
        logger.info("Starting Jenkins MCP Server...")
        asyncio.run(server.main())

    except KeyboardInterrupt:
        vprint("=== Server stopped by user ===")
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        vprint(f"=== EXCEPTION: {e} ===")
        logger.error(f"Failed to start server: {e}", exc_info=args.verbose)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


# Package metadata
__all__ = ['main', 'server', '__version__']