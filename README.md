# DevOps Incident Response Agent

A comprehensive DevOps and Incident Response agent that leverages AI to help diagnose and resolve issues by interacting with GitHub, Prometheus, Loki, and other DevOps tools.

## Features

- 🤖 **AI-Powered Incident Response**: Uses advanced LLM models (Gemini, OpenAI, Claude, etc.) for intelligent issue diagnosis.
- 🔧 **GitHub Integration**: Comprehensive GitHub API tools for repository management, issue tracking, and workflow automation.
- 📊 **Observability Integration**: Connects to Prometheus for metrics and Loki for logs to get a full picture of application health.
- 🛠️ **Modular Architecture**: Extensible tool system for adding new integrations (e.g., Jenkins, Kubernetes, Slack).
- 🔒 **Secure**: Environment-based configuration with proper credential management.
- 📈 **Monitoring Ready**: Designed to work with modern observability stacks.

## Quick Start


### Logging Configuration

The agent includes comprehensive logging with the following features:

- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL, SUCCESS
- **File Rotation**: Automatic log rotation based on size or time
- **Retention Policy**: Configurable log retention periods
- **Thread Safety**: Thread-safe logging for concurrent operations
- **Structured Format**: Rich log format with timestamps, levels, and context

For detailed logging documentation, see [docs/logging.md](docs/logging.md).

## Usage

### Basic Usage

Start the agent and interact with it:

```bash
python src/main/react_agent.py
```

Example interactions:
```
Hey what is up : List all repositories in my organization
Hey what is up : Check the status of workflow runs in repo/my-app
Hey what is up : Create an issue about the deployment failure
Hey what is up : quit
```

### Available Tools

The agent provides access to comprehensive GitHub tools:

#### Repository Management
- List repositories
- Get repository details
- Search repositories

#### Issue Management
- List issues
- Create issues
- Update issues
- Search issues

#### Pull Request Management
- List pull requests
- Create pull requests
- Merge pull requests

#### Workflow Management
- List workflow runs
- Trigger workflows
- Cancel workflow runs

#### Content Management
- Get file content
- Create or update files
- List commits
- List branches

#### Deployment Management
- List deployments
- Create deployments

#### Webhook Management
- List webhooks
- Create webhooks

## Architecture

### Core Components

- **LLM Factory**: Manages different LLM providers (Gemini, OpenAI, Claude, etc.)
- **GitHub Toolset**: Comprehensive GitHub API integration
- **ReAct Agent**: LangGraph-based agent with reasoning capabilities
- **Logging System**: Structured logging with loguru

### Project Structure

```
DevOps_Agent/
├── docker
│   ├── .dockerignore
│   └── docker-compose.yaml
├── docs
│   ├── action_plan.md
│   ├── configuration.md
│   ├── jenkins_docs.md
│   ├── logging.md
│   └── tool_recommendations.md
├── examples
│   └── logging_demo.py
├── k8s
│   └── config.yaml
├── llms
│   ├── base.py
│   ├── factory.py
│   ├── providers.py
│   └── __init__.py
├── logs
│   └── devops_agent_test.log
├── prompts
│   └── system_prompt.md
├── protocols
│   └── mcp
│       ├── client.py
│       └── server.py
├── src
│   ├── __init__.py
│   ├── config
│   │   ├── config_manager.py
│   │   ├── settings.py
│   │   └── __init__.py
│   ├── main
│   │   ├── agent_serve.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── react_agent.py
│   │   ├── state.py
│   │   └── __init__.py
│   └── utils
│       ├── logging_config.py
│       ├── rate_limiter.py
│       ├── retry.py
│       └── __init__.py
├── tests
│   ├── e2e
│   ├── integration
│   └── unit
│       └── test_logging.py
└── tools
    ├── base.py
    ├── __init__.py
    ├── github
    │   ├── factory.py
    │   ├── github_tool.py
    │   └── __init__.py
    ├── jenkins
    │   ├── factory.py
    │   └── jenkins_tool.py
    ├── kubernetes
    │   ├── factory.py
    │   └── kubernetes_tool.py
    ├── Loki
    │   └── loki_log_aggregation_tool.py
    ├── powershell
    │   ├── factory.py
    │   └── runner.py
    ├── prometheus
    │   ├── factory.py
    │   └── prometheus_tool.py
    └── slack
        ├── factory.py
        ├── slack_tool.py
        └── __init__.py
       # Logging demonstration
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Logging Demo

Test the logging functionality:

```bash
python examples/logging_demo.py
```

### Adding New Tools

1. Create a new tool class in `tools/`
2. Implement the `AbstractTool` interface
3. Register the tool in the appropriate factory
4. Add tests for the new tool

### Adding New LLM Providers

1. Create a new provider class in `llms/providers.py`
2. Implement the `LLMProvider` interface
3. Register the provider in `LLMFactory`
4. Add configuration and tests

## Monitoring and Observability

### Log Analysis

The structured logs can be analyzed using various tools:

```bash
# Count errors in the last hour
grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" logs/devops_agent.log | grep "ERROR" | wc -l

