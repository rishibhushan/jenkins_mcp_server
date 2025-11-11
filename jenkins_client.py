from typing import Dict, List, Optional, Any

import requests
import jenkins
from requests.auth import HTTPBasicAuth

from .config import jenkins_settings


class JenkinsClient:
    """Client for interacting with Jenkins API."""

    def __init__(self):
        """Initialize the Jenkins client using configuration settings."""
        try:
            # Disable SSL verification warnings
            import urllib3
            urllib3.disable_warnings()

            if jenkins_settings.username and jenkins_settings.token:
                print(f"Using API token authentication for user {jenkins_settings.username}")
                self.auth = HTTPBasicAuth(jenkins_settings.username, jenkins_settings.token)
                self.base_url = jenkins_settings.jenkins_url.rstrip('/')

                # Test connection
                print("\nTesting connection with direct request...")
                response = requests.get(f"{self.base_url}/api/json",
                                        auth=self.auth,
                                        verify=False)
                print(f"Direct request status: {response.status_code}")

                if response.ok:
                    print("Direct API call successful!")
                    data = response.json()
                    print(f"Server version: {data.get('_class', 'unknown')}")

                    # Store the initial jobs data
                    self._jobs = data.get('jobs', [])
                    print(f"Found {len(self._jobs)} jobs:")
                    # for job in self._jobs:
                    #     print(f"- {job['name']} ({job.get('color', 'unknown')})")
                else:
                    print(f"Direct API call failed: {response.text}")
                    raise Exception("Failed to connect to Jenkins")
            else:
                raise ValueError("Username and token are required")

        except Exception as e:
            print(f"\nError connecting to Jenkins: {str(e)}")
            print("\nPlease check:")
            print(f"1. Jenkins server is running at {jenkins_settings.jenkins_url}")
            print("2. Your credentials in .env file are correct")
            print("3. You have proper permissions in Jenkins")
            import traceback
            traceback.print_exc()
            raise

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get a list of all Jenkins jobs (prefer python-jenkins)."""
        try:
            server = self._make_jenkins_server()
            # python-jenkins returns a list of jobs with 'name' and 'url'
            jobs = server.get_jobs()
            return jobs
        except Exception:
            # fallback to requests-based implementation
            try:
                response = requests.get(f"{self.base_url}/api/json",
                                        auth=self.auth,
                                        verify=False)
                response.raise_for_status()
                return response.json().get('jobs', [])
            except Exception as e:
                print(f"Error getting Jenkins jobs: {str(e)}")
                return []

    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific job (prefer python-jenkins)."""
        try:
            server = self._make_jenkins_server()
            return server.get_job_info(job_name)
        except Exception:
            try:
                response = requests.get(f"{self.base_url}/job/{job_name}/api/json",
                                        auth=self.auth,
                                        verify=False)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error getting job info for {job_name}: {str(e)}")
                raise

    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get information about a specific build (prefer python-jenkins)."""
        try:
            server = self._make_jenkins_server()
            return server.get_build_info(job_name, build_number)
        except Exception:
            try:
                response = requests.get(f"{self.base_url}/job/{job_name}/{build_number}/api/json",
                                        auth=self.auth,
                                        verify=False)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error getting build info for {job_name} #{build_number}: {str(e)}")
                raise

    def get_build_console_output(self, job_name: str, build_number: int) -> str:
        """Get console output from a build (prefer python-jenkins)."""
        try:
            server = self._make_jenkins_server()
            return server.get_build_console_output(job_name, build_number)
        except Exception:
            try:
                response = requests.get(f"{self.base_url}/job/{job_name}/{build_number}/consoleText",
                                        auth=self.auth,
                                        verify=False)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"Error getting build console for {job_name} #{build_number}: {str(e)}")
                raise

    def build_job(self, job_name: str, parameters: Optional[Dict[str, Any]] = None, wait_for_build: bool = True,
                  timeout: int = 30, poll_interval: float = 1.0) -> Dict[str, Optional[int]]:
        """
        Trigger a build for a job and return both queue_id and build_number (if available).

        Parameters:
        - job_name: Jenkins job name
        - parameters: optional build parameters dict
        - wait_for_build: if True, poll the queue until the build starts and return the build number
        - timeout: maximum seconds to wait when waiting for build_number
        - poll_interval: seconds between poll attempts

        Returns a dict: { "queue_id": int or None, "build_number": int or None }
        """
        try:
            server = self._make_jenkins_server()
            # python-jenkins returns queue id when scheduling a build
            if parameters:
                q = server.build_job(job_name, parameters)
            else:
                q = server.build_job(job_name)
            queue_id = int(q) if q is not None else None

            build_number = None
            if wait_for_build and queue_id is not None:
                # Poll until queue item has an 'executable' -> contains build number
                elapsed = 0.0
                while elapsed < timeout:
                    try:
                        item = server.get_queue_item(queue_id)
                        if item is None:
                            # Sleep and continue if item not present yet
                            import time
                            time.sleep(poll_interval)
                            elapsed += poll_interval
                            continue
                        if 'executable' in item and item['executable']:
                            build_number = int(item['executable']['number'])
                            break
                    except Exception:
                        # If python-jenkins fails to fetch queue item, try fallback via requests
                        try:
                            import time
                            resp = requests.get(f"{self.base_url}/queue/item/{queue_id}/api/json", auth=self.auth,
                                                verify=False)
                            if resp.ok:
                                j = resp.json()
                                if 'executable' in j and j['executable']:
                                    build_number = int(j['executable']['number'])
                                    break
                        except Exception:
                            pass
                    import time
                    time.sleep(poll_interval)
                    elapsed += poll_interval

            return {"queue_id": queue_id, "build_number": build_number}
        except Exception:
            # fallback to requests-based implementation
            try:
                url = f"{self.base_url}/job/{job_name}/build"
                if parameters:
                    url = f"{self.base_url}/job/{job_name}/buildWithParameters"
                response = requests.post(url,
                                         auth=self.auth,
                                         params=parameters,
                                         verify=False)
                response.raise_for_status()
                location = response.headers.get('Location', '') or response.headers.get('location', '')
                queue_id = None
                if location:
                    # Location header often contains /queue/item/<id>/ or /queue/<id>/
                    parts = location.rstrip('/').split('/')
                    for p in reversed(parts):
                        if p.isdigit():
                            queue_id = int(p)
                            break

                build_number = None
                if wait_for_build and queue_id is not None:
                    elapsed = 0.0
                    import time
                    while elapsed < timeout:
                        try:
                            resp = requests.get(f"{self.base_url}/queue/item/{queue_id}/api/json", auth=self.auth,
                                                verify=False)
                            if resp.ok:
                                j = resp.json()
                                if 'executable' in j and j['executable']:
                                    build_number = int(j['executable']['number'])
                                    break
                        except Exception:
                            pass
                        time.sleep(poll_interval)
                        elapsed += poll_interval

                return {"queue_id": queue_id, "build_number": build_number}
            except Exception as e:
                print(f"Error triggering build for {job_name}: {str(e)}")
                raise

    def stop_build(self, job_name: str, build_number: int) -> None:
        """Stop a running build."""
        try:
            response = requests.post(f"{self.base_url}/job/{job_name}/{build_number}/stop",
                                     auth=self.auth,
                                     verify=False)
            response.raise_for_status()
        except Exception as e:
            print(f"Error stopping build {job_name} #{build_number}: {str(e)}")
            raise

    def get_queue_info(self) -> List[Dict[str, Any]]:
        """Get information about the queue."""
        try:
            response = requests.get(f"{self.base_url}/queue/api/json",
                                    auth=self.auth,
                                    verify=False)
            response.raise_for_status()
            return response.json().get('items', [])
        except Exception as e:
            print(f"Error getting queue info: {str(e)}")
            return []

    def get_node_info(self, node_name: str) -> Dict[str, Any]:
        """Get information about a specific node."""
        try:
            response = requests.get(f"{self.base_url}/computer/{node_name}/api/json",
                                    auth=self.auth,
                                    verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting node info for {node_name}: {str(e)}")
            raise

    def get_nodes(self) -> List[Dict[str, str]]:
        """Get a list of all nodes."""
        try:
            response = requests.get(f"{self.base_url}/computer/api/json",
                                    auth=self.auth,
                                    verify=False)
            response.raise_for_status()
            return response.json().get('computer', [])
        except Exception as e:
            print(f"Error getting nodes: {str(e)}")
            return []

    # ----------------------------------------------------
    # --- Job Management & Configuration methods added ---
    # ----------------------------------------------------

    def create_job(self, job_name: str, config_xml: str) -> bool:
        """Create a new Jenkins job with given config XML (prefer python-jenkins)."""
        try:
            server = self._make_jenkins_server()
            server.create_job(job_name, config_xml)
            # Ensure job saved/configured
            server.reconfig_job(job_name, config_xml)
            return True
        except Exception:
            try:
                headers = {"Content-Type": "application/xml"}
                params = {"name": job_name}
                response = requests.post(f"{self.base_url}/createItem", params=params,
                                         data=config_xml, headers=headers, auth=self.auth, verify=False)
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"Error creating job {job_name}: {e}")
                raise

    def create_job_from_copy(self, new_job_name: str, source_job_name: str) -> bool:
        """Create a new Jenkins job by copying an existing job."""

        try:
            # Extract username and password from self.auth
            # Assuming self.auth is HTTPBasicAuth(username, password)
            if hasattr(self.auth, 'username') and hasattr(self.auth, 'password'):
                username = self.auth.username
                password = self.auth.password
            elif isinstance(self.auth, tuple):
                # If self.auth is a tuple (username, password)
                username, password = self.auth
            else:
                raise ValueError("Unable to extract credentials from self.auth")

            # Create Jenkins server connection
            server = jenkins.Jenkins(
                self.base_url,
                username=username,
                password=password
            )

            # Get source config
            config_xml = server.get_job_config(source_job_name)

            # Fix the uno-choice plugin references
            import xml.etree.ElementTree as ET
            root = ET.fromstring(config_xml)

            # Update projectName and projectFullName references
            for elem in root.iter():
                if elem.tag in ['projectName', 'projectFullName']:
                    if elem.text == source_job_name:
                        elem.text = new_job_name

            # Convert back to string
            fixed_xml = ET.tostring(root, encoding='unicode', method='xml')

            # Create new job with fixed config
            server.create_job(new_job_name, fixed_xml)

            print(f"Successfully created job: {new_job_name}")
            return True

        except Exception as e:
            print(f"Failed to create job from copy: {e}")
            raise

    def create_job_from_dict(self, job_name: str, config_data: dict, root_tag: str = 'project') -> bool:
        """Create a new Jenkins job by constructing a simple XML from a dict.

        Parameters
        - job_name: name of the new job
        - config_data: a dict containing the desired XML structure under `root_tag`
        - root_tag: top-level element name for the Jenkins job XML (default: 'project')

        Note: This helper builds basic XML. Complex Jenkins job configurations
        may not be correctly represented by an automatic conversion. Prefer
        using `create_job` with full `config_xml` or `create_job_from_copy`.
        """
        try:
            config_xml = self._dict_to_xml(root_tag, config_data)
            return self.create_job(job_name, config_xml)
        except Exception as e:
            print(f"Error creating job {job_name} from dict: {e}")
            raise

    def _dict_to_xml(self, root_tag: str, data: dict) -> str:
        """Convert a simple dict into an XML string with the given root tag.

        This is a lightweight helper intended for basic use-cases. Jenkins
        job config XML is complex; for full control prefer providing
        `config_xml` directly or copying an existing job.
        """
        try:
            from xml.etree.ElementTree import Element, tostring
            def _build_elem(parent, obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        child = Element(k)
                        parent.append(child)
                        _build_elem(child, v)
                elif isinstance(obj, list):
                    for item in obj:
                        item_el = Element('item')
                        parent.append(item_el)
                        _build_elem(item_el, item)
                else:
                    parent.text = str(obj)

            root = Element(root_tag)
            _build_elem(root, data)
            # tostring returns bytes in py3; decode to str
            xml_bytes = tostring(root, encoding='utf-8')
            return xml_bytes.decode('utf-8')
        except Exception as e:
            print(f"Error converting dict to XML: {e}")
            raise

    def delete_job(self, job_name: str) -> bool:
        """Delete an existing Jenkins job (prefer python-jenkins)."""
        try:
            server = self._make_jenkins_server()
            server.delete_job(job_name)
            return True
        except Exception:
            try:
                response = requests.post(f"{self.base_url}/job/{job_name}/doDelete",
                                         auth=self.auth, verify=False)
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"Error deleting job {job_name}: {e}")
                raise

    def enable_job(self, job_name: str) -> bool:
        """Enable a disabled Jenkins job."""
        try:
            response = requests.post(f"{self.base_url}/job/{job_name}/enable",
                                     auth=self.auth, verify=False)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error enabling job {job_name}: {e}")
            raise

    def disable_job(self, job_name: str) -> bool:
        """Disable an enabled Jenkins job."""
        try:
            response = requests.post(f"{self.base_url}/job/{job_name}/disable",
                                     auth=self.auth, verify=False)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error disabling job {job_name}: {e}")
            raise

    def rename_job(self, job_name: str, new_name: str) -> bool:
        """Rename an existing Jenkins job."""
        try:
            params = {"newName": new_name}
            response = requests.post(f"{self.base_url}/job/{job_name}/doRename", params=params,
                                     auth=self.auth, verify=False)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error renaming job {job_name} to {new_name}: {e}")
            raise

    def get_job_config(self, job_name: str) -> str:
        """Get the job's configuration XML (prefer python-jenkins)."""
        try:
            server = self._make_jenkins_server()
            return server.get_job_config(job_name)
        except Exception:
            try:
                response = requests.get(f"{self.base_url}/job/{job_name}/config.xml",
                                        auth=self.auth, verify=False)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"Error getting config for job {job_name}: {e}")
                raise

    def update_job_config(self, job_name: str, config_xml: str) -> bool:
        """Update the job's configuration XML (prefer python-jenkins reconfig)."""
        try:
            server = self._make_jenkins_server()
            server.reconfig_job(job_name, config_xml)
            return True
        except Exception:
            try:
                headers = {"Content-Type": "application/xml"}
                response = requests.post(f"{self.base_url}/job/{job_name}/config.xml",
                                         data=config_xml, headers=headers, auth=self.auth, verify=False)
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"Error updating config for job {job_name}: {e}")
                raise

    def get_last_build_number(self, job_name: str) -> Optional[int]:
        """Return last build number for a job, or None."""
        try:
            server = self._make_jenkins_server()
            info = server.get_job_info(job_name)
            last = info.get('lastBuild')
            if last and 'number' in last:
                return int(last['number'])
            lastc = info.get('lastCompletedBuild')
            if lastc and 'number' in lastc:
                return int(lastc['number'])
            return None
        except Exception:
            try:
                info = self.get_job_info(job_name)
                last = info.get('lastBuild')
                if last and 'number' in last:
                    return int(last['number'])
                lastc = info.get('lastCompletedBuild')
                if lastc and 'number' in lastc:
                    return int(lastc['number'])
                return None
            except Exception as e:
                print(f"Error getting last build number for {job_name}: {e}")
                return None

    def get_last_build_timestamp(self, job_name: str) -> Optional[int]:
        """Return timestamp (ms since epoch) of last build, or None."""
        try:
            last_num = self.get_last_build_number(job_name)
            if last_num is None:
                return None
            server = self._make_jenkins_server()
            info = server.get_build_info(job_name, last_num)
            return info.get('timestamp')
        except Exception:
            try:
                info = self.get_build_info(job_name, self.get_last_build_number(job_name))
                return info.get('timestamp')
            except Exception as e:
                print(f"Error getting last build timestamp for {job_name}: {e}")
                return None

    def _make_jenkins_server(self):
        """Return a python-jenkins Jenkins instance for higher-level operations.

        Caches the server instance on the client object for reuse.
        """
        if getattr(self, '_jenkins_server', None) is None:
            # extract credentials from self.auth
            username = None
            password = None
            if hasattr(self.auth, 'username') and hasattr(self.auth, 'password'):
                username = self.auth.username
                password = self.auth.password
            elif isinstance(self.auth, tuple):
                username, password = self.auth
            # create python-jenkins Jenkins object
            self._jenkins_server = jenkins.Jenkins(self.base_url, username=username, password=password)
        return self._jenkins_server


# Create a singleton instance
# Replace eager instantiation with a lazy factory
jenkins_client = None


def get_jenkins_client() -> JenkinsClient:
    """Return a shared JenkinsClient, creating it when first requested."""
    global jenkins_client
    if jenkins_client is None:
        jenkins_client = JenkinsClient()
    return jenkins_client
