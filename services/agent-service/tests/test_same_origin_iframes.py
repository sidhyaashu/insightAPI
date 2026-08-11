import pytest
from playwright.async_api import async_playwright
from app.engine.browser.dom_distiller import DOMDistiller


@pytest.mark.asyncio
async def test_same_origin_iframe_recursion():
    """
    Simulates a page containing both same-origin and cross-origin iframes.
    Verifies DOMDistiller recurses into same-origin iframes to extract interactive controls
    while safely skipping cross-origin iframes.
    
    Fixes failure mode: Embedded widget/form controls inside same-origin iframe elements being missed.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Iframe Test</title></head>
        <body>
            <button id="main-btn">Main Button</button>
            <iframe id="same-origin-frame" srcdoc="<html><body><button id='iframe-btn'>Iframe Inner Button</button></body></html>"></iframe>
            <iframe id="cross-origin-frame" src="https://example.com"></iframe>
        </body>
        </html>
        """
        await page.set_content(html_content)
        await page.wait_for_timeout(500)

        snapshot = await DOMDistiller.extract_interactive_snapshot(page, scroll_virtualized=False)
        texts = [el.get("text") for el in snapshot]

        assert "Main Button" in texts
        assert "Iframe Inner Button" in texts

        await browser.close()
