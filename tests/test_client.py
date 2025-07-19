"""
Tests for Aparavi SDK client
"""

import pytest
import requests_mock
from aparavi_dtc_sdk import AparaviClient
from aparavi_dtc_sdk.exceptions import AuthenticationError, ValidationError, TaskNotFoundError, AparaviError


class TestAparaviClient:
    """Test cases for AparaviClient"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = AparaviClient(
            base_url="https://eaas-dev.aparavi.com",
            api_key="test-api-key"
        )
        self.pipeline_config = {
            "source": "s3://bucket/data",
            "transformations": ["filter", "aggregate"]
        }
    
    def test_init(self):
        """Test client initialization"""
        assert self.client.base_url == "https://eaas-dev.aparavi.com"
        assert self.client.api_key == "test-api-key"
        assert self.client.timeout == 30
        assert "Bearer test-api-key" in self.client.session.headers['Authorization']
    
    def test_validate_pipe_success(self):
        """Test successful pipeline validation"""
        with requests_mock.Mocker() as m:
            m.post(
                "https://eaas-dev.aparavi.com/pipe/validate",
                json={"status": "OK", "data": {"valid": True}}
            )
            
            result = self.client.validate_pipe(self.pipeline_config)
            assert result.status == "OK"
            assert result.data == {"valid": True}
    
    def test_validate_pipe_failure(self):
        """Test failed pipeline validation"""
        with requests_mock.Mocker() as m:
            m.post(
                "https://eaas-dev.aparavi.com/pipe/validate",
                json={"status": "Error", "error": {"message": "Invalid pipeline"}}
            )
            
            with pytest.raises(Exception):
                self.client.validate_pipe(self.pipeline_config)
    
    def test_start_task_success(self):
        """Test successful task start"""
        with requests_mock.Mocker() as m:
            m.put(
                "https://eaas-dev.aparavi.com/task",
                json={"status": "OK", "data": {"token": "task-123"}}
            )
            
            result = self.client.start_task(self.pipeline_config, name="test-task")
            assert result.status == "OK"
            assert result.data == {"token": "task-123"}
    
    def test_start_task_with_threads(self):
        """Test task start with thread specification"""
        with requests_mock.Mocker() as m:
            m.put(
                "https://eaas-dev.aparavi.com/task",
                json={"status": "OK", "data": {"token": "task-123"}}
            )
            
            result = self.client.start_task(self.pipeline_config, threads=4)
            assert result.status == "OK"
    
    def test_start_task_invalid_threads(self):
        """Test task start with invalid thread count"""
        with pytest.raises(ValueError):
            self.client.start_task(self.pipeline_config, threads=20)
    
    def test_get_task_status_success(self):
        """Test successful task status retrieval"""
        with requests_mock.Mocker() as m:
            m.get(
                "https://eaas-dev.aparavi.com/task?token=task-123",
                json={"status": "OK", "data": {"state": "running"}}
            )
            
            result = self.client.get_task_status("task-123")
            assert result.status == "OK"
            assert result.data == {"state": "running"}
    
    def test_get_task_status_not_found(self):
        """Test task status for non-existent task"""
        with requests_mock.Mocker() as m:
            m.get(
                "https://eaas-dev.aparavi.com/task?token=task-123",
                json={"status": "Error", "error": {"message": "Task not found"}}
            )
            
            with pytest.raises(TaskNotFoundError):
                self.client.get_task_status("task-123")
    
    def test_post_to_webhook_success(self):
        """Test successful webhook post"""
        with requests_mock.Mocker() as m:
            m.put(
                "https://eaas-dev.aparavi.com/webhook?token=task-123",
                json={"result": "success"}
            )
            
            result = self.client.post_to_webhook("task-123", {"data": "test"})
            assert result == {"result": "success"}
    
    def test_end_task_success(self):
        """Test successful task termination"""
        with requests_mock.Mocker() as m:
            m.delete(
                "https://eaas-dev.aparavi.com/task?token=task-123",
                json={"status": "OK"}
            )
            
            result = self.client.end_task("task-123")
            assert result.status == "OK"
    
    def test_authentication_error(self):
        """Test authentication error handling"""
        with requests_mock.Mocker() as m:
            m.post(
                "https://eaas-dev.aparavi.com/pipe/validate",
                status_code=401,
                text="Unauthorized"
            )
            
            with pytest.raises(AuthenticationError):
                self.client.validate_pipe(self.pipeline_config)
    
    def test_validation_error(self):
        """Test validation error handling"""
        with requests_mock.Mocker() as m:
            m.post(
                "https://eaas-dev.aparavi.com/pipe/validate",
                status_code=422,
                text="Validation failed"
            )
            
            with pytest.raises(ValidationError):
                self.client.validate_pipe(self.pipeline_config)
    
    def test_generic_api_error(self):
        """Test generic API error handling"""
        with requests_mock.Mocker() as m:
            m.post(
                "https://eaas-dev.aparavi.com/pipe/validate",
                status_code=500,
                text="Internal server error"
            )
            
            with pytest.raises(AparaviError):
                self.client.validate_pipe(self.pipeline_config)

