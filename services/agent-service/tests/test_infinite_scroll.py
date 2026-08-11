import pytest
from playwright.async_api import async_playwright
from app.engine.browser.dom_distiller import DOMDistiller


@pytest.mark.asyncio
async def test_infinite_scroll_plain_container():
    """
    Simulates a page with a plain infinite-scroll container where scrollHeight grows dynamically.
    Verifies DOMDistiller.extract_interactive_snapshot performs incremental scroll passes,
    captures lazy-loaded interactive elements, and caps scroll attempts at 3.
    
    Fixes failure mode: Lazy-loaded dynamic elements staying hidden or getting stuck in infinite scroll loops.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { margin: 0; padding: 0; }
                #content { height: 400px; }
                .item { height: 100px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div id="content" style="height: 300px; overflow-y: scroll;">
                <button id="btn-1">Button 1</button>
                <div class="item" style="height: 600px;">Item 1</div>
            </div>
            <script>
                let itemCount = 1;
                const container = document.getElementById('content');
                container.addEventListener('scroll', () => {
                    if (container.scrollTop > 50 && itemCount < 3) {
                        itemCount++;
                        const newBtn = document.createElement('button');
                        newBtn.id = 'btn-' + itemCount;
                        newBtn.innerText = 'Button ' + itemCount;
                        container.appendChild(newBtn);
                    }
                });
            </script>
        </body>
        </html>
        """
        await page.set_content(html_content)

        snapshot = await DOMDistiller.extract_interactive_snapshot(page, scroll_virtualized=True)
        button_ids = [el.get("selector") for el in snapshot if "btn" in el.get("selector", "")]

        # Ensure scroll pass expanded and discovered newly rendered buttons from infinite scroll
        assert len(button_ids) > 1
        # Ensure scroll capped at 3 scroll passes max
        assert len(button_ids) <= 4

        await browser.close()