# Find slow operations
grep "completed in" logs/devops_agent.log | grep -E "[0-9]+\.[0-9]+ seconds" | awk '$NF > 1.0'
```

### Integration with Monitoring Tools

The logs are compatible with:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- Datadog
- New Relic
- Grafana

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
1. Check the [documentation](docs/)
2. Search existing issues
3. Create a new issue with detailed information

## Roadmap

See [docs/action_plan.md](docs/action_plan.md) for the development roadmap and planned features.
### Prerequisites

- Python 3.12+
- Docker and `docker-compose`
- GitHub Personal Access Token
- API keys for your chosen LLM provider

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd DevOps_Agent
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Set up environment variables:
    ```bash
    cp .env.example .env
    # Edit .env with your API keys and configuration
    ```

4.  Run the agent:
    ```bash
    python src/main/react_agent.py
    ```

## Testing with a Local Observability Stack

To fully test the agent's diagnostic capabilities with tools like Loki and Prometheus, you can set up a local, containerized test environment. This environment includes a sample application that can generate logs and metrics, and a full observability stack to monitor it.

### Overview of the Test Environment

This setup uses `docker-compose` to launch:
- A **FastAPI App**: A simple Python web server that the agent will monitor. It includes a "Chaos Monkey" to intentionally inject errors and latency for testing.
- **Prometheus**: To scrape performance metrics from the FastAPI app.
- **Loki**: To aggregate logs from the FastAPI app.
- **Promtail**: To ship logs from the app to Loki.
- **Grafana**: To visualize logs and metrics (optional, for manual inspection).

### 1. Setting Up the Test Environment

In your `DevOps_Agent` project root, create a new directory called `local_test_stack/`. Inside it, create the following file structure.

```bash 

local_test_stack/
├── app/
│ ├── main.py
│ ├── Dockerfile
│ └── requirements.txt
├── promtail/
│ └── config.yml
├── prometheus/
│ └── prometheus.yml
├── loki/
│ └── config.yml
└── docker-compose.yml
```
Now, populate these files with the content below.

#### `docker-compose.yml`
This file orchestrates all the services. 

``` yaml

services:
  fastapi-app:
    build: ./app
    container_name: fastapi-app
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/var/log
    networks:
      - monitoring

  loki:
    image: grafana/loki:2.9.2
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      # THE FIX: Mount the parent directory...
      - ./loki:/etc/loki_config
      - ./loki_data:/data/loki
    # ...and tell the command to find the file inside it.
    command: -config.file=/etc/loki_config/config.yaml
    networks:
      - monitoring

  promtail:
    image: grafana/promtail:2.9.2
    container_name: promtail
    volumes:
      # THE FIX: Mount the parent directory...
      - ./promtail:/etc/promtail_config
      - ./logs:/var/log
    # ...and tell the command to find the file inside it.
    command: -config.file=/etc/promtail_config/config.yaml
    depends_on:
      - loki
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:v2.47.2
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      # THE FIX: Mount the parent directory...
      - ./prometheus:/etc/prometheus_config
      - ./prometheus_data:/prometheus
    # ...and tell the command to find the file inside it.
    command: --config.file=/etc/prometheus_config/prometheus.yaml
    depends_on:
      - fastapi-app
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:10.2.0
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
      - loki
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

app/main.py
The sample application with built-in Chaos Monkey.

This is just an example , you can simulate system failures by using tools like chaos monkey or you can use the built-in tools in your container orchestration

