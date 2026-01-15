"""
Unit tests for Aliyun Trace MetricsClient.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.ops.aliyun_trace.data_exporter.traceclient import MetricsClient


class TestMetricsClient:
    """Test cases for MetricsClient."""

    @pytest.fixture
    def mock_meter_provider(self):
        """Create a mock MeterProvider."""
        with patch("core.ops.aliyun_trace.data_exporter.traceclient.MeterProvider") as mock_provider:
            yield mock_provider

    @pytest.fixture
    def mock_otlp_exporter(self):
        """Create a mock OTLPMetricExporter."""
        with patch("core.ops.aliyun_trace.data_exporter.traceclient.OTLPMetricExporter") as mock_exporter:
            yield mock_exporter

    @pytest.fixture
    def mock_meter(self):
        """Create a mock meter with histogram instruments."""
        meter = MagicMock()
        # Mock histogram creation
        meter.create_histogram = MagicMock(return_value=MagicMock())
        return meter

    @pytest.fixture
    def metrics_client(self, mock_meter_provider, mock_otlp_exporter, mock_meter):
        """Create a MetricsClient instance with mocked dependencies."""
        # Mock the meter provider to return our mock meter
        mock_provider_instance = MagicMock()
        mock_provider_instance.get_meter = MagicMock(return_value=mock_meter)
        mock_meter_provider.return_value = mock_provider_instance

        client = MetricsClient(
            service_name="test_app",
            endpoint="http://test-endpoint:4318/v1/metrics",
        )
        return client

    def test_metrics_client_initialization(self, metrics_client):
        """Test that MetricsClient initializes properly."""
        assert metrics_client.service_name == "test_app"
        assert metrics_client.endpoint == "http://test-endpoint:4318/v1/metrics"
        assert metrics_client.meter is not None
        assert metrics_client.time_to_first_token_histogram is not None
        assert metrics_client.time_per_output_token_histogram is not None
        assert metrics_client.time_between_token_histogram is not None
        assert metrics_client.operation_histogram is not None
        assert metrics_client.cached_tokens_histogram is not None
        assert metrics_client.operation_duration_histogram is not None
        assert metrics_client.token_usage_histogram is not None

    def test_record_llm_metrics_basic(self, metrics_client):
        """Test recording basic LLM metrics."""
        metrics_client.record_llm_metrics(
            operation="llm",
            duration=1.5,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        # Verify that histograms were called
        metrics_client.operation_histogram.record.assert_called()
        metrics_client.operation_duration_histogram.record.assert_called()
        metrics_client.token_usage_histogram.record.assert_called()

    def test_record_llm_metrics_with_optional_fields(self, metrics_client):
        """Test recording LLM metrics with optional fields."""
        metrics_client.record_llm_metrics(
            operation="llm",
            duration=2.0,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cached_tokens=20,
            time_to_first_token=0.5,
            time_per_output_token=0.02,
            time_between_token=0.01,
        )

        # Verify that all histograms were called
        metrics_client.operation_histogram.record.assert_called()
        metrics_client.operation_duration_histogram.record.assert_called()
        metrics_client.token_usage_histogram.record.assert_called()
        metrics_client.cached_tokens_histogram.record.assert_called()
        metrics_client.time_to_first_token_histogram.record.assert_called()
        metrics_client.time_per_output_token_histogram.record.assert_called()
        metrics_client.time_between_token_histogram.record.assert_called()

    def test_record_llm_metrics_calculates_time_per_token(self, metrics_client):
        """Test that time per output token is calculated when not provided."""
        metrics_client.record_llm_metrics(
            operation="llm",
            duration=2.0,
            prompt_tokens=100,
            completion_tokens=50,  # 2.0 / 50 = 0.04 seconds per token
            total_tokens=150,
        )

        # Verify that time_per_output_token_histogram was called
        metrics_client.time_per_output_token_histogram.record.assert_called()
        # Check that the calculated value is correct (0.04)
        call_args = metrics_client.time_per_output_token_histogram.record.call_args
        assert call_args[0][0] == 0.04  # duration / completion_tokens

    def test_record_llm_metrics_includes_app_name_tag(self, metrics_client):
        """Test that all metrics include the app_name tag."""
        metrics_client.record_llm_metrics(
            operation="llm",
            duration=1.5,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        # Verify that the app_name tag is included in attributes
        for histogram in [
            metrics_client.operation_histogram,
            metrics_client.operation_duration_histogram,
            metrics_client.token_usage_histogram,
        ]:
            call_args = histogram.record.call_args
            if call_args:
                attributes = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("attributes", {})
                assert "app_name" in attributes
                assert attributes["app_name"] == "test_app"

    def test_metrics_client_shutdown(self, metrics_client):
        """Test that MetricsClient can be shut down gracefully."""
        metrics_client.shutdown()
        # Verify shutdown was called on meter provider
        metrics_client.meter_provider.shutdown.assert_called_once()
