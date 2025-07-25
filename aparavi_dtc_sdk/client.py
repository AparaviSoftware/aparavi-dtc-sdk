# Standrd
import json
import glob
import mimetypes
import os
import time
import requests
# Third Party
from typing import Optional, Dict, Any, Literal, List, Union
from colorama import Fore, Style, init as colorama_init
from enum import Enum
# Local
from .models import ResultBase
from .exceptions import AparaviError, AuthenticationError, ValidationError, TaskNotFoundError, PipelineError

# Initialize colorama for cross-platform compatibility
colorama_init(autoreset=True)

class PredefinedPipeline(str, Enum):
    SIMPLE_PARSER = "simple_parser"
    SIMPLE_AUDIO_TRANSCRIBE = "simple_audio_transcribe"
    AUDIO_AND_SUMMARY = "audio_and_summary"


class AparaviClient:
    COLOR_GREEN = Fore.GREEN
    COLOR_RED = Fore.RED
    COLOR_ORANGE = Fore.YELLOW
    COLOR_RESET = Style.RESET_ALL
    PREFIX = "[Aparavi DTC SDK]"

    def __init__(
        self,
        base_url: Union[str, None],
        api_key: Union[str, None],
        timeout: int = 30,
        logs: Literal["none", "concise", "verbose"] = "none",
    ):

        if base_url is None:
            raise ValueError("base_url is a required value.")
        if api_key is None:
            raise ValueError("api_key is a required value.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.logs = logs
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def _log(self, message: str, color: Optional[str] = None):
        if self.logs == "none":
            return
        print(f"{color if color else ''}{self.PREFIX}{self.COLOR_RESET} {message}")

    def _log_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ):
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

    def _wrap_pipeline_payload(self, pipeline: Dict[str, Any]) -> Dict[str, Any]:
        if "pipeline" in pipeline:
            # Respect existing values; fill in only if missing
            if "errors" not in pipeline:
                pipeline["errors"] = []
            if "warnings" not in pipeline:
                pipeline["warnings"] = []
            return pipeline

        # Payload format — wrap it
        return {
            "pipeline": pipeline,
            "errors": [],
            "warnings": []
        }

    def _parse_result(self, response: Dict[str, Any]) -> ResultBase:
        return ResultBase(
            status=response["status"],
            data=response.get("data"),
            error=response.get("error"),
            metrics=response.get("metrics"),
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request to the API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            **kwargs: Additional arguments for requests

        Returns:
            Dict containing the API response

        Raises:
            AuthenticationError: If authentication fails
            ValidationError: If validation fails
            AparaviError: For other API errors
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

            if response_json is None:
                raise AparaviError("Response did not return valid JSON")

            return response_json

        except requests.exceptions.RequestException as e:
            raise AparaviError(f"Request failed: {str(e)}")

    def get_version(self) -> ResultBase:
        response = self._make_request(method="GET", endpoint="/version")
        result = self._parse_result(response)
        return result

    def validate_pipeline(self, pipeline: Dict[str, Any]) -> ResultBase:
        payload = self._wrap_pipeline_payload(pipeline)
        response = self._make_request(method="POST", endpoint="/pipe/validate", json=payload)

        result = self._parse_result(response)

        if result.status == "Error":
            raise PipelineError(f"Pipeline validation failed: {result.error}")

        return result

    def execute_pipeline(
        self,
        pipeline: Dict[str, Any],
        name: Optional[str] = None,
        threads: Optional[int] = None,
    ) -> ResultBase:
        params = {}
        if name:
            params["name"] = name
        if threads:
            if not 1 <= threads <= 16:
                raise ValueError("Threads must be between 1 and 16")
            params["threads"] = threads

        payload = self._wrap_pipeline_payload(pipeline)
        response = self._make_request(method="PUT", endpoint="/task", json=payload, params=params)

        result = self._parse_result(response)

        if result.status == "Error":
            raise AparaviError(f"Task execution failed: {result.error}")

        return result

    def get_pipeline_status(self, token: str, task_type: str) -> ResultBase:
        response = self._make_request(method="GET", endpoint="/task", params={"token": token, "type": task_type})

        result = self._parse_result(response)

        if result.status == "Error":
            if "not found" in str(result.error).lower():
                raise TaskNotFoundError(f"Task not found: {result.error}")
            raise AparaviError(f"Failed to get task status: {result.error}")

        return result

    def send_payload_to_webhook(self, token: str, task_type: str, file_glob: str) -> List[Dict[str, Any]]:
        file_paths = glob.glob(file_glob)
        if not file_paths:
            raise ValueError(f"No files matched pattern: {file_glob}")

        webhook_url = f"{self.base_url}/webhook"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        responses = []

        try:
            if len(file_paths) > 1:
                files_to_upload = []
                for file_path in file_paths:
                    with open(file_path, "rb") as f:
                        file_buffer = f.read()
                    filename = os.path.basename(file_path)
                    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                    files_to_upload.append(
                        ("files", (filename, file_buffer, content_type))
                    )

                if self.logs != "none":
                    self._log(f"Uploading {len(files_to_upload)} files to webhook (multipart)", self.COLOR_ORANGE)

                response = requests.put(
                    webhook_url,
                    params={"token": token, "type": task_type},
                    headers=headers,
                    files=files_to_upload,
                    timeout=self.timeout,
                )

            else:
                file_path = file_paths[0]
                with open(file_path, "rb") as f:
                    file_buffer = f.read()
                filename = os.path.basename(file_path)
                content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

                if self.logs != "none":
                    self._log(f"Uploading single file to webhook: {filename}", self.COLOR_ORANGE)

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
                raise AparaviError(
                    f"Webhook failed: Server responded with status {e.response.status_code} - {e.response.text}"
                )
            raise AparaviError(f"Error sending to webhook: {e}")

    def teardown_pipeline(self, token: str, task_type: Literal["gpu", "cpu"]) -> ResultBase:
        response = self._make_request(method="DELETE", endpoint="/task", params={"token": token, "type": task_type})

        result = self._parse_result(response)

        if result.status == "Error":
            if "not found" in str(result.error).lower():
                raise TaskNotFoundError(f"Task not found: {result.error}")
            raise AparaviError(f"Failed to end task: {result.error}")

        return result

    def execute_pipeline_workflow(
        self,
        pipeline: Dict[str, Any],
        file_glob: Optional[str] = None,
        task_name: Optional[str] = "my-task",
        poll_interval: int = 15,
        max_attempts: int = 20
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Run a pipeline through the AparaviClient instance.

        Args:
            pipeline: The pipeline definition dictionary.
            file_glob: Glob pattern for files (required for webhook pipelines).
            task_name: Optional task name for identification.
            poll_interval: Seconds to wait between polling attempts.
            max_attempts: Max polling attempts to wait for "Running" state.

        Returns:
            - List of responses from webhook if webhook pipeline.
            - Final task status if non-webhook.
            - None if pipeline execution fails.
        """
        try:
            result = self.validate_pipeline(pipeline)
            self._log(f"Pipeline validation: {result.status}", self.COLOR_GREEN)
        except Exception as e:
            self._log(f"Validation failed: {e}", self.COLOR_RED)
            return None

        try:
            task_result = self.execute_pipeline(pipeline, name=task_name)
            if task_result.status != "OK":
                raise Exception(f"Task failed to start: {task_result.error}")

            if task_result.data is not None:
                token = task_result.data["token"]
                task_type = task_result.data["type"]
            else:
                self._log("No response received.")
                return

            is_webhook = pipeline.get("source", "").startswith("webhook") if isinstance(pipeline.get("source"), str) else False

            if is_webhook:
                self._log("Webhook pipeline detected. Polling until task is running...", self.COLOR_ORANGE)

                for attempt in range(max_attempts):
                    status_result = self.get_pipeline_status(token, task_type=task_type)
                    status_data = status_result.data
                    self._log(f"[Attempt {attempt + 1}] getTaskResponse: {status_data}", self.COLOR_ORANGE)
                    if status_data is not None:
                        if status_data.get("status") == "Running":
                            break

                    time.sleep(poll_interval)
                else:
                    raise TimeoutError("Task never entered 'Running' state.")

                self._log("Webhook task is running. Sending files...", self.COLOR_GREEN)
                if not file_glob:
                    raise ValueError("file_glob must be provided for webhook pipelines")

                responses = self.send_payload_to_webhook(
                    token=token,
                    task_type=task_type,
                    file_glob=file_glob
                )

                final_status = self.get_pipeline_status(token=token, task_type=task_type)
                self._log(f"Final Task status: {final_status.data}", self.COLOR_GREEN)

                end_result = self.teardown_pipeline(token=token, task_type=task_type)
                self._log(f"Task ended: {end_result.status}", self.COLOR_GREEN)

                return responses

            else:
                final_status = self.get_pipeline_status(token=token, task_type=task_type)
                self._log(f"Final Task status: {final_status.data}", self.COLOR_GREEN)

                end_result = self.teardown_pipeline(token=token, task_type=task_type)
                self._log(f"Task ended: {end_result.status}", self.COLOR_GREEN)

                return final_status.data  # 🔁 non-webhook return

        except Exception as e:
            self._log(f"Task operation failed: {e}", self.COLOR_RED)
            return None

    def run_predefined_pipeline(
        self,
        name: PredefinedPipeline,
        file_glob: Optional[str] = None,
        task_name: Optional[str] = None,
        poll_interval: int = 15,
        max_attempts: int = 20
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Run a predefined pipeline stored in the 'packages' folder.

        Args:
            name: Enum value of the predefined pipeline.
            file_glob: Optional glob pattern (required for webhook pipelines).
            task_name: Optional name for the task.
            poll_interval: Seconds between polling attempts.
            max_attempts: Max polling attempts for status.

        Returns:
            Result of the pipeline execution workflow.
        """
        pipeline_path = os.path.join(os.path.dirname(__file__), "pipelines", f"{name.value}.json")
        if not os.path.exists(pipeline_path):
            self._log(f"Pipeline definition not found: {pipeline_path}", self.COLOR_RED)
            return None

        try:
            with open(pipeline_path, "r") as f:
                pipeline = json.load(f)
        except Exception as e:
            self._log(f"Failed to read pipeline file: {e}", self.COLOR_RED)
            return None

        return self.execute_pipeline_workflow(
            pipeline=pipeline,
            file_glob=file_glob,
            task_name=task_name or name.value,
            poll_interval=poll_interval,
            max_attempts=max_attempts,
        )

