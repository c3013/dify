# Aliyun Trace Metrics Implementation

## Overview

This implementation adds OpenTelemetry histogram metrics to the Aliyun Trace component for tracking LLM operations. All metrics include an `app_name` tag that corresponds to the configured service name.

## Metrics

The following histogram metrics are exported to the Aliyun OTLP endpoint:

### 1. `gen_ai.client.time_to_first_token`
- **Type**: Histogram
- **Unit**: seconds (s)
- **Description**: Time to first token in LLM responses
- **Tags**: `app_name`, `operation`
- **Notes**: Only recorded when explicitly provided (not always available in current data)

### 2. `gen_ai.client.time_per_output_token`
- **Type**: Histogram
- **Unit**: seconds (s)
- **Description**: Average time per output token
- **Tags**: `app_name`, `operation`
- **Notes**: Automatically calculated as `duration / completion_tokens` if not provided

### 3. `gen_ai.client.time_between_token`
- **Type**: Histogram
- **Unit**: seconds (s)
- **Description**: Time between tokens in LLM responses
- **Tags**: `app_name`, `operation`
- **Notes**: Only recorded when explicitly provided (not always available in current data)

### 4. `gen_ai.client.operation`
- **Type**: Histogram
- **Unit**: dimensionless (1)
- **Description**: LLM operation count (value of 1 per operation)
- **Tags**: `app_name`, `operation`
- **Notes**: Used for counting operations by type

### 5. `gen_ai.usage.usage.prompt_tokens_details.cached_tokens`
- **Type**: Histogram
- **Unit**: dimensionless (1)
- **Description**: Number of cached tokens used
- **Tags**: `app_name`, `operation`
- **Notes**: Only recorded when cached tokens > 0

### 6. `gen_ai.client.operation.duration`
- **Type**: Histogram
- **Unit**: seconds (s)
- **Description**: Duration of LLM operations
- **Tags**: `app_name`, `operation`
- **Notes**: Total latency from start to finish

### 7. `gen_ai.client.token.usage`
- **Type**: Histogram
- **Unit**: dimensionless (1)
- **Description**: Token usage in LLM operations
- **Tags**: `app_name`, `operation`
- **Notes**: Total tokens (prompt + completion)

## Architecture

### Components

1. **MetricsClient** (`core/ops/aliyun_trace/data_exporter/traceclient.py`)
   - Manages OpenTelemetry metrics infrastructure
   - Creates histogram instruments for each metric type
   - Exports metrics to Aliyun OTLP endpoint
   - Automatically includes `app_name` tag in all metrics

2. **AliyunDataTrace** (`core/ops/aliyun_trace/aliyun_trace.py`)
   - Integrates metrics recording with trace span creation
   - Records metrics when LLM spans are created in workflows
   - Records metrics for message-based LLM calls

### Integration Points

Metrics are recorded at the following points:

1. **Workflow LLM Nodes** (`build_workflow_llm_span` method)
   - Extracts usage data from `process_data` and `outputs`
   - Records metrics when total_tokens > 0 and latency > 0

2. **Message LLM Calls** (`message_trace` method)
   - Calculates duration from start_time and end_time
   - Records metrics for simple chat/completion calls

## Configuration

The MetricsClient is automatically initialized with:
- **service_name**: Taken from `aliyun_config.app_name`
- **endpoint**: Same OTLP endpoint used for traces
- **export_interval**: 5000ms (5 seconds) by default

## Data Flow

```
LLM Execution
    ↓
process_data/usage extraction
    ↓
MetricsClient.record_llm_metrics()
    ↓
Histogram.record() with app_name tag
    ↓
PeriodicExportingMetricReader
    ↓
OTLPMetricExporter
    ↓
Aliyun OTLP Endpoint
```

## Usage Example

```python
# Metrics are automatically recorded when trace spans are created
# No manual intervention needed

# For workflow LLM nodes:
usage_data = {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150,
    "latency": 2.0
}
# → Metrics automatically recorded in build_workflow_llm_span()

# For message LLM calls:
trace_info = MessageTraceInfo(
    message_tokens=100,
    answer_tokens=50,
    total_tokens=150,
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(seconds=2)
)
# → Metrics automatically recorded in message_trace()
```

## Testing

Unit tests are provided in `tests/unit_tests/core/ops/aliyun_trace/test_metrics_client.py`:

- Test MetricsClient initialization
- Test basic metric recording
- Test optional field recording
- Test automatic time-per-token calculation
- Test app_name tag inclusion
- Test graceful shutdown

## Limitations and Future Enhancements

### Current Limitations

1. **Time to First Token**: Not currently captured in process_data
   - Could be added in future by tracking streaming token events

2. **Time Between Tokens**: Not currently available
   - Would require streaming event timestamps

3. **Cached Tokens**: Not currently exposed by LLM providers
   - Placeholder implemented for when this data becomes available

### Future Enhancements

1. Add streaming token event tracking for more granular timing metrics
2. Extract cached token information when LLM providers expose it
3. Add more operation types (e.g., "embedding", "reranker")
4. Add model-specific tags (provider, model name) for better filtering