``` python 
import sys, random, asyncio
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

# --- Loguru Logging Setup ---
logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")
logger.add("/var/log/app.log", serialize=True, level="INFO", rotation="10 MB", catch=True)

# --- Chaos Monkey ---
class ChaosConfig(BaseModel):
    enabled: bool = False
    error_rate: float = 0.0
    latency_ms: int = 0
chaos_config = ChaosConfig()

class ChaosMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "/chaos/" in request.url.path:
            return await call_next(request)
        if chaos_config.enabled:
            if random.random() < chaos_config.error_rate:
                logger.error("CHAOS: Injecting 503 error.")
                raise HTTPException(status_code=503, detail="Chaos Monkey induced a failure!")
            if chaos_config.latency_ms > 0:
                await asyncio.sleep(chaos_config.latency_ms / 1000.0)
        return await call_next(request)

# --- FastAPI App ---
app = FastAPI()
app.add_middleware(ChaosMiddleware)
Instrumentator().instrument(app).expose(app)

@app.get("/")
async def read_root():
    logger.info("Received GET request on path: /")
    return {"message": "Hello, World!"}

@app.get("/error")
async def make_error():
    try:
        result = 1 / 0
    except Exception:
        logger.exception("A predictable ZeroDivisionError occurred!")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"result": result}

@app.get("/chaos/status", tags=["Chaos Control"])
async def get_chaos_status(): return chaos_config
@app.post("/chaos/configure", tags=["Chaos Control"])
async def configure_chaos(config: ChaosConfig):
    global chaos_config
    chaos_config = config
    logger.warning(f"CHAOS: Config updated to: {config.model_dump_json()}")
    return chaos_config

logger.info("Test application startup complete.")
```

``` text
fastapi
uvicorn[standard]
pydantic
prometheus-fastapi-instrumentator
loguru
```
Dockerfile

```Dockerfile

FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

promtail/config.yml
```yaml
global:
  scrape_interval: 15s # Scrape targets every 15 seconds

scrape_configs:
  - job_name: 'prometheus'
    # Scrape Prometheus itself
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'fastapi-app'
    # Scrape our FastAPI application
    static_configs:
      - targets: ['fastapi-app:8000'] # 'fastapi-app' is the service name in docker-compose
```

loki/config.yml
``` yaml 
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /data/loki
  storage:
    filesystem:
      chunks_directory: /data/loki/chunks
      rules_directory: /data/loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9093

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s

compactor:
  working_directory: /data/loki
  shared_store: filesystem
  compactor_ring:
    kvstore:
      store: inmemory
```

Grafana_Loki_test\grafana\provisioning\datasources\datasources.yaml
``` yaml 
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090 # 'prometheus' is the service name
    isDefault: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100 # 'loki' is the service name
```


# 2. Running the Environment
Navigate to the local_test_stack/ directory:

``` bash 
cd local_test_stack
```

# Start all services using docker-compose:
``` bash 
docker-compose up -d
```

All containers should show an Up or running status.
## 3. Configuring the DevOps Agent
For the agent to connect to this local stack, ensure your main .env file (in the DevOps_Agent root) has the correct URLs:

``` .env
PROMETHEUS_URL="http://localhost:9090"
LOKI_URL="http://localhost:3100" # As used by the retrieve_job_logs tool

# Add other required keys like GITHUB_PERSONAL_ACCESS_TOKEN, GOOGLE_API_KEY, etc.
```

## 4. Testing with the Agent
Now you are ready to test!
Start the Agent: From the project root (DevOps_Agent/), run your agent. 

``` bash 
python src/main/react_agent.py
```

# 5. Give it a task 

``` text 
"Check the logs for the fastapi-app job.
```

# 6.C reate an Incident: Use the Chaos Monkey to inject problems.
Inject 50% errors:
``` bash 
curl -X POST -H "Content-Type: application/json" -d '{"enabled": true, "error_rate": 0.5}' http://localhost:8000/chaos/configure
```
# 7. Then, prompt the agent:
```text
"Users are reporting a high number of errors from the fastapi-app. Investigate and report the cause."
```

# 8.Stop the Environment: When you are finished, stop and remove the containers:
``` bash 
docker-compose down
```

# Configuration : 

Configuration
Environment Variables
Create a .env file with the following variables:

``` .env
GOOGLE_API_KEY=your_google_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
CLAUDE_API_KEY=your_claude_api_key

# GitHub Configuration
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token

# Observability Configuration
PROMETHEUS_URL="http://localhost:9090"
LOKI_URL="http://localhost:3100"

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/devops_agent.log
LOG_CONSOLE=true
LOG_FILE_ENABLED=true
LOG_ROTATION=10 MB
LOG_RETENTION=30 days

# Langsmith Configuration
LANGSMITH_TRACING="true"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="<Your_langsmith_api_key>"
LANGSMITH_PROJECT="<Your_langsmith_project>"
```
