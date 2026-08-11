"""
test_stabilizer.py — Unit tests for PageNetworkStabilizer
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.engine.browser.stabilizer import PageNetworkStabilizer


@pytest.mark.asyncio
async def test_page_network_stabilizer_mock_page():
    """Verify PageNetworkStabilizer completes and returns True on quiet network."""
    mock_page = MagicMock()
    mock_page.on = MagicMock()
    mock_page.remove_listener = MagicMock()

    # Mock evaluate for loading spinner check
    mock_page.evaluate = AsyncMock(return_value=False)

    is_stable = await PageNetworkStabilizer.wait_until_stable(
        mock_page,
        timeout_ms=1000,
        quiet_window_ms=200,
    )

    assert is_stable is True
    mock_page.on.assert_called()
    mock_page.remove_listener.assert_called()


@pytest.mark.asyncio
async def test_page_network_stabilizer_none_page():
    """Verify None page reference returns True gracefully without errors."""
    is_stable = await PageNetworkStabilizer.wait_until_stable(None, timeout_ms=500)
    assert is_stable is True
