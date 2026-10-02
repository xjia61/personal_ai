import json
import logging
import sys

from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):

    def format(self, record):

        data = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                timezone.utc
            ).isoformat(),

            "level": record.levelname,
            "event": record.getMessage(),
        }

        for field in [
            "method",
            "path",
            "status_code",
            "duration_ms",
        ]:
            if hasattr(record, field):
                data[field] = getattr(record, field)

        return json.dumps(data)


def setup_logging():

    logger = logging.getLogger("personal_ai")

    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:

        handler = logging.StreamHandler(
            sys.stdout
        )

        handler.setFormatter(
            JsonFormatter()
        )

        logger.addHandler(handler)

    return logger