"""
Jenkins MCP Server Client Module

Provides a clean interface to Jenkins API operations with automatic fallback
between python-jenkins library and direct REST API calls.

Enhanced with configurable timeout support.
"""

import logging
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import jenkins
import requests
import urllib3
from requests.auth import HTTPBasicAuth

from .config import JenkinsSettings, get_default_settings

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logger = logging.getLogger(__name__)


class JenkinsConnectionError(Exception):
    """Raised when unable to connect to Jenkins"""
    pass


class JenkinsClient:
    """
    Client for interacting with Jenkins API.

    Supports both python-jenkins library and direct REST API calls
    with automatic fallback for reliability. Enhanced with configurable
    timeout support.
    """

    def __init__(self, settings: Optional[JenkinsSettings] = None, test_connection: bool = False):
        """
        Initialize Jenkins client.

        Args:
            settings: JenkinsSettings instance. If None, uses default settings.
            test_connection: If True, test connection during initialization.
                            Set to False for MCP list_resources to avoid blocking.

        Raises:
            JenkinsConnectionError: If unable to connect to Jenkins
            ValueError: If required settings are missing
        """
        self.settings = settings or get_default_settings()

        # Validate required settings
        if not self.settings.is_configured:
            raise ValueError(
                "Jenkins settings incomplete. Required: url, username, and (token or password)"
            )

        self.base_url = self.settings.url
        username, auth_value = self.settings.get_credentials()
        self.auth = HTTPBasicAuth(username, auth_value)

        # Store timeout settings (High Priority Issue #4)
        self.timeout = self.settings.timeout
        self.connect_timeout = self.settings.connect_timeout
        self.read_timeout = self.settings.read_timeout
        self.verify_ssl = self.settings.verify_ssl

        # Cache for python-jenkins server instance
        self._server: Optional[jenkins.Jenkins] = None

        # Only test connection if explicitly requested
        # This prevents blocking during MCP initialization
        if test_connection:
            self._test_connection()

    def _test_connection(self) -> None:
        """Test connection to Jenkins server (with configurable timeout)"""
        try:
            # Quick connection test with configured timeout for MCP compatibility
            response = requests.get(
                f"{self.base_url}/api/json",
                auth=self.auth,
                verify=self.verify_ssl if self.verify_ssl else False,
                timeout=self.connect_timeout  # Use configured connect timeout
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Connected to Jenkins: {self.base_url}")
            logger.debug(f"Jenkins version: {data.get('_class', 'unknown')}")

        except requests.Timeout:
            logger.warning(f"Connection to Jenkins timed out after {self.connect_timeout}s (server may be slow)")
            # Don't fail - let actual operations fail if there's a real problem
        except requests.RequestException as e:
            logger.warning(f"Could not verify Jenkins connection: {e}")
            # Don't fail - let actual operations fail if there's a real problem

    @property
    def server(self) -> jenkins.Jenkins:
        """Get or create python-jenkins server instance (lazy initialization with timeout)"""
        if self._server is None:
            username, password = self.settings.get_credentials()
            self._server = jenkins.Jenkins(
                self.base_url,
                username=username,
                password=password,
                timeout=self.timeout  # Use configured timeout
            )
        return self._server

    def _api_call(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make a direct REST API call to Jenkins with configured timeout.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/job/myjob/api/json')
            **kwargs: Additional arguments for requests

        Returns:
            requests.Response object
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('verify', self.verify_ssl if self.verify_ssl else False)

        # Use configured timeout (can be overridden per call)
        if 'timeout' not in kwargs:
            kwargs['timeout'] = (self.connect_timeout, self.read_timeout)

        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    # ==================== Job Information ====================

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get list of all Jenkins jobs"""
        try:
            return self.server.get_jobs()
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            response = self._api_call('GET', '/api/json')
            return response.json().get('jobs', [])

    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific job"""
        try:
            return self.server.get_job_info(job_name)
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            response = self._api_call('GET', f'/job/{job_name}/api/json')
            return response.json()

    def get_last_build_number(self, job_name: str) -> Optional[int]:
        """Get the last build number for a job"""
        try:
            info = self.get_job_info(job_name)

            # Try lastBuild first
            if info.get('lastBuild') and 'number' in info['lastBuild']:
                return int(info['lastBuild']['number'])

            # Fall back to lastCompletedBuild
            if info.get('lastCompletedBuild') and 'number' in info['lastCompletedBuild']:
                return int(info['lastCompletedBuild']['number'])

            return None
        except Exception as e:
            logger.error(f"Error getting last build number for {job_name}: {e}")
            return None

    def get_last_build_timestamp(self, job_name: str) -> Optional[int]:
        """Get timestamp (ms since epoch) of the last build"""
        try:
            last_num = self.get_last_build_number(job_name)
            if last_num is None:
                return None

            build_info = self.get_build_info(job_name, last_num)
            return build_info.get('timestamp')
        except Exception as e:
            logger.error(f"Error getting last build timestamp for {job_name}: {e}")
            return None

    # ==================== Build Information ====================

    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get information about a specific build"""
        try:
            return self.server.get_build_info(job_name, build_number)
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            response = self._api_call('GET', f'/job/{job_name}/{build_number}/api/json')
            return response.json()

    def get_build_console_output(self, job_name: str, build_number: int) -> str:
        """Get console output from a build (alias for get_build_log)"""
        return self.get_build_log(job_name, build_number)

    def get_build_log(self, job_name: str, build_number: int) -> str:
        """Get console log output from a build"""
        try:
            return self.server.get_build_console_output(job_name, build_number)
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            response = self._api_call('GET', f'/job/{job_name}/{build_number}/consoleText')
            return response.text

    # ==================== Build Operations ====================

    def build_job(
            self,
            job_name: str,
            parameters: Optional[Dict[str, Any]] = None,
            wait_for_start: bool = True,
            timeout: int = 30,
            poll_interval: float = 1.0
    ) -> Dict[str, Optional[int]]:
        """
        Trigger a build and optionally wait for it to start.

        Args:
            job_name: Name of the Jenkins job
            parameters: Optional build parameters
            wait_for_start: Wait for build to start and return build number
            timeout: Maximum seconds to wait for build start
            poll_interval: Seconds between polling attempts

        Returns:
            Dict with 'queue_id' and 'build_number' (if wait_for_start=True)
        """
        # Get the last build number before triggering
        last_build_num = self.get_last_build_number(job_name) or 0

        # Trigger the build
        if parameters:
            self._api_call(
                'POST',
                f'/job/{job_name}/buildWithParameters',
                params=parameters
            )
        else:
            self._api_call('POST', f'/job/{job_name}/build')

        # Get queue ID from response
        queue_id = self._extract_queue_id_from_location(
            f'/job/{job_name}/build'
        )

        result = {
            'queue_id': queue_id,
            'build_number': None
        }

        # Optionally wait for build to start
        if wait_for_start:
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(poll_interval)

                # Check if a new build has started
                current_build_num = self.get_last_build_number(job_name)
                if current_build_num and current_build_num > last_build_num:
                    result['build_number'] = current_build_num
                    logger.info(f"Build {job_name} #{current_build_num} started")
                    break

        return result

    def _extract_queue_id_from_location(self, location: str) -> Optional[int]:
        """Extract queue ID from Location header"""
        if not location:
            return None

        parts = location.rstrip('/').split('/')
        for part in reversed(parts):
            if part.isdigit():
                return int(part)
        return None

    def stop_build(self, job_name: str, build_number: int) -> None:
        """Stop a running build"""
        self._api_call('POST', f'/job/{job_name}/{build_number}/stop')
        logger.info(f"Stopped build {job_name} #{build_number}")

    # ==================== Job Management ====================

    def create_job(self, job_name: str, config_xml: str) -> bool:
        """Create a new Jenkins job with XML configuration"""
        try:
            self.server.create_job(job_name, config_xml)
            self.server.reconfig_job(job_name, config_xml)
            logger.info(f"Created job: {job_name}")
            return True
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            self._api_call(
                'POST',
                '/createItem',
                params={'name': job_name},
                data=config_xml,
                headers={'Content-Type': 'application/xml'}
            )
            logger.info(f"Created job: {job_name}")
            return True

    def create_job_from_copy(self, new_job_name: str, source_job_name: str) -> bool:
        """Create a new job by copying an existing one"""
        # Get source config
        config_xml = self.get_job_config(source_job_name)

        # Update job references in XML
        config_xml = self._update_job_references(config_xml, source_job_name, new_job_name)

        # Create new job
        return self.create_job(new_job_name, config_xml)

    @staticmethod
    def _update_job_references(config_xml: str, old_name: str, new_name: str) -> str:
        """Update job name references in XML configuration"""
        try:
            root = ET.fromstring(config_xml)

            # Update projectName and projectFullName elements
            for elem in root.iter():
                if elem.tag in ['projectName', 'projectFullName'] and elem.text == old_name:
                    elem.text = new_name

            return ET.tostring(root, encoding='unicode', method='xml')
        except Exception as e:
            logger.warning(f"Failed to update job references in XML: {e}")
            return config_xml

    def create_job_from_dict(
            self,
            job_name: str,
            config_data: Dict[str, Any],
            root_tag: str = 'project'
    ) -> bool:
        """
        Create a job from a dictionary (simplified XML generation).

        Note: For complex configurations, use create_job() with full XML
        or create_job_from_copy() instead.
        """
        config_xml = self._dict_to_xml(root_tag, config_data)
        return self.create_job(job_name, config_xml)

    @staticmethod
    def _dict_to_xml(root_tag: str, data: Dict[str, Any]) -> str:
        """Convert dictionary to XML (basic implementation)"""

        def build_elem(parent: ET.Element, obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    child = ET.SubElement(parent, key)
                    build_elem(child, value)
            elif isinstance(obj, list):
                for item in obj:
                    item_el = ET.SubElement(parent, 'item')
                    build_elem(item_el, item)
            else:
                parent.text = str(obj)

        root = ET.Element(root_tag)
        build_elem(root, data)
        return ET.tostring(root, encoding='unicode')

    def delete_job(self, job_name: str) -> bool:
        """Delete an existing job"""
        try:
            self.server.delete_job(job_name)
            logger.info(f"Deleted job: {job_name}")
            return True
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            self._api_call('POST', f'/job/{job_name}/doDelete')
            logger.info(f"Deleted job: {job_name}")
            return True

    def enable_job(self, job_name: str) -> bool:
        """Enable a disabled job"""
        self._api_call('POST', f'/job/{job_name}/enable')
        logger.info(f"Enabled job: {job_name}")
        return True

    def disable_job(self, job_name: str) -> bool:
        """Disable a job"""
        self._api_call('POST', f'/job/{job_name}/disable')
        logger.info(f"Disabled job: {job_name}")
        return True

    def rename_job(self, job_name: str, new_name: str) -> bool:
        """Rename a job"""
        self._api_call(
            'POST',
            f'/job/{job_name}/doRename',
            params={'newName': new_name}
        )
        logger.info(f"Renamed job: {job_name} -> {new_name}")
        return True

    # ==================== Job Configuration ====================

    def get_job_config(self, job_name: str) -> str:
        """Get job configuration XML"""
        try:
            return self.server.get_job_config(job_name)
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            response = self._api_call('GET', f'/job/{job_name}/config.xml')
            return response.text

    def update_job_config(self, job_name: str, config_xml: str) -> bool:
        """Update job configuration XML"""
        try:
            self.server.reconfig_job(job_name, config_xml)
            logger.info(f"Updated config for job: {job_name}")
            return True
        except Exception as e:
            logger.debug(f"python-jenkins failed, using REST API: {e}")
            self._api_call(
                'POST',
                f'/job/{job_name}/config.xml',
                data=config_xml,
                headers={'Content-Type': 'application/xml'}
            )
            logger.info(f"Updated config for job: {job_name}")
            return True

    # ==================== Queue & Node Information ====================

    def get_queue_info(self) -> List[Dict[str, Any]]:
        """Get information about the build queue"""
        try:
            response = self._api_call('GET', '/queue/api/json')
            return response.json().get('items', [])
        except Exception as e:
            logger.error(f"Error getting queue info: {e}")
            return []

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of all Jenkins nodes"""
        try:
            response = self._api_call('GET', '/computer/api/json')
            return response.json().get('computer', [])
        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return []

    def get_node_info(self, node_name: str) -> Dict[str, Any]:
        """Get information about a specific node"""
        response = self._api_call('GET', f'/computer/{node_name}/api/json')
        return response.json()

    # ==================== Additional Helper Methods ====================

    def get_whoami(self) -> Dict[str, Any]:
        """Get information about the current authenticated user"""
        response = self._api_call('GET', '/me/api/json')
        return response.json()

    def get_version(self) -> str:
        """Get Jenkins version"""
        response = self._api_call('GET', '/api/json')
        return response.headers.get('X-Jenkins', 'Unknown')


# ==================== Client Factory ====================

_default_client: Optional[JenkinsClient] = None


def get_jenkins_client(
        settings: Optional[JenkinsSettings] = None,
        test_connection: bool = False
) -> JenkinsClient:
    """
    Get Jenkins client instance.

    Args:
        settings: Optional JenkinsSettings. If None, uses default settings.
        test_connection: If True, test connection during initialization.

    Returns:
        JenkinsClient instance

    Note: If no settings provided, returns a cached default client (singleton).
          If settings are provided, always returns a new client instance.
    """
    global _default_client

    if settings is not None:
        # Always create new client with custom settings
        return JenkinsClient(settings, test_connection=test_connection)

    # Use cached default client
    if _default_client is None:
        _default_client = JenkinsClient(test_connection=test_connection)

    return _default_client
