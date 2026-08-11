import os
import pytest
from app.core.logging_config import setup_production_logging, get_logger, LOG_FILE_PATH, log_step


def test_production_logging_initialization():
    setup_production_logging()
    logger = get_logger("test")
    logger.info("Testing production logging initialization.")

    # Verify log file creation
    assert os.path.exists(LOG_FILE_PATH)
    
    # Read log file content and verify test log entry exists
    with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Testing production logging initialization." in content


def test_structured_log_step():
    setup_production_logging()
    logger = get_logger("test_step")
    log_step(logger, 99, "Testing Step Title", "Step details info")

    with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        assert "STEP 99: Testing Step Title" in content
