"""
Jenkins MCP Server Configuration Module

Handles loading Jenkins connection settings from multiple sources:
1. VS Code settings.json (highest priority)
2. Environment variables / .env file
3. Direct instantiation with parameters

Enhanced with timeout configuration support.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .verbose import vprint

# Configure logging
logger = logging.getLogger(__name__)

class JenkinsSettings(BaseSettings):
    """
    Jenkins connection settings with support for multiple configuration sources.

    Priority order:
    1. Directly passed parameters
    2. VS Code settings
    3. Environment variables
    4. .env file
    """

    # Use 'url' as the primary field name, but accept 'jenkins_url' as alias
    url: Optional[str] = Field(
        default=None,
        alias="jenkins_url",
        description="Jenkins server URL (e.g., http://localhost:8080)"
    )
    username: Optional[str] = Field(
        default=None,
        description="Jenkins username"
    )
    password: Optional[str] = Field(
        default=None,
        description="Jenkins password"
    )
    token: Optional[str] = Field(
        default=None,
        description="Jenkins API token (preferred over password)"
    )

    # Timeout settings (High Priority Issue #4)
    timeout: int = Field(
        default=30,
        description="Default timeout for Jenkins API calls in seconds",
        ge=5,
        le=300
    )

    connect_timeout: int = Field(
        default=10,
        description="Connection timeout in seconds",
        ge=2,
        le=60
    )

    read_timeout: int = Field(
        default=30,
        description="Read timeout for API responses in seconds",
        ge=5,
        le=300
    )

    # Retry settings
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed requests",
        ge=0,
        le=10
    )

    # Console output settings (High Priority Issue #5)
    console_max_lines: int = Field(
        default=1000,
        description="Default maximum lines to return from console output",
        ge=10,
        le=50000
    )

    # SSL verification
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates"
    )

    model_config = SettingsConfigDict(
        env_prefix="JENKINS_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,  # Allow both 'url' and 'jenkins_url'
        extra="ignore"
    )

    @field_validator('url')
    @classmethod
    def strip_trailing_slash(cls, v: Optional[str]) -> Optional[str]:
        """Remove trailing slash from URL"""
        if v:
            return v.rstrip('/')
        return v

    @property
    def is_configured(self) -> bool:
        """Check if minimum required settings are present"""
        return bool(self.url and self.username and (self.token or self.password))

    @property
    def auth_method(self) -> str:
        """Return the authentication method being used"""
        if self.token:
            return "API Token"
        elif self.password:
            return "Password"
        return "None"

    def get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Return (username, password/token) tuple for authentication"""
        if self.username:
            auth_value = self.token if self.token else self.password
            return (self.username, auth_value)
        return (None, None)

    def log_config(self, hide_sensitive: bool = True) -> None:
        """Log current configuration (with optional masking of sensitive data)"""
        logger.info("Jenkins Configuration:")
        logger.info(f"  URL: {self.url or 'Not configured'}")
        logger.info(f"  Username: {self.username or 'Not configured'}")
        logger.info(f"  Timeout: {self.timeout}s")
        logger.info(f"  Connect Timeout: {self.connect_timeout}s")
        logger.info(f"  Read Timeout: {self.read_timeout}s")
        logger.info(f"  Max Retries: {self.max_retries}")
        logger.info(f"  Console Max Lines: {self.console_max_lines}")
        logger.info(f"  Verify SSL: {self.verify_ssl}")

        if hide_sensitive:
            logger.info(f"  Authentication: {self.auth_method}")
        else:
            logger.info(f"  Token: {self.token or 'Not set'}")
            logger.info(f"  Password: {self.password or 'Not set'}")


