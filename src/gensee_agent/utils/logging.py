import logging
import os
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

def configure_logger(logger_name, log_level='INFO', environment=None):
    """Configures a logger with the specified name and log level.

    Args:
        logger_name: Name of the logger
        log_level: Logging level (default: INFO)
        environment: Environment ('dev', 'prod', etc.). If None, reads from ENV variable.
    """
    import os

    logger = logging.getLogger(logger_name)

    logger.setLevel(log_level)
    logger.propagate = False

    pod_name = socket.gethostname()

    # Determine environment
    if environment is None:
        environment = os.environ.get("ENV", "dev")

    sh = logging.StreamHandler(sys.stdout)

    # Use different formatters based on environment
    if environment == "dev":
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt='%(levelname).1s [%(asctime)s] [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # JSON format for production (GCP Cloud Logging)
        formatter = GCPJsonFormatter(pod_name)

    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger