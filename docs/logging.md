# Logging Documentation

This document describes the comprehensive logging system implemented in the DevOps Agent using loguru.

## Overview

The DevOps Agent uses loguru for structured, feature-rich logging that provides:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL, SUCCESS)
- Console and file logging with colorization
- Automatic log rotation and retention
- Thread-safe logging
- Detailed error tracebacks
- Environment-based configuration

## Quick Start

### Basic Usage

```python
from src.utils.logging_config import setup_logging_from_env, get_logger

# Setup logging (uses environment variables)
setup_logging_from_env()

# Get a logger
logger = get_logger(__name__)

# Use the logger
logger.info("Application started")
logger.debug("Debug information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.success("Operation completed successfully")
```

### Custom Configuration

```python
from src.utils.logging_config import setup_logging

# Custom logging setup
setup_logging(
    log_level="DEBUG",
    log_file="custom.log",
    enable_console=True,
    enable_file=True,
    rotation="5 MB",
    retention="14 days"
)
```

## Environment Variables

The logging system can be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FILE` | `logs/devops_agent.log` | Path to log file |
| `LOG_CONSOLE` | `true` | Enable console logging (true/false) |
| `LOG_FILE_ENABLED` | `true` | Enable file logging (true/false) |
| `LOG_ROTATION` | `10 MB` | Log rotation size or time |
| `LOG_RETENTION` | `30 days` | Log retention period |

### Example .env file

```env
# Logging Configuration
LOG_LEVEL=DEBUG
LOG_FILE=logs/devops_agent.log
LOG_CONSOLE=true
LOG_FILE_ENABLED=true
LOG_ROTATION=10 MB
LOG_RETENTION=30 days
```

## Log Levels

### DEBUG
Detailed information for debugging purposes.

```python
logger.debug("Processing user request", user_id="123", action="login")
```

### INFO
General information about application flow.

```python
logger.info("User authentication successful", user_id="123")
```

### WARNING
Warning messages for potentially problematic situations.

```python
logger.warning("API rate limit approaching", current_usage="85%")
```

### ERROR
Error messages for failed operations.

```python
logger.error("Failed to connect to database", error=str(e))
```

### CRITICAL
Critical errors that may cause application failure.

```python
logger.critical("Database connection lost", retry_attempts=3)
```

### SUCCESS
Success messages for completed operations.

```python
logger.success("Deployment completed successfully", version="1.2.3")
```

## Log Format

The default log format includes:
- Timestamp with milliseconds
- Log level
- Module name, function name, and line number
- Message content

Example output:
```
2024-01-15 10:30:45.123 | INFO     | main:process_request:45 | Processing user request
2024-01-15 10:30:45.124 | DEBUG    | api:validate_token:23 | Token validation successful
2024-01-15 10:30:45.125 | SUCCESS  | main:process_request:67 | Request processed successfully
```

## File Logging Features

### Automatic Rotation
Logs are automatically rotated when they reach the specified size or time limit:

```python
# Rotate when file reaches 10 MB
setup_logging(rotation="10 MB")

# Rotate daily at midnight
setup_logging(rotation="00:00")

# Rotate weekly
setup_logging(rotation="1 week")
```

### Retention Policy
Old log files are automatically cleaned up:

```python
# Keep logs for 30 days
setup_logging(retention="30 days")

# Keep logs for 1 week
setup_logging(retention="1 week")

# Keep only the last 5 files
setup_logging(retention=5)
```

### Compression
Old log files are automatically compressed to save disk space.

## Error Handling

### Exception Logging
Use `logger.exception()` to log exceptions with full tracebacks:

```python
try:
    result = risky_operation()
except Exception as e:
    logger.exception("Operation failed")
    # This automatically includes the full traceback
```

### Structured Error Logging
Log errors with additional context:

```python
try:
    response = api_call(user_id, data)
except APIError as e:
    logger.error(
        "API call failed",
        user_id=user_id,
        endpoint="/api/users",
        status_code=e.status_code,
        error_message=str(e)
    )
```

## Performance Logging

### Timing Operations
Log the duration of operations:

```python
import time

start_time = time.time()
logger.debug("Starting database query")

# ... perform operation ...

duration = time.time() - start_time
logger.info(f"Database query completed in {duration:.2f} seconds")

if duration > 1.0:
    logger.warning(f"Slow query detected: {duration:.2f}s")
```

## Integration with Components

### LLM Factory
The LLM factory includes comprehensive logging:

```python
logger.debug("Creating LLM provider for type: gemini")
logger.info("LLM provider created successfully: gemini(gemini-2.5-flash)")
logger.success("Successfully created gemini provider")
```

### GitHub Toolset
GitHub tools include detailed logging:

```python
logger.debug("Initializing GitHub toolset")
logger.info("GitHub API client initialized successfully")
logger.info("Successfully created 22 GitHub tools")
logger.debug("Available tools: ['list_repositories', 'get_repository', ...]")
```

### Main Agent
The main agent includes session tracking and error handling:

```python
logger.info("Starting DevOps Incident Response Agent")
logger.info("Session 1: Waiting for user input")
logger.info("Processing query: List all repositories in the organization...")
logger.success("Session 1 completed successfully")
```

## Best Practices

### 1. Use Appropriate Log Levels
- DEBUG: Detailed debugging information
- INFO: General application flow
- WARNING: Potential issues
- ERROR: Failed operations
- CRITICAL: Application-threatening issues
- SUCCESS: Completed operations

### 2. Include Context
```python
# Good
logger.info("User login successful", user_id="123", ip="192.168.1.100")

# Avoid
logger.info("Login successful")
```

### 3. Use Structured Logging
```python
# Good
logger.error(
    "API request failed",
    endpoint="/api/users",
    method="POST",
    status_code=500,
    response_time=1.23
)

# Avoid
logger.error(f"API request failed: {endpoint} {method} {status_code}")
```

### 4. Handle Sensitive Data
Never log sensitive information like passwords, tokens, or personal data:

```python
# Good
logger.info("User authenticated", user_id="123", auth_method="token")

# Avoid
logger.info(f"User authenticated with token: {auth_token}")
```

### 5. Use Exception Logging
Always use `logger.exception()` for exceptions:

```python
try:
    result = operation()
except Exception as e:
    logger.exception("Operation failed")
    # Don't use logger.error(f"Operation failed: {e}")
```

## Demo Script

Run the logging demo to see all features in action:

```bash
cd DevOps_Agent
python examples/logging_demo.py
```

This will demonstrate:
- All log levels
- Error handling with tracebacks
- Structured logging
- Performance logging
- Environment-based configuration

## Troubleshooting

### Common Issues

1. **Logs not appearing in file**
   - Check if the `logs` directory exists
   - Verify file permissions
   - Check `LOG_FILE_ENABLED` environment variable

2. **Too many log files**
   - Adjust `LOG_ROTATION` and `LOG_RETENTION` settings
   - Check available disk space

3. **Performance issues**
   - Reduce log level in production
   - Disable file logging if not needed
   - Use async logging for high-throughput scenarios

### Debug Mode
Enable debug logging to see detailed information:

```bash
export LOG_LEVEL=DEBUG
python src/main/react_agent.py
```

## Monitoring and Alerting

### Log Analysis
Use tools like `grep`, `awk`, or log analysis tools to monitor logs:

```bash
# Count errors in the last hour
grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" logs/devops_agent.log | grep "ERROR" | wc -l

# Find slow operations
grep "completed in" logs/devops_agent.log | grep -E "[0-9]+\.[0-9]+ seconds" | awk '$NF > 1.0'
```

### Integration with Monitoring Tools
The structured log format is compatible with monitoring tools like:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- Datadog
- New Relic

## Conclusion

The logging system provides comprehensive visibility into the DevOps Agent's operations, making it easier to:
- Debug issues
- Monitor performance
- Track user interactions
- Maintain audit trails
- Integrate with monitoring systems

For questions or issues with logging, refer to the loguru documentation or create an issue in the project repository. 