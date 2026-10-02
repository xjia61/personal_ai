import json
import logging

from app.core.logging_config import JsonFormatter


def test_json_logging():

    record = logging.LogRecord(
        name="personal_ai",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="api_request",
        args=(),
        exc_info=None,
    )

    record.method = "GET"
    record.status_code = 200
    record.duration_ms = 12.5

    formatter = JsonFormatter()

    result = json.loads(
        formatter.format(record)
    )

    assert result["event"] == "api_request"
    assert result["method"] == "GET"
    assert result["status_code"] == 200
    assert result["duration_ms"] == 12.5