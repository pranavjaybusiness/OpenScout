"""Custom CloudWatch metrics for operational signals."""

import boto3
from botocore.exceptions import ClientError

from src.constants import (
    FEEDBACK_MATCH_NO_METRIC,
    FEEDBACK_MATCH_YES_METRIC,
    FEEDBACK_NO_RESPONSE_METRIC,
    NEGATIVE_MATCH_FEEDBACK_METRIC,
    OPENSCOUT_METRIC_NAMESPACE,
)
from src.pipeline_log import log_event

_cloudwatch_client = None


def _get_cloudwatch_client():
    global _cloudwatch_client
    if _cloudwatch_client is None:
        _cloudwatch_client = boto3.client("cloudwatch")
    return _cloudwatch_client


def _publish_count(metric_name: str) -> None:
    try:
        _get_cloudwatch_client().put_metric_data(
            Namespace=OPENSCOUT_METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": 1.0,
                    "Unit": "Count",
                }
            ],
        )
    except ClientError as e:
        log_event(
            "cloudwatch_metric_error",
            level="WARNING",
            namespace=OPENSCOUT_METRIC_NAMESPACE,
            metric=metric_name,
            error=str(e),
        )


def record_match_feedback_yes() -> None:
    _publish_count(FEEDBACK_MATCH_YES_METRIC)


def record_match_feedback_no() -> None:
    _publish_count(FEEDBACK_MATCH_NO_METRIC)
    # Keep legacy metric for existing alarms/dashboards.
    _publish_count(NEGATIVE_MATCH_FEEDBACK_METRIC)


def record_match_feedback_no_response() -> None:
    """User saw Same product? but closed/dismissed without Yes or No."""
    _publish_count(FEEDBACK_NO_RESPONSE_METRIC)
