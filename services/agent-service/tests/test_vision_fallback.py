"""
Unit and integration tests for Vision LLM Fallback & Set-of-Mark (SoM) Navigation.
Tests canvas detection, candidate bounding box generation, VisionPlannerNode reasoning,
coordinate mouse execution, and AnalyzerNode confidence discounting.
"""
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image

from app.engine.vision.som import SetOfMarksAnnotator
from app.engine.browser.dom_distiller import DOMDistiller
from app.agents.nodes.vision_planner import VisionPlannerNode
from app.agents.nodes.planner import PlannerNode
from app.agents.nodes.executor import ExecutorNode
from app.agents.nodes.analyzer import AnalyzerNode, compute_confidence
from app.engine.executor.dynamic_executor import DynamicRuntimeExecutor
from app.services.openapi_exporter import OpenAPIExporter
from app.services.markdown_exporter import MarkdownExporter


def _create_test_image_bytes(width: int = 800, height: int = 600) -> bytes:
    """Helper to generate dummy PNG image bytes."""
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_som_annotator_candidate_generation_and_drawing():
    """Verify SetOfMarksAnnotator draws numbered mark badges and generates marks registry."""
    raw_png = _create_test_image_bytes(800, 600)
    canvas_rects = [{"x": 50, "y": 50, "width": 700, "height": 500}]

    annotated_png, marks_registry = SetOfMarksAnnotator.annotate_image(raw_png, canvas_rects)

    assert len(annotated_png) > 0
    assert len(marks_registry) >= 5

    # Check mark 1 structure
    m1 = marks_registry[1]
    assert m1["mark"] == 1
    assert "x" in m1 and "y" in m1
    assert len(m1["box"]) == 4
    assert 0 <= m1["x"] <= 800
    assert 0 <= m1["y"] <= 600


@pytest.mark.asyncio
async def test_dom_distiller_has_canvas_element():
    """Verify DOMDistiller detects <canvas> elements on the page."""
    mock_page = AsyncMock()

    # 1. Page with canvas
    mock_page.evaluate = AsyncMock(return_value=True)
    assert await DOMDistiller.has_canvas_element(mock_page) is True

    # 2. Plain page without canvas
    mock_page.evaluate = AsyncMock(return_value=False)
    assert await DOMDistiller.has_canvas_element(mock_page) is False


@pytest.mark.asyncio
async def test_vision_planner_node_selection():
    """Verify VisionPlannerNode passes SoM image to Vision LLM and resolves mark coordinates."""
    mock_page = AsyncMock()
    mock_page.url = "https://figma-demo.app/canvas"

    mock_marks = {
        1: {"mark": 1, "x": 120, "y": 75, "box": [100, 50, 140, 100], "label": "Mark 1"},
        2: {"mark": 2, "x": 280, "y": 75, "box": [260, 50, 300, 100], "label": "Mark 2"},
        3: {"mark": 3, "x": 450, "y": 300, "box": [400, 250, 500, 350], "label": "Mark 3"},
    }

    mock_llm_response = MagicMock()
    mock_llm_response.content = '{"mark": 2, "action": "click", "value": "", "reasoning": "Toolbar Export API button"}'

    state = {
        "page_ref": mock_page,
        "current_url": "https://figma-demo.app/canvas",
        "goal": "Discover export endpoints",
        "interactive_elements": [],
        "frontier": [],
    }

    with patch("app.engine.vision.som.SetOfMarksAnnotator.annotate_page", new=AsyncMock(return_value=(b"fake_png", mock_marks))), \
         patch("app.agents.nodes.llm_client.get_llm") as mock_get_llm:

        mock_llm_inst = AsyncMock()
        mock_llm_inst.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm_inst

        action = await VisionPlannerNode.select_action(state)

        assert action is not None
        assert action["is_vision_action"] is True
        assert action["mark"] == 2
        assert action["coordinates"] == {"x": 280, "y": 75}
        assert action["action"] == "click"
        assert "Export API" in action["reasoning"]


@pytest.mark.asyncio
async def test_dynamic_runtime_executor_coordinate_click():
    """Verify DynamicRuntimeExecutor performs mouse.click at exact coordinates for vision actions."""
    mock_page = AsyncMock()
    mock_page.mouse = AsyncMock()
    mock_page.keyboard = AsyncMock()

    # 1. Coordinate click (fast mode test)
    executor_fast = DynamicRuntimeExecutor(mock_page, humanize=False)
    action_click = {
        "action": "click",
        "coordinates": {"x": 350, "y": 210},
        "is_vision_action": True,
    }
    res1 = await executor_fast.execute_action(action_click)
    assert res1["success"] is True
    mock_page.mouse.click.assert_called_with(350, 210)

    # 2. Coordinate click + type (fast mode test)
    action_type = {
        "action": "type",
        "coordinates": {"x": 180, "y": 90},
        "value": "My Design Project",
        "is_vision_action": True,
    }
    res2 = await executor_fast.execute_action(action_type)
    assert res2["success"] is True
    mock_page.mouse.click.assert_called_with(180, 90)
    mock_page.keyboard.type.assert_called_with("My Design Project")


