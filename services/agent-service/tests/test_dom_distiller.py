import pytest
from app.engine.browser.dom_distiller import DOMDistiller, JS_DOM_DISTILLER


def test_js_dom_distiller_script_validity():
    assert "processNode" in JS_DOM_DISTILLER
    assert "shadowRoot" in JS_DOM_DISTILLER
    assert "form_context" in JS_DOM_DISTILLER
    assert "parent_text" in JS_DOM_DISTILLER


@pytest.mark.asyncio
async def test_extract_interactive_snapshot_empty_fallback(mocker):
    mock_page = mocker.AsyncMock()
    mock_page.evaluate.side_effect = Exception("Page crashed")

    snapshot = await DOMDistiller.extract_interactive_snapshot(mock_page)
    assert snapshot == []
