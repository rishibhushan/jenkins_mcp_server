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
    """Configure logging for the application"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    # Reduce noise from libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


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
        version='jenkins-mcp-server 1.0.0'
    )

    parser.add_argument(
        '--no-vscode',
        action='store_true',
        help='Skip loading settings from VS Code (use only .env/environment)'
    )

    args = parser.parse_args()

    # Setup logging first
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load settings based on arguments
        logger.info("Loading Jenkins configuration...")

        settings = get_settings(
            env_file=args.env_file,
            load_vscode=not args.no_vscode
        )

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
        logger.info(f"Jenkins server: {settings.url}")
        logger.info(f"Username: {settings.username}")
        logger.info(f"Authentication: {settings.auth_method}")

        # Pass settings to server module
        server.set_jenkins_settings(settings)

        # Run the server
        logger.info("Starting Jenkins MCP Server...")
        asyncio.run(server.main())

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=args.verbose)
        sys.exit(1)


# Package metadata
__version__ = "1.0.0"
__all__ = ['main', 'server']