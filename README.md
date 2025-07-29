# Aparavi Data Toolchain SDK

A Python SDK for interacting with the Aparavi Web Services API. This SDK provides a clean, type-safe interface for validating pipelines, executing tasks, monitoring status, and managing webhooks with the Aparavi platform.

---

## Description

This SDK simplifies integration with Aparavi's data processing pipelines by providing:

* `validate_pipeline`: Validates a pipeline structure against Aparavi's backend to ensure it is correctly formed.
* `execute_pipeline`: Submits a pipeline for execution on the Aparavi platform.
* `get_pipeline_status`: Fetches the current execution status of a pipeline task.
* `teardown_pipeline`: Gracefully ends a running pipeline task.
* `send_payload_to_webhook`: Sends file(s) to a running webhook-based pipeline.
* `execute_pipeline_workflow`: Performs a full end-to-end execution lifecycle for a pipeline.
* `get_version`: Fetches the current version of the Aparavi API/backend.

Perfect for data engineers, analysts, and developers building automated data processing workflows.

---

## Setup

1. **Get your credentials:**
- Obtain your API key from the [Aparavi console](https://core-dev.aparavi.com/usage/)
- Note your API base URL (e.g. `https://eaas-dev.aparavi.com`)

2. **Install package:**
   ```bash
   pip install aparavi-dtc-sdk
   ```

3. **Create .env file:**
   
   **Linux/macOS:**
   ```bash
   touch .env
   ```
   
   **Windows:**
   ```cmd
   type nul > .env
   ```

### Env file

```env
APARAVI_API_KEY=aparavi-dtc-api-key
APARAVI_BASE_URL=https://eaas-dev.aparavi.com
```

---

## Quick Start

```python
import os

from dotenv import load_dotenv
from aparavi_dtc_sdk import AparaviClient

load_dotenv()

client = AparaviClient(
    base_url=os.getenv("APARAVI_BASE_URL"),
    api_key=os.getenv("APARAVI_API_KEY")
)

result = client.execute_pipeline_workflow(
    pipeline="./pipeline_config.json",
    file_glob="./*.png"
)

print(result)
```

### Pre Build Pipelines

Available pre-built pipeline configurations:
- `ADVANCED_PARSER`: Parse documentes using LLM-based logic, and deliver structured outputs such as text and tables. 
- `AUDIO_AND_SUMMARY`: Processes audio content and produces both a transcription and a concise summary. 
- `SIMPLE_AUDIO_TRANSCRIBE`: Processes audio files and returns transcriptions of spoken content. 
- `SIMPLE_PARSER`: Extracts and processes metadata and content from uploaded documents. 

```python
import os

from dotenv import load_dotenv
from aparavi_dtc_sdk import AparaviClient, PredefinedPipelines # Import PredefinedPipelines enum

load_dotenv()

client = AparaviClient(
    base_url=os.getenv("APARAVI_BASE_URL"),
    api_key=os.getenv("APARAVI_API_KEY")
)

result = client.execute_pipeline_workflow(
    pipeline=PredefinedPipelines.SIMPLE_AUDIO_TRANSCRIBE, # Specify PredefinedPipelines
    file_glob="./audio/*.mp3"
)

print(result)
```

### Power user quick start

```python
import json
import os

from dotenv import load_dotenv
from aparavi_dtc_sdk import AparaviClient

load_dotenv()

client = AparaviClient(
    base_url=os.getenv("APARAVI_BASE_URL"),
    api_key=os.getenv("APARAVI_API_KEY")
)

try:
    validation_result = client.validate_pipeline("pipeline_config.json")
except Exception as e:
    print(f"Validation failed: {e}")

try:
    start_result = client.execute_pipeline(pipeline_config, name="my-task")
    if start_result.status == "OK":
        token = start_result.data["token"]
        task_type = start_result.data["type"]

        status_result = client.get_pipeline_status(token=token, task_type=task_type)

        end_result = client.teardown_pipeline(token=token, task_type=task_type)

except Exception as e:
    print(f"Task operation failed: {e}")
```

---

## Development

### Setting up for development

```bash
# Install in development mode
pip install -e ".[dev]"

# Find package Install
pip list | grep aparavi

# Show package info
pip show aparavi-dtc-sdk

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

