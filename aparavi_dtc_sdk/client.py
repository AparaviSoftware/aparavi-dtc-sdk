"""
Aparavi SDK Client
"""

import glob
import base64
import os
import requests
from typing import Optional, Dict, Any, Literal, List 
from .models import ResultBase
from .exceptions import AparaviError, AuthenticationError, ValidationError, TaskNotFoundError, PipelineError


class AparaviClient:
    """
    Client for interacting with Aparavi Web Services API
    """
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """
        Initialize the Aparavi client
        
        Args:
            base_url: The base URL of the Aparavi API
            api_key: The API key for authentication
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
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
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or authentication failed")
            elif response.status_code == 422:
                raise ValidationError(f"Validation error: {response.text}")
            elif response.status_code >= 400:
                raise AparaviError(f"API error {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise AparaviError(f"Request failed: {str(e)}")

    def get_version(self) -> ResultBase:
        """
        Get the version of the Aparavi Web Services API

        Returns:
            ResultBase: Response containing the version information

        Raises:
            AuthenticationError: If authentication fails
            AparaviError: For other API errors
        """
        response = self._make_request(
            method='GET',
            endpoint='/version'
        )

        return ResultBase(
            status=response['status'],
            data=response.get('data'),
            error=response.get('error'),
            metrics=response.get('metrics')
        )

    def validate_pipe(self, pipeline: Dict[str, Any]) -> ResultBase:
        """
        Validate a processing pipeline configuration
        
        Args:
            pipeline: The pipeline configuration to validate
            
        Returns:
            ResultBase: Response indicating success or failure
            
        Raises:
            ValidationError: If pipeline validation fails
            AuthenticationError: If authentication fails
            AparaviError: For other API errors
        """
        response = self._make_request(
            method='POST',
            endpoint='/pipe/validate',
            json=pipeline
        )
        
        result = ResultBase(
            status=response['status'],
            data=response.get('data'),
            error=response.get('error'),
            metrics=response.get('metrics')
        )
        
        if result.status == 'Error':
            raise PipelineError(f"Pipeline validation failed: {result.error}")
        
        return result
    
    def start_task(
        self,
        pipeline: Dict[str, Any],
        task_type: str = "gpu",
        name: Optional[str] = None,
        threads: Optional[int] = None,
    ) -> ResultBase:
        params = {'type': task_type}
        if name:
            params['name'] = name
        if threads:
            if not 1 <= threads <= 16:
                raise ValueError("Threads must be between 1 and 16")
            params['threads'] = threads

        response = self._make_request(
            method='PUT',
            endpoint='/task',
            json=pipeline,
            params=params
        )

        result = ResultBase(
            status=response['status'],
            data=response.get('data'),
            error=response.get('error'),
            metrics=response.get('metrics')
        )

        if result.status == 'Error':
            raise AparaviError(f"Task execution failed: {result.error}")

        return result


    def get_task_status(self, token: str, task_type: str) -> ResultBase:
        response = self._make_request(
            method='GET',
            endpoint='/task',
            params={'token': token, 'type': task_type}
        )

        result = ResultBase(
            status=response['status'],
            data=response.get('data'),
            error=response.get('error'),
            metrics=response.get('metrics')
        )

        if result.status == 'Error':
            if 'not found' in str(result.error).lower():
                raise TaskNotFoundError(f"Task not found: {result.error}")
            raise AparaviError(f"Failed to get task status: {result.error}")

        return result


    def send_to_webhook_with_file(
        self,
        token: str,
        task_type: str,
        file_glob: str
    ) -> List[Dict[str, Any]]:
        file_paths = glob.glob(file_glob)
        if not file_paths:
            raise ValueError(f"No files matched pattern: {file_glob}")

        responses = []
        for file_path in file_paths:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")

            file_data = {
                "record": {
                    "filename": os.path.basename(file_path),
                    "content": encoded,
                    "encoding": "base64"
                }
            }

            response = self._make_request(
                method="PUT",
                endpoint="/webhook",
                params={"token": token, "type": task_type},
                json=file_data
            )
            responses.append(response)

        return responses
 
    def end_task(self, token: str, task_type: Literal["gpu", "cpu"]) -> ResultBase:
        """
        Cancel/end a task
        
        Args:
            token: The task token received from start_task
            
        Returns:
            ResultBase: Response indicating success or failure
            
        Raises:
            TaskNotFoundError: If task is not found
            AuthenticationError: If authentication fails
            AparaviError: For other API errors
        """
        response = self._make_request(
            method='DELETE',
            endpoint='/task',
            params={'token': token, 'type': task_type}
        )
        
        result = ResultBase(
            status=response['status'],
            data=response.get('data'),
            error=response.get('error'),
            metrics=response.get('metrics')
        )
        
        if result.status == 'Error':
            if 'not found' in str(result.error).lower():
                raise TaskNotFoundError(f"Task not found: {result.error}")
            raise AparaviError(f"Failed to end task: {result.error}")
        
        return result

