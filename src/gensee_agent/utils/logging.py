import logging
import socket
import sys

def configure_logger(logger_name, log_level='INFO'):
    """Configures a logger with the specified name and log level."""
    logger = logging.getLogger(logger_name)

    logger.setLevel(log_level)
    logger.propagate = False

    pod_name = socket.gethostname()

    formatter = logging.Formatter(f'%(levelname).1s [%(asctime)s] [%(name)s:%(lineno)d] [{pod_name}] %(message)s')

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger