import logging
import os

from colorama import init, Fore, Back

init(autoreset=True)

_LOG_FORMAT = "%(levelname)s: %(asctime)-10s [%(name)s]: %(message)s"
_DEFAULT_LEVEL = "INFO"
_ENV_VAR_LOG_LEVEL = "HEALTHCHAIN_LOG_LEVEL"

_configured = False


class ColorFormatter(logging.Formatter):
    COLORS = {
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "CRITICAL": Fore.RED + Back.WHITE,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        if color:
            record.asctime = color + self.formatTime(record, self.datefmt)
            record.name = color + record.name
            record.levelname = color + record.levelname
            record.msg = color + record.msg
        return logging.Formatter.format(self, record)


def _get_log_level() -> int:
    """Get the log level from environment variable or default."""
    level_name = os.environ.get(_ENV_VAR_LOG_LEVEL, _DEFAULT_LEVEL).upper()
    return getattr(logging, level_name, logging.INFO)


def _configure_root_healthchain_logger() -> None:
    """Configure the root 'healthchain' logger once.

    Sets up a single console handler with color formatting on the
    top-level 'healthchain' logger. Child loggers obtained via
    ``get_logger`` inherit this handler through standard library
    propagation, so no per-module handler setup is needed.
    """
    global _configured
    if _configured:
        return

    root_logger = logging.getLogger("healthchain")
    if not root_logger.handlers:
        formatter = ColorFormatter(_LOG_FORMAT)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    root_logger.setLevel(_get_log_level())
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``healthchain`` namespace.

    All loggers share the handler and level configured on the root
    ``healthchain`` logger. The level can be controlled at runtime
    via the ``HEALTHCHAIN_LOG_LEVEL`` environment variable
    (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    _configure_root_healthchain_logger()
    return logging.getLogger(name)


# Keep backward compatibility with existing code that imports add_handlers
def add_handlers(log: logging.Logger) -> logging.Logger:
    if len(log.handlers) == 0:
        formatter = ColorFormatter(_LOG_FORMAT)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)
    return log
