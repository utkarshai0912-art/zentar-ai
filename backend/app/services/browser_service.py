"""
Zentar Intelligence — Browser Automation Service

Playwright-based persistent browser service for AI agents.
Supports multiple tabs, screenshots, PDF export, file operations,
form filling, and session management.
"""

import asyncio
import base64
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zentar.services.browser")


class BrowserTab:
    """Represents a single browser tab."""

    def __init__(self, tab_id: str, page):
        self.tab_id = tab_id
        self.page = page
        self.created_at = time.time()
        self.last_activity = time.time()

    def update_activity(self):
        self.last_activity = time.time()


class BrowserContext:
    """Represents a browser context (session) with cookies, localStorage."""

    def __init__(self, context_id: str, context):
        self.context_id = context_id
        self.context = context
        self.tabs: Dict[str, BrowserTab] = {}
        self.created_at = time.time()
        self.last_activity = time.time()

    def update_activity(self):
        self.last_activity = time.time()


class BrowserService:
    """Persistent browser service for AI agents using Playwright."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._default_context: Optional[BrowserContext] = None
        self._is_headless = True
        self._is_running = False

    async def start(self, headless: bool = True):
        if self._is_running:
            return
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                ]
            )
            self._is_headless = headless
            self._is_running = True
            ctx = await self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            ctx_id = str(uuid.uuid4())
            self._default_context = BrowserContext(ctx_id, ctx)
            self._contexts[ctx_id] = self._default_context
            logger.info("Browser service started (headless=%s)", headless)
        except Exception as e:
            logger.error("Failed to start browser: %s", e)
            raise

    async def stop(self):
        if not self._is_running:
            return
        for ctx in self._contexts.values():
            try:
                await ctx.context.close()
            except Exception:
                pass
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._is_running = False
        self._contexts.clear()
        logger.info("Browser service stopped")

    async def new_context(self, viewport: Optional[Dict] = None) -> str:
        if not self._is_running:
            raise RuntimeError("Browser service not started")
        ctx = await self._browser.new_context(
            viewport=viewport or {"width": 1280, "height": 720},
        )
        ctx_id = str(uuid.uuid4())
        self._contexts[ctx_id] = BrowserContext(ctx_id, ctx)
        logger.info("Created browser context: %s", ctx_id)
        return ctx_id

    async def close_context(self, context_id: str):
        ctx = self._contexts.pop(context_id, None)
        if ctx:
            await ctx.context.close()

    async def new_tab(self, url: Optional[str] = None, context_id: Optional[str] = None) -> str:
        ctx = self._get_context(context_id)
        page = await ctx.context.new_page()
        tab_id = str(uuid.uuid4())
        ctx.tabs[tab_id] = BrowserTab(tab_id, page)
        if url:
            await page.goto(url, wait_until="domcontentloaded")
        ctx.update_activity()
        return tab_id

    async def close_tab(self, tab_id: str, context_id: Optional[str] = None):
        ctx = self._get_context(context_id)
        tab = ctx.tabs.pop(tab_id, None)
        if tab:
            await tab.page.close()

    async def navigate(self, url: str, tab_id: str, context_id: Optional[str] = None):
        page = self._get_page(tab_id, context_id)
        await page.goto(url, wait_until="domcontentloaded")
        self._update_activity(tab_id, context_id)
        return {"url": page.url, "title": await page.title()}

    async def get_content(self, tab_id: str, context_id: Optional[str] = None) -> str:
        page = self._get_page(tab_id, context_id)
        content = await page.content()
        self._update_activity(tab_id, context_id)
        return content

    async def get_text(self, tab_id: str, context_id: Optional[str] = None) -> str:
        page = self._get_page(tab_id, context_id)
        text = await page.inner_text("body")
        self._update_activity(tab_id, context_id)
        return text

    async def get_title(self, tab_id: str, context_id: Optional[str] = None) -> str:
        page = self._get_page(tab_id, context_id)
        return await page.title()

    async def get_url(self, tab_id: str, context_id: Optional[str] = None) -> str:
        page = self._get_page(tab_id, context_id)
        return page.url

    async def screenshot(self, tab_id: str, context_id: Optional[str] = None) -> str:
        page = self._get_page(tab_id, context_id)
        screenshot = await page.screenshot(type="png", full_page=True)
        self._update_activity(tab_id, context_id)
        return base64.b64encode(screenshot).decode("utf-8")

    async def pdf(self, tab_id: str, context_id: Optional[str] = None) -> str:
        page = self._get_page(tab_id, context_id)
        pdf_bytes = await page.pdf(format="A4")
        self._update_activity(tab_id, context_id)
        return base64.b64encode(pdf_bytes).decode("utf-8")

    async def click(self, selector: str, tab_id: str, context_id: Optional[str] = None):
        page = self._get_page(tab_id, context_id)
        await page.click(selector)
        self._update_activity(tab_id, context_id)

    async def type_text(self, selector: str, text: str, tab_id: str, context_id: Optional[str] = None):
        page = self._get_page(tab_id, context_id)
        await page.fill(selector, text)
        self._update_activity(tab_id, context_id)

    async def select_option(self, selector: str, value: str, tab_id: str, context_id: Optional[str] = None):
        page = self._get_page(tab_id, context_id)
        await page.select_option(selector, value)
        self._update_activity(tab_id, context_id)

    async def scroll(self, delta_x: int = 0, delta_y: int = 500, tab_id: str = None, context_id: str = None):
        page = self._get_page(tab_id, context_id)
        await page.evaluate(f"window.scrollBy({delta_x}, {delta_y})")
        self._update_activity(tab_id, context_id)

    async def extract_links(self, tab_id: str, context_id: Optional[str] = None) -> List[Dict[str, str]]:
        page = self._get_page(tab_id, context_id)
        links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.innerText.trim(),
                href: a.href,
            }))
        """)
        self._update_activity(tab_id, context_id)
        return links

    async def extract_table(self, selector: str, tab_id: str, context_id: Optional[str] = None) -> List[List[str]]:
        page = self._get_page(tab_id, context_id)
        data = await page.evaluate(f"""
            () => {{
                const table = document.querySelector('{selector}');
                if (!table) return [];
                return Array.from(table.rows).map(row =>
                    Array.from(row.cells).map(cell => cell.innerText.trim())
                );
            }}
        """)
        self._update_activity(tab_id, context_id)
        return data

    async def fill_form(self, data: Dict[str, str], tab_id: str, context_id: Optional[str] = None):
        page = self._get_page(tab_id, context_id)
        for selector, value in data.items():
            try:
                await page.fill(selector, value)
            except Exception as e:
                logger.warning("Failed to fill %s: %s", selector, e)
        self._update_activity(tab_id, context_id)

    async def evaluate(self, script: str, tab_id: str, context_id: Optional[str] = None) -> Any:
        page = self._get_page(tab_id, context_id)
        result = await page.evaluate(script)
        self._update_activity(tab_id, context_id)
        return result

    async def get_cookies(self, context_id: Optional[str] = None) -> List[Dict]:
        ctx = self._get_context(context_id)
        return await ctx.context.cookies()

    async def set_cookies(self, cookies: List[Dict], context_id: Optional[str] = None):
        ctx = self._get_context(context_id)
        await ctx.context.add_cookies(cookies)

    async def wait_for_selector(self, selector: str, timeout: int = 10000, tab_id: str = None, context_id: str = None):
        page = self._get_page(tab_id, context_id)
        await page.wait_for_selector(selector, timeout=timeout)
        self._update_activity(tab_id, context_id)

    async def get_session_state(self, context_id: Optional[str] = None) -> Dict:
        ctx = self._get_context(context_id)
        tabs_info = []
        for tid, tab in ctx.tabs.items():
            try:
                tabs_info.append({
                    "tab_id": tid,
                    "url": tab.page.url,
                    "title": await tab.page.title(),
                })
            except Exception:
                tabs_info.append({"tab_id": tid, "url": "unknown", "title": "unknown"})
        return {
            "context_id": ctx.context_id,
            "tabs": tabs_info,
            "cookies_count": len(await ctx.context.cookies()),
            "created_at": ctx.created_at,
            "last_activity": ctx.last_activity,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "is_running": self._is_running,
            "is_headless": self._is_headless,
            "contexts": len(self._contexts),
            "tabs": sum(len(ctx.tabs) for ctx in self._contexts.values()),
        }

    def _get_context(self, context_id: Optional[str] = None) -> BrowserContext:
        if context_id:
            ctx = self._contexts.get(context_id)
            if not ctx:
                raise ValueError(f"Context not found: {context_id}")
            return ctx
        if not self._default_context:
            raise RuntimeError("No default browser context")
        return self._default_context

    def _get_page(self, tab_id: Optional[str] = None, context_id: Optional[str] = None):
        ctx = self._get_context(context_id)
        if tab_id:
            tab = ctx.tabs.get(tab_id)
            if not tab:
                raise ValueError(f"Tab not found: {tab_id}")
            return tab.page
        if ctx.tabs:
            return list(ctx.tabs.values())[0].page
        raise ValueError("No tabs open in this context")

    def _update_activity(self, tab_id: Optional[str] = None, context_id: Optional[str] = None):
        ctx = self._get_context(context_id)
        ctx.update_activity()
        if tab_id and tab_id in ctx.tabs:
            ctx.tabs[tab_id].update_activity()


# Global browser service instance
browser_service = BrowserService()