class VSCodeSettingsLoader:
    """Handles loading Jenkins settings from VS Code settings.json files"""

    # Standard VS Code settings paths by platform
    VSCODE_PATHS = [
        # Workspace settings (highest priority if exists)
        Path.cwd() / ".vscode/settings.json",
        # User settings (platform-specific)
        Path.home() / "Library/Application Support/Code/User/settings.json",  # macOS
        Path.home() / "Library/Application Support/Code - Insiders/User/settings.json",
        Path.home() / ".config/Code/User/settings.json",  # Linux
        Path.home() / ".config/Code - Insiders/User/settings.json",
        Path.home() / "AppData/Roaming/Code/User/settings.json",  # Windows
        Path.home() / "AppData/Roaming/Code - Insiders/User/settings.json",
    ]

    @staticmethod
    def parse_jsonc(content: str) -> Dict[str, Any]:
        """
        Parse JSON with comments (JSONC).

        Removes single-line (//) and multi-line (/* */) comments before parsing.
        """
        if not content or not content.strip():
            return {}

        try:
            # Try direct JSON parse first (fastest path)
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Remove comments
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Clean up trailing commas (common JSONC pattern)
        content = re.sub(r',(\s*[}\]])', r'\1', content)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSONC: {e}")
            return {}

    @classmethod
    def find_jenkins_settings(cls, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Jenkins settings from VS Code settings dictionary.

        Supports two configuration patterns:
        1. "jenkins-mcp-server": { "jenkins": {...} }
        2. "mcp": { "servers": { "jenkins-mcp-server": { "jenkinsConfig": {...} } } }
        """
        # Pattern 1: Direct jenkins-mcp-server.jenkins
        jenkins_config = settings.get("jenkins-mcp-server", {}).get("jenkins", {})
        if jenkins_config:
            return jenkins_config

        # Pattern 2: MCP servers configuration
        mcp_config = (
            settings.get("mcp", {})
            .get("servers", {})
            .get("jenkins-mcp-server", {})
            .get("jenkinsConfig", {})
        )
        if mcp_config:
            return mcp_config

        return None

    @classmethod
    def load(cls) -> Optional[Dict[str, Any]]:
        """
        Load Jenkins settings from VS Code settings files.

        Returns the first valid configuration found, or None.
        """
        for settings_path in cls.VSCODE_PATHS:
            if not settings_path.exists():
                continue

            try:
                logger.debug(f"Checking VS Code settings: {settings_path}")
                content = settings_path.read_text(encoding='utf-8')
                settings = cls.parse_jsonc(content)

                jenkins_settings = cls.find_jenkins_settings(settings)
                if jenkins_settings:
                    logger.info(f"Loaded Jenkins settings from: {settings_path}")
                    return jenkins_settings

            except Exception as e:
                logger.debug(f"Error reading {settings_path}: {e}")
                continue

        logger.debug("No Jenkins settings found in VS Code configuration")
        return None


def load_settings(
        env_file: Optional[str] = None,
        load_vscode: bool = True,
        **override_values
) -> JenkinsSettings:
    """
    Load Jenkins settings from all available sources.

    Args:
        env_file: Optional path to .env file (overrides default .env)
        load_vscode: Whether to load from VS Code settings (default: True)
        **override_values: Direct override values (highest priority)

    Priority order:
        1. override_values (passed as kwargs)
        2. VS Code settings (if load_vscode=True)
        3. Environment variables / .env file

    Returns:
        JenkinsSettings instance with merged configuration
    """
    vprint(f"=== config.load_settings called: env_file={env_file}, load_vscode={load_vscode} ===")

    # Start with environment variables and .env file
    if env_file:
        vprint(f"=== Using custom env file: {env_file} ===")
        settings = JenkinsSettings(_env_file=env_file)
    else:
        vprint("=== Using default .env ===")
        settings = JenkinsSettings()

    vprint(f"=== Initial settings: url={settings.url} ===")

    # Override with VS Code settings if requested
    if load_vscode:
        vprint("=== Loading VS Code settings ===")
        vscode_settings = VSCodeSettingsLoader.load()
        vprint(f"=== VS Code settings loaded: {vscode_settings is not None} ===")
        if vscode_settings:
            # Merge VS Code settings into our settings object
            for key in ['url', 'username', 'password', 'token', 'timeout', 'connect_timeout',
                        'read_timeout', 'max_retries', 'console_max_lines', 'verify_ssl']:
                vscode_value = vscode_settings.get(key)
                if vscode_value is not None:
                    setattr(settings, key, vscode_value)

    # Apply direct overrides (highest priority)
    vprint("=== Applying overrides ===")
    for key, value in override_values.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)

    # Log final configuration
    vprint(f"=== Final settings: url={settings.url}, configured={settings.is_configured} ===")
    settings.log_config()

    return settings


# Factory function for backward compatibility
def get_settings(
        env_file: Optional[str] = None,
        load_vscode: bool = True,
        **kwargs
) -> JenkinsSettings:
    """
    Get Jenkins settings instance.

    This is the recommended way to obtain settings in the application.
    Each call returns a fresh instance with current configuration.
    """
    return load_settings(env_file=env_file, load_vscode=load_vscode, **kwargs)


# For backward compatibility with code that expects a global settings object
# Note: This is lazily evaluated when first accessed
_default_settings: Optional[JenkinsSettings] = None


def get_default_settings() -> JenkinsSettings:
    """Get or create the default settings instance (singleton pattern)"""
    global _default_settings
    if _default_settings is None:
        _default_settings = load_settings()
    return _default_settings
