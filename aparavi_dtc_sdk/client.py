# Standard Library
import glob
import json
import mimetypes
import os
import requests
import time

# Third-party
from typing import Optional, Dict, Any, Literal, List, Union
from colorama import Fore, Style, init as colorama_init
from enum import Enum

# Local project imports
from .models import ResultBase
from .exceptions import AparaviError, AuthenticationError, ValidationError, TaskNotFoundError, PipelineError

# Initialize colorama to enable colored terminal output across platforms
colorama_init(autoreset=True)

# Blow away system mimetypes and use pythons
mimetypes.init()


# Enum for predefined pipelines stored as local JSON files
class PredefinedPipelines(str, Enum):
    ADVANCED_PARSER="advanced_parser"
    AUDIO_AND_SUMMARY = "audio_and_summary"
    SIMPLE_AUDIO_TRANSCRIBE = "simple_audio_transcribe"
    SIMPLE_PARSER = "simple_parser"


# Main class that wraps Aparavi DTC API calls
class AparaviClient:
    # Terminal color constants
    COLOR_GREEN = Fore.GREEN
    COLOR_RED = Fore.RED
    COLOR_ORANGE = Fore.YELLOW
    COLOR_RESET = Style.RESET_ALL
    PREFIX = "[Aparavi DTC SDK]"

    def __init__(
        self,
        base_url: Union[str, None],
        api_key: Union[str, None],
        timeout: int = 100,
        logs: Literal["none", "concise", "verbose"] = "concise",
    ):
        """
        Initializes the client with API credentials and optional logging configuration.
        """
        if base_url is None:
            raise ValueError("base_url is a required value.")
        if api_key is None:
            raise ValueError("api_key is a required value.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.logs = logs

        # Create a persistent session for requests
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def _log(self, message: str, color: Optional[str] = None):
        """
        Prints a log message with optional color depending on verbosity.
        """
        if self.logs == "none":
            return
        print(f"{color if color else ''}{self.PREFIX}{self.COLOR_RESET} {message}")

    def _log_request(self, method: str, url: str, params=None, json_data=None):
        """
        Logs outgoing HTTP requests.
        """
        if self.logs == "verbose":
            self._log(f"{method} {url}", self.COLOR_GREEN)
            if params:
                self._log(f"Params: {json.dumps(params, indent=2)}", self.COLOR_GREEN)
            if json_data:
                self._log(f"JSON: {json.dumps(json_data, indent=2)}", self.COLOR_GREEN)
        elif self.logs == "concise":
            endpoint = url.replace(self.base_url, "")
            self._log(f"{method} {endpoint}", self.COLOR_GREEN)

    def _log_response(self, status_code: int, response_json: Optional[Dict[str, Any]]):
        """
        Logs the HTTP response status and JSON.
        """
        is_success = status_code < 400
        color = self.COLOR_GREEN if is_success else self.COLOR_RED
        self._log(f"Status: {status_code}", color)

        if self.logs == "verbose" and response_json:
            self._log(f"Response JSON:\n{json.dumps(response_json, indent=2)}", color)
        elif self.logs == "concise" and response_json and response_json.get("error"):
            error_msg = response_json["error"]
            if isinstance(error_msg, (dict, list)):
                error_msg = json.dumps(error_msg)
            self._log(f"Error: {error_msg}", self.COLOR_RED)

    def _wrap_pipeline_payload(self, pipeline: Union[Dict[str, Any], None]) -> Dict[str, Any]:
        """
        Ensures the pipeline payload has the required structure.
        """
        if pipeline is None:
            raise AparaviError("Pipeline is missing.")
        if "pipeline" in pipeline:
            pipeline.setdefault("errors", [])
            pipeline.setdefault("warnings", [])
            return pipeline
        return {
            "pipeline": pipeline,
            "errors": [],
            "warnings": []
        }

    def _parse_result(self, response: Dict[str, Any]) -> ResultBase:
        """
        Wraps the raw API response into a structured ResultBase object.
        """
        return ResultBase(
            status=response["status"],
            data=response.get("data"),
            error=response.get("error"),
            metrics=response.get("metrics"),
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Sends an HTTP request and handles errors and logging.
        """
        url = f"{self.base_url}{endpoint}"
        params = kwargs.get("params")
        json_data = kwargs.get("json")

        self._log_request(method, url, params=params, json_data=json_data)

        try:
            response = self.session.request(method=method, url=url, timeout=self.timeout, **kwargs)
            try:
                response_json = response.json()
            except Exception:
                response_json = None

            if response_json is None:
                raise AparaviError("Response did not return valid JSON")

            self._log_response(response.status_code, response_json)

            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or authentication failed")
            elif response.status_code == 422:
                raise ValidationError(f"Validation error: {response.text}")
            elif response.status_code >= 400:
                raise AparaviError(f"API error {response.status_code}: {response.text}")

            return response_json

        except requests.exceptions.RequestException as e:
            raise AparaviError(f"Request failed: {str(e)}")

    def _resolve_pipeline(
        self,
        pipeline_input: Union[str, PredefinedPipelines, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Resolves the pipeline input into a dictionary. Accepts:
        - A dict (returned as-is)
        - A PredefinedPipeline enum (loads from internal pipelines dir)
        - A string path to a JSON file (relative or absolute)
        """
        if isinstance(pipeline_input, dict):
            return pipeline_input

        # Resolve predefined enum
        elif isinstance(pipeline_input, PredefinedPipelines):
            filename = f"{pipeline_input.value}.json"
            pipeline_path = os.path.join(os.path.dirname(__file__), "pipelines", filename)

        # Resolve string path
        elif isinstance(pipeline_input, str):
            abs_path = os.path.abspath(pipeline_input)
            if os.path.exists(abs_path):
                pipeline_path = abs_path
            else:
                # Fall back to internal pipelines dir if not found on filesystem
                pipeline_path = os.path.join(os.path.dirname(__file__), "pipelines", pipeline_input)

        else:
            self._log("Invalid pipeline input type", self.COLOR_RED)
            return None

        if not os.path.exists(pipeline_path):
            self._log(f"Pipeline definition not found: {pipeline_path}", self.COLOR_RED)
            return None

        try:
            with open(pipeline_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self._log(f"Failed to read pipeline file: {e}", self.COLOR_RED)
            return None

    def get_version(self) -> ResultBase:
        """
        Fetch the current version of the API or backend service.
        """
        response = self._make_request("GET", "/version")
        return self._parse_result(response)

    def validate_pipeline(self, pipeline: Union[Dict[str, Any], None]) -> ResultBase:
        """
        Validates a pipeline against the Aparavi backend.
        """
        payload = self._wrap_pipeline_payload(pipeline)
        response = self._make_request("POST", "/pipe/validate", json=payload)
        result = self._parse_result(response)

        if result.status == "Error":
            raise PipelineError(f"Pipeline validation failed: {result.error}")

        return result

    def execute_pipeline(self, pipeline: Union[str, PredefinedPipelines, Dict[str, Any]], name=None, threads=None) -> ResultBase:
        """
        Starts a pipeline execution task.
        """
        resolved_pipeline = self._resolve_pipeline(pipeline)
        if not pipeline:
            raise AparaviError("Invalid pipeline input")

        params = {}
        if name:
            params["name"] = name
        if threads:
            if not 1 <= threads <= 16:
                raise ValueError("Threads must be between 1 and 16")
            params["threads"] = threads

        payload = self._wrap_pipeline_payload(resolved_pipeline)
        response = self._make_request("PUT", "/task", json=payload, params=params)
        result = self._parse_result(response)

        if result.status == "Error":
            raise AparaviError(f"Task execution failed: {result.error}")

        return result

    def get_pipeline_status(self, token: str, task_type: str) -> ResultBase:
        """
        Fetches the current status of an executing pipeline.
        """
        response = self._make_request("GET", "/task", params={"token": token, "type": task_type})
        result = self._parse_result(response)

        if result.status == "Error":
            if "not found" in str(result.error).lower():
                raise TaskNotFoundError(f"Task not found: {result.error}")
            raise AparaviError(f"Failed to get task status: {result.error}")

        return result

    def send_payload_to_webhook(self, token: str, task_type: Literal["gpu", "cpu"], file_glob: str) -> List[Dict[str, Any]]:
        """
        Uploads files to a running webhook pipeline task.
        """
        file_paths = glob.glob(file_glob)
        if not file_paths:
            raise ValueError(f"No files matched pattern: {file_glob}")

        webhook_url = f"{self.base_url}/webhook"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        responses = []

        try:
            # Multipart upload for multiple files
            if len(file_paths) > 1:
                files_to_upload = []
                for file_path in file_paths:
                    with open(file_path, "rb") as f:
                        file_buffer = f.read()
                    filename = os.path.basename(file_path)
                    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                    files_to_upload.append(("files", (filename, file_buffer, content_type)))

                self._log(f"Uploading {len(files_to_upload)} files to webhook (multipart)", self.COLOR_GREEN)

                response = requests.put(
                    webhook_url,
                    params={"token": token, "type": task_type},
                    headers=headers,
                    files=files_to_upload,
                    timeout=self.timeout,
                )

            # Single file upload
            else:
                file_path = file_paths[0]
                with open(file_path, "rb") as f:
                    file_buffer = f.read()
                filename = os.path.basename(file_path)
                content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

                self._log(f"Uploading single file to webhook: {filename}", self.COLOR_GREEN)

                headers.update({
                    "Content-Type": content_type,
                    "Content-Disposition": f'attachment; filename="{filename}"',
                })

                response = requests.put(
                    webhook_url,
                    params={"token": token, "type": task_type},
                    headers=headers,
                    data=file_buffer,
                    timeout=self.timeout,
                )

            response.raise_for_status()
            response_json = response.json()
            responses.append(response_json)

            if self.logs == "verbose":
                self._log(f"Webhook response:\n{json.dumps(response_json, indent=2)}", self.COLOR_GREEN)

            return responses

        except requests.exceptions.RequestException as e:
            if e.response:
                raise AparaviError(f"Webhook failed: Server responded with status {e.response.status_code} - {e.response.text}")
            raise AparaviError(f"Error sending to webhook: {e}")

    def teardown_pipeline(self, token: str, task_type: Literal["gpu", "cpu"]) -> ResultBase:
        """
        Gracefully ends an active task using the token and type.
        """
        response = self._make_request("DELETE", "/task", params={"token": token, "type": task_type})
        result = self._parse_result(response)

        if result.status == "Error":
            if "not found" in str(result.error).lower():
                raise TaskNotFoundError(f"Task not found: {result.error}")
            raise AparaviError(f"Failed to end task: {result.error}")

        return result

    def execute_pipeline_workflow(
        self,
        pipeline: Union[str, PredefinedPipelines, Dict[str, Any]],
        file_glob: Optional[str] = None,
        task_name: Optional[str] = "my-task",
        poll_interval: int = 15,
        max_attempts: int = 1000
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Full lifecycle execution of a pipeline including webhook support.
        Accepts a pipeline dict, a predefined pipeline enum, or a path to a pipeline JSON file.
        """
        # Resolve the pipeline object from input
        resolved_pipeline = self._resolve_pipeline(pipeline)
        if resolved_pipeline is None:
            self._log("Pipeline could not be resolved.", self.COLOR_RED)
            return None

        # Step 1: Validate the pipeline
        try:
            result = self.validate_pipeline(resolved_pipeline)
            self._log(f"Pipeline validation: {result.status}", self.COLOR_GREEN)
        except Exception as e:
            self._log(f"Validation failed: {e}", self.COLOR_RED)
            return None

        token = None
        task_type = None
        # Step 2: Execute pipeline
        try:
            task_result = self.execute_pipeline(resolved_pipeline, name=task_name)
            if task_result.status != "OK":
                raise Exception(f"Task failed to start: {task_result.error}")

            if task_result.data is not None:
                token = task_result.data["token"]
                task_type = task_result.data["type"]
                self._log(f"Task token: {token}", self.COLOR_GREEN)
            else:
                raise AparaviError("Response did not return valid JSON")

            # Check if webhook-based pipeline
            is_webhook = resolved_pipeline.get("source", "").startswith("webhook") if isinstance(resolved_pipeline.get("source"), str) else False

            if is_webhook:
                self._log("Webhook pipeline detected. Polling until task is running...", self.COLOR_GREEN)
                if not file_glob:
                    raise ValueError("file_glob must be provided for webhook pipelines")

                try:
                    for attempt in range(max_attempts):
                        status_result = self.get_pipeline_status(token, task_type)
                        self._log(f"Task Status: [Attempt {attempt + 1}] {status_result.status}", self.COLOR_GREEN)
                        if status_result.data and status_result.data.get("status") == "Running":
                            break
                        time.sleep(poll_interval)

                except KeyboardInterrupt:
                    raise AparaviError("Interrupted by user.") 

                except:
                    raise TimeoutError("Task never entered 'Running' state.")

                self._log("Webhook task is running. Sending files...", self.COLOR_GREEN)

                responses = self.send_payload_to_webhook(token, task_type, file_glob)

                final_status = self.get_pipeline_status(token, task_type)
                self._log(f"Final Task status: {final_status.status}", self.COLOR_GREEN)

                end_result = self.teardown_pipeline(token, task_type)
                self._log(f"Task ended: {end_result.status}", self.COLOR_GREEN)

                return responses

            else:
                # Standard CPU/GPU pipeline
                final_status = self.get_pipeline_status(token, task_type)
                self._log(f"Final Task status: {final_status.status}", self.COLOR_GREEN)

                end_result = self.teardown_pipeline(token, task_type)
                self._log(f"Task ended: {end_result.status}", self.COLOR_GREEN)

                return final_status.data

        except Exception as e:
            self._log(f"Task operation failed: {e}", self.COLOR_RED)
            return None

        finally:
            if token and task_type:
                try:
                    end_result = self.teardown_pipeline(token, task_type)
                    self._log(f"Task ended: {end_result.status}", self.COLOR_GREEN)
                except Exception as e:
                    self._log(f"Failed to teardown task: {e}", self.COLOR_RED)

