"""
Aparavi SDK Client
"""

import requests
from typing import Optional, Dict, Any, Literal 
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
    
    def start_task(self, pipeline: Dict[str, Any], name: Optional[str] = None, 
                   threads: Optional[int] = None, type: Literal['gpu', 'cpu'] = 'gpu') -> ResultBase:
        """
        Execute a task with the given pipeline configuration
        
        Args:
            pipeline: The pipeline configuration
            name: Optional name for the task
            threads: Optional number of threads to use (1-16)
            
        Returns:
            ResultBase: Response containing task token on success
            
        Raises:
            ValidationError: If pipeline validation fails
            AuthenticationError: If authentication fails
            AparaviError: For other API errors
        """
        params = {'type': type}
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
    
    def get_task_status(self, token: str, type: Literal['gpu', 'cpu'] = 'gpu') -> ResultBase:
        """
        Get the status of a task
        
        Args:
            token: The task token received from start_task
            
        Returns:
            ResultBase: Response containing task status
            
        Raises:
            TaskNotFoundError: If task is not found
            AuthenticationError: If authentication fails
            AparaviError: For other API errors
        """
        response = self._make_request(
            method='GET',
            endpoint='/task',
            params={'token': token, 'type': type}
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
    
    def post_to_webhook(self, token: str, data: Optional[Dict[str, Any]] = None, type: Literal['gpu', 'cpu'] = 'gpu') -> Dict[str, Any]:
        """
        Send a webhook request to the task engine
        
        Args:
            token: The task token
            data: Optional data to send in the webhook request
            
        Returns:
            Dict: Response from the webhook endpoint
            
        Raises:
            TaskNotFoundError: If task is not found
            AuthenticationError: If authentication fails
            AparaviError: For other API errors
        """
        kwargs = {'params': {'token': token, 'type': type}}
        if data:
            kwargs['json'] = data
        
        response = self._make_request(
            method='PUT',
            endpoint='/webhook',
            **kwargs
        )
        
        return response
    
    def end_task(self, token: str) -> ResultBase:
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
            params={'token': token}
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

