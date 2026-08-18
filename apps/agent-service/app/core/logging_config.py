import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console

# Safely resolve logs directory
LOGS_DIR = os.getenv("LOGS_DIR", os.path.abspath(os.path.join(os.getcwd(), "logs")))
try:
    os.makedirs(LOGS_DIR, exist_ok=True)
    LOG_FILE_PATH = os.path.join(LOGS_DIR, "insightapi.log")
except OSError:
    LOGS_DIR = None
    LOG_FILE_PATH = None

_logging_initialized = False


def setup_production_logging(log_level: int = logging.INFO) -> None:
    """
    Initializes production-grade structured logging for InsightAPI AI.
    Configures Rich colored console formatting and optional rotating file logging.
    """
    global _logging_initialized
    if _logging_initialized:
        return

    # Ensure UTF-8 output encoding for legacy Windows terminals
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing default handlers to avoid duplication
    root_logger.handlers.clear()

    # 1. Rich Console Handler (for terminal UI logs)
    console = Console(force_terminal=True, legacy_windows=False)
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False
    )
    rich_handler.setLevel(log_level)
    root_logger.addHandler(rich_handler)

    # 2. Optional Rotating File Handler
    if LOG_FILE_PATH:
        try:
            file_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler = RotatingFileHandler(
                LOG_FILE_PATH,
                maxBytes=10 * 1024 * 1024,  # 10 MB limit
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except OSError:
            pass

    # Mute noisy third-party loggers
    for noisy_lib in ["urllib3", "asyncio", "httpx", "httpcore"]:
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    _logging_initialized = True
    target_info = f" Log file: [bold cyan]{LOG_FILE_PATH}[/bold cyan]" if LOG_FILE_PATH else ""
    logging.getLogger("insightapi.system").info(f"Production logging initialized.{target_info}")


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance for the given module name."""
    if not _logging_initialized:
        setup_production_logging()
    return logging.getLogger(f"insightapi.{name}")


# Contextual Structured Logging Helpers
def log_step(logger: logging.Logger, step_num: int, title: str, details: str = "") -> None:
    """Logs a major pipeline execution step."""
    logger.info(f"[bold yellow]STEP {step_num}: {title}[/bold yellow] {details}")


def log_risk_event(logger: logging.Logger, tier: str, decision: str, selector: str, reason: str = "") -> None:
    """Logs an action risk evaluation result."""
    color = "green" if decision == "SAFE" else "red"
    logger.info(f"Risk Classifier [{tier}] -> [[bold {color}]{decision}[/bold {color}]] Target: `{selector}` | Reason: {reason}")


def log_network_event(logger: logging.Logger, method: str, url: str, status: int, is_graphql: bool = False) -> None:
    """Logs captured network traffic."""
    tag = "[GraphQL]" if is_graphql else "[REST]"
    logger.info(f"Captured {tag} {method} {url} -> Status {status}")


def log_compliance_event(logger: logging.Logger, domain: str, action: str, details: str = "") -> None:
    """Logs compliance and rate limiting guardrail events."""
    logger.info(f"Compliance Guard [{domain}] -> {action}: {details}")
