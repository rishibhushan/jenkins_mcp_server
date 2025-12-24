"""Version management - reads from package.json"""
import json
import os
from pathlib import Path


def get_version() -> str:
    """
    Read version from package.json.
    Falls back to a default if package.json is not found.
    """
    try:
        # Get the project root (3 levels up from this file)
        # src/jenkins_mcp_server/version.py -> project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        package_json_path = project_root / "package.json"

        if package_json_path.exists():
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                return package_data.get('version', '0.0.0')
        else:
            # Fallback if package.json not found
            return '0.0.0'

    except Exception:
        # If anything goes wrong, return a safe default
        return '0.0.0'


# Module-level constant
__version__ = get_version()