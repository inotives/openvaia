"""Browser tool — web browsing via Playwright (lazy-loaded)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

BROWSER_TOOL = {
    "name": "browser",
    "description": (
        "Browse a web page and extract its content. "
        "Use for reading documentation, checking deployments, or fetching reference material."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to visit"},
            "action": {
                "type": "string",
                "enum": ["get_text", "get_html", "screenshot", "click", "fill"],
                "description": "Action to perform (default: get_text)",
            },
            "selector": {"type": "string", "description": "CSS selector for click/fill actions"},
            "value": {"type": "string", "description": "Value for fill action"},
        },
        "required": ["url"],
    },
}

MAX_OUTPUT_CHARS = 50_000


# Module-level shared browser state (singleton across all agents)
_shared_pw = None
_shared_browser = None
_shared_context = None


async def _ensure_shared_browser():
    """Lazy-init shared Playwright browser (singleton)."""
    global _shared_pw, _shared_browser, _shared_context
    if _shared_browser is not None:
        return _shared_browser, _shared_context
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
        )
    _shared_pw = await async_playwright().start()
    _shared_browser = await _shared_pw.chromium.launch(headless=True)
    _shared_context = await _shared_browser.new_context()
    return _shared_browser, _shared_context


class BrowserTool:
    """Web browsing via Playwright. Shares a single browser instance across all agents."""

    async def _ensure_browser(self) -> None:
        browser, context = await _ensure_shared_browser()
        self._browser = browser
        self._context = context

    async def execute(
        self,
        url: str,
        action: str = "get_text",
        selector: str | None = None,
        value: str | None = None,
    ) -> str:
        try:
            await self._ensure_browser()
        except Exception as e:
            return f"Error: Browser not available: {e}"

        page = await self._context.new_page()
        try:
            await page.goto(url, timeout=30000)

            if action == "get_text":
                text = await page.inner_text("body")
                if len(text) > MAX_OUTPUT_CHARS:
                    text = text[:MAX_OUTPUT_CHARS] + "\n... (truncated)"
                return text
            elif action == "get_html":
                html = await page.content()
                if len(html) > MAX_OUTPUT_CHARS:
                    html = html[:MAX_OUTPUT_CHARS] + "\n... (truncated)"
                return html
            elif action == "screenshot":
                buf = await page.screenshot()
                return f"[Screenshot taken: {len(buf)} bytes of {url}]"
            elif action == "click":
                if not selector:
                    return "Error: 'selector' is required for click action"
                await page.click(selector)
                return f"Clicked '{selector}' on {url}"
            elif action == "fill":
                if not selector or value is None:
                    return "Error: 'selector' and 'value' are required for fill action"
                await page.fill(selector, value)
                return f"Filled '{selector}' on {url}"
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"Error browsing {url}: {e}"
        finally:
            await page.close()

    async def close(self) -> None:
        """Shut down the shared browser."""
        global _shared_browser, _shared_pw, _shared_context
        if _shared_browser:
            await _shared_browser.close()
            _shared_browser = None
        if _shared_pw:
            await _shared_pw.stop()
            _shared_pw = None
        _shared_context = None