def test_analyzer_node_vision_discount_and_open_api_extension():
    """Verify AnalyzerNode applies vision uncertainty discount and OpenAPI exporter tags x-vision-derived."""
    # 1. Standard DOM endpoint vs Vision-derived endpoint
    conf_standard = compute_confidence(example_count=3, schema_change_count=0, has_auth_header=False, is_vision_derived=False)
    conf_vision = compute_confidence(example_count=3, schema_change_count=0, has_auth_header=False, is_vision_derived=True)

    assert conf_standard == 0.8
    assert conf_vision == round(0.8 * 0.85, 3)
    assert conf_vision < conf_standard

    # 2. OpenAPI Exporter
    sample_endpoints = [
        {
            "template_route": "/api/v1/canvas/export",
            "method": "POST",
            "status": 200,
            "schema": {"type": "object", "properties": {"export_url": {"type": "string"}}},
            "confidence": conf_vision,
            "example_count": 1,
            "is_vision_derived": True,
        }
    ]

    spec = OpenAPIExporter.generate_spec("Canvas App", "https://figma-demo.app", sample_endpoints)
    operation = spec["paths"]["/api/v1/canvas/export"]["post"]
    assert operation.get("x-vision-derived") is True

    # 3. Markdown Exporter
    md = MarkdownExporter.generate_markdown("Canvas App", "https://figma-demo.app", sample_endpoints)
    assert "Vision Fallback" in md


@pytest.mark.asyncio
async def test_e2e_canvas_navigation_flow():
    """Simulate end-to-end canvas page exploration: empty AXTree -> Vision SoM -> Coordinate click -> Action trace."""
    mock_page = AsyncMock()
    mock_page.url = "https://draw.canvas-app.com"
    mock_page.mouse = AsyncMock()
    mock_page.keyboard = AsyncMock()

    mock_marks = {
        1: {"mark": 1, "x": 150, "y": 80, "box": [100, 60, 200, 100], "label": "Mark 1"}
    }

    state = {
        "page_ref": mock_page,
        "current_url": "https://draw.canvas-app.com",
        "interactive_elements": [],  # AXTree completely empty on canvas
        "visited_selectors": [],
        "visited_state_hashes": [],
        "frontier": [],
        "captured_endpoints": [],
        "explored_count": 0,
        "max_pages": 5,
        "needs_vision_fallback": False,
        "action_traces": [],
    }

    # Step 1: Planner detects empty frontier on canvas and triggers VisionPlannerNode
    with patch("app.engine.browser.dom_distiller.DOMDistiller.has_canvas_element", new=AsyncMock(return_value=True)), \
         patch("app.engine.vision.som.SetOfMarksAnnotator.annotate_page", new=AsyncMock(return_value=(b"png_bytes", mock_marks))), \
         patch("app.agents.nodes.llm_client.get_llm") as mock_get_llm:

        mock_resp = MagicMock(content='{"mark": 1, "action": "click", "reasoning": "Toolbar new shape button"}')
        mock_llm_inst = AsyncMock(ainvoke=AsyncMock(return_value=mock_resp))
        mock_get_llm.return_value = mock_llm_inst

        planner_state = await PlannerNode.process(state)

        assert planner_state["needs_vision_fallback"] is True
        assert planner_state["next_action"] is not None
        assert planner_state["next_action"]["is_vision_action"] is True
        assert planner_state["next_action"]["coordinates"] == {"x": 150, "y": 80}

    # Step 2: Executor executes coordinate click and logs trace
    mock_observer = MagicMock()
    mock_ep = {
        "template_route": "/api/shapes/create",
        "method": "POST",
        "status": 201,
        "response_body": {"id": "shape-123"},
    }
    mock_observer.captured_endpoints = [mock_ep]
    planner_state["network_observer"] = mock_observer

    with patch("app.engine.browser.dom_distiller.DOMDistiller.detect_login_wall", new=AsyncMock(return_value=False)), \
         patch("app.engine.browser.stabilizer.PageNetworkStabilizer.wait_until_stable", new=AsyncMock()), \
         patch("app.engine.browser.dom_distiller.DOMDistiller.extract_interactive_snapshot", new=AsyncMock(return_value=[])):

        executor_state = await ExecutorNode.process(planner_state)

        assert executor_state.get("vision_action_count") == 1
        traces = executor_state.get("action_traces", [])
        assert len(traces) == 1
        assert traces[0]["is_vision_action"] is True
        assert traces[0]["coordinates"] == {"x": 150, "y": 80}
        assert mock_page.mouse.down.called or mock_page.mouse.click.called

