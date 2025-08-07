# DevOps Incident Response Agent

A comprehensive DevOps and Incident Response agent that leverages AI to help diagnose and resolve issues by interacting with GitHub and other DevOps tools.

## Features

- 🤖 **AI-Powered Incident Response**: Uses advanced LLM models (Gemini, OpenAI, Claude, etc.) for intelligent issue diagnosis
- 🔧 **GitHub Integration**: Comprehensive GitHub API tools for repository management, issue tracking, and workflow automation
- 📊 **Structured Logging**: Advanced loguru-based logging with rotation, retention, and monitoring capabilities
- 🛠️ **Modular Architecture**: Extensible tool system for adding new integrations
- 🔒 **Secure**: Environment-based configuration with proper credential management
- 📈 **Monitoring Ready**: Structured logs compatible with ELK Stack, Splunk, and other monitoring tools

## Quick Start

### Prerequisites

- Python 3.12+
- GitHub Personal Access Token
- API keys for your chosen LLM provider

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd DevOps_Agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Run the agent:
```bash
python src/main/react_agent.py
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# LLM Configuration
GOOGLE_API_KEY=your_google_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
CLAUDE_API_KEY=your_claude_api_key

# GitHub Configuration
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/devops_agent.log
LOG_CONSOLE=true
LOG_FILE_ENABLED=true
LOG_ROTATION=10 MB
LOG_RETENTION=30 days
```

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
├── src/
│   ├── main/
│   │   ├── react_agent.py      # Main agent application
│   │   ├── graph.py            # LangGraph configuration
│   │   └── nodes.py            # Graph nodes
│   ├── utils/
│   │   ├── logging_config.py   # Logging configuration
│   │   ├── rate_limiter.py     # Rate limiting utilities
│   │   └── retry.py            # Retry mechanisms
│   └── config/
│       └── settings.py         # Configuration management
├── llms/
│   ├── factory.py              # LLM provider factory
│   ├── base.py                 # Base LLM classes
│   └── providers.py            # LLM provider implementations
├── tools/
│   ├── github/
│   │   ├── factory.py          # GitHub toolset factory
│   │   └── github_tool.py      # GitHub API tools
│   └── base.py                 # Base tool classes
├── docs/
│   ├── logging.md              # Logging documentation
│   └── action_plan.md          # Development roadmap
├── tests/
│   ├── unit/
│   │   └── test_logging.py     # Logging tests
│   ├── integration/
│   └── e2e/
└── examples/
    └── logging_demo.py         # Logging demonstration
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
