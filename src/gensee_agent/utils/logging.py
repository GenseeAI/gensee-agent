import logging
import socket
import sys
import json
from datetime import datetime


class GCPJsonFormatter(logging.Formatter):
    """Formats logs as JSON for GCP Cloud Logging."""

    def __init__(self, pod_name):
        super().__init__()
        self.pod_name = pod_name

    def format(self, record):
        log_obj = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            },
            "pod_name": self.pod_name,
            "logger_name": record.name
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)

def configure_logger(logger_name, log_level='INFO'):
    """Configures a logger with the specified name and log level."""
    logger = logging.getLogger(logger_name)

    logger.setLevel(log_level)
    logger.propagate = False

    pod_name = socket.gethostname()

    # Use JSON formatter for GCP Cloud Logging
    formatter = GCPJsonFormatter(pod_name)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger