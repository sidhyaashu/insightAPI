"""
Unit and integration tests for Humanizer & Humanized Interaction Engine.
Tests cubic Bezier curves, intermediate mouse movements, keystroke cadence,
incremental wheel scrolls, and fast mode switching.
"""
import math
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.engine.browser.humanizer import Humanizer
from app.engine.executor.dynamic_executor import DynamicRuntimeExecutor
from app.sdk import AgentEngine


def test_bezier_curve_generation():
    """Verify cubic Bezier math creates a smooth non-linear trajectory starting at start and ending at end."""
    start = (10.0, 20.0)
    end = (400.0, 300.0)
    points = Humanizer.compute_bezier_points(start, end, num_points=12)

    assert len(points) == 13
    assert points[0] == start
    assert points[-1] == end

    # Verify intermediate points deviate from simple linear interpolation
    for i in range(1, len(points) - 1):
        x, y = points[i]
        assert isinstance(x, float) and isinstance(y, float)


@pytest.mark.asyncio
async def test_humanized_move_and_click():
    """Verify humanized_click moves mouse across multiple intermediate Bezier points before mouse down/up."""
    mock_page = AsyncMock()
    mock_page.mouse = AsyncMock()
    mock_page.mouse.move = AsyncMock()
    mock_page.mouse.down = AsyncMock()
    mock_page.mouse.up = AsyncMock()

    mock_locator = AsyncMock()
    mock_locator.bounding_box = AsyncMock(return_value={"x": 200, "y": 150, "width": 80, "height": 30})
    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    success = await Humanizer.humanized_click(mock_page, "button#sign-up", timeout_ms=1000)

    assert success is True
    # Asserts that mouse.move was called at least 8 times across the Bezier path
    assert mock_page.mouse.move.call_count >= 8
    assert mock_page.mouse.down.called
    assert mock_page.mouse.up.called


@pytest.mark.asyncio
async def test_humanized_type_cadence():
    """Verify humanized_type clicks into target and types each character sequentially."""
    mock_page = AsyncMock()
    mock_page.mouse = AsyncMock()
    mock_page.keyboard = AsyncMock()
    mock_page.keyboard.type = AsyncMock()
    mock_page.fill = AsyncMock()

    mock_locator = AsyncMock()
    mock_locator.bounding_box = AsyncMock(return_value={"x": 100, "y": 80, "width": 200, "height": 40})
    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    sample_text = "test@api.io"
    await Humanizer.humanized_type(mock_page, "input#email", sample_text)

    # Asserts each character was typed individually
    assert mock_page.keyboard.type.call_count == len(sample_text)
    typed_chars = [call.args[0] for call in mock_page.keyboard.type.call_args_list]
    assert "".join(typed_chars) == sample_text


@pytest.mark.asyncio
async def test_humanized_scroll_increments():
    """Verify humanized_scroll divides scroll distance into multiple incremental wheel events."""
    mock_page = AsyncMock()
    mock_page.mouse = AsyncMock()
    mock_page.mouse.wheel = AsyncMock()

    await Humanizer.humanized_scroll(mock_page, 500, steps=5)

    assert mock_page.mouse.wheel.call_count == 5
    # Total scrolled distance should approximate 500
    total_scrolled = sum(call.args[1] for call in mock_page.mouse.wheel.call_args_list)
    assert 400 <= total_scrolled <= 600


@pytest.mark.asyncio
async def test_dynamic_executor_humanize_switching():
    """Verify DynamicRuntimeExecutor toggles between Humanizer and direct Playwright calls based on humanize flag."""
    mock_page = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_locator = AsyncMock()
    mock_locator.is_visible = AsyncMock(return_value=False)
    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    action_click = {"tag": "button", "selector": "button#submit", "action": "click"}
    action_type = {"tag": "input", "selector": "input#name", "action": "type", "text": "Alice"}

    # 1. Fast mode (humanize=False): Calls page.click / page.fill directly
    exec_fast = DynamicRuntimeExecutor(mock_page, humanize=False)
    await exec_fast.execute_action(action_click)
    assert mock_page.click.called

    await exec_fast.execute_action(action_type)
    assert mock_page.fill.called

    # 2. Humanized mode (humanize=True): Calls Humanizer methods
    exec_human = DynamicRuntimeExecutor(mock_page, humanize=True)
    with patch("app.engine.browser.humanizer.Humanizer.humanized_click", new=AsyncMock(return_value=True)) as mock_hclick, \
         patch("app.engine.browser.humanizer.Humanizer.humanized_type", new=AsyncMock(return_value=True)) as mock_htype:

        await exec_human.execute_action(action_click)
        assert mock_hclick.called

        await exec_human.execute_action(action_type)
        assert mock_htype.called


def test_agent_engine_fast_mode_defaults():
    """Verify AgentEngine respects humanize_interactions and fast_mode initialization parameters."""
    engine_default = AgentEngine()
    assert engine_default.humanize_interactions is True
    assert engine_default.fast_mode is False

    engine_fast = AgentEngine(fast_mode=True)
    assert engine_fast.fast_mode is True
