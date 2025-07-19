# Aparavi Data Toolchain SDK

A Python SDK for interacting with the Aparavi Web Services API. This SDK provides a clean, type-safe interface for validating pipelines, executing tasks, monitoring status, and managing webhooks with the Aparavi platform.

---

## Description

This SDK simplifies integration with Aparavi's data processing pipelines by providing:

- **Pipeline Validation**: Validate your data processing configurations before execution
- **Task Management**: Start, monitor, and terminate processing tasks
- **Webhook Integration**: Send real-time updates to your task engines
- **Error Handling**: Comprehensive exception handling with meaningful error messages
- **Type Safety**: Full type hints and structured data models for reliable development

Perfect for data engineers, analysts, and developers building automated data processing workflows.

---

## Setup

1. **Install the package:**
   ```bash
   pip install aparavi-dtc-sdk
   ```

2. **Get your API credentials:**
   - Obtain your API key from the Aparavi app
   - Note your API base URL (e.g., `https://eaas-dev.aparavi.com`)

3. **Initialize the client:**
   ```python
   from aparavi-dtc-sdk import AparaviClient

   client = AparaviClient(
       base_url="https://api.aparavi.com",
       api_key="your-api-key-here"
   )
   ```

---

## Quick Start

```python
from aparavi-dtc-sdk import AparaviClient

# Initialize the client
client = AparaviClient(
    base_url="https://api.aparavi.com",
    api_key="your-api-key-here"
)

# Validate a pipeline configuration
pipeline_config = {
    "source": "s3://bucket/data",
    "transformations": ["filter", "aggregate"]
}

try:
    result = client.validate_pipe(pipeline_config)
    print(f"Pipeline validation: {result.status}")
except Exception as e:
    print(f"Validation failed: {e}")

# Start a task
try:
    task_result = client.start_task(pipeline_config, name="my-task")
    if task_result.status == "OK":
        token = task_result.data["token"]
        print(f"Task started with token: {token}")
        
        # Get task status
        status_result = client.get_task_status(token)
        print(f"Task status: {status_result.data}")
        
        # End the task when done
        end_result = client.end_task(token)
        print(f"Task ended: {end_result.status}")
        
except Exception as e:
    print(f"Task operation failed: {e}")
```

---

## Development

### Setting up for development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
flake8 aparavi-dtc-sdk/
black aparavi-dtc-sdk/
mypy aparavi-dtc-sdk/
```

### Running Tests

```bash
pytest tests/
```

## Support

For problems and questions, please open an issue on the [GitHub repository](https://github.com/AparaviSoftware/aparavi-dtc-sdk/issues).

---

## Authors

**Joshua D. Phillips**  
[github.com/joshuadarron](https://github.com/joshuadarron)

Contributions welcome — feel free to submit a PR or open an issue!

