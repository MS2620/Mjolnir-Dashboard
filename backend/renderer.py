import asyncio
import io
from PIL import Image
from playwright.async_api import async_playwright


class DashboardRenderer:
    def __init__(self, url: str, width: int = 640, height: int = 480):
        self.url = url
        self.width = width
        self.height = height
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--disable-gpu",
                "--hide-scrollbars",
            ],
        )

        self.page = await self.browser.new_page(
            viewport={
                "width": self.width,
                "height": self.height,
            },
            device_scale_factor=1,
        )

        await self.page.goto(
            self.url,
            wait_until="networkidle",
        )

        await self.page.evaluate(
            """
            () => {
                document.documentElement.style.width = '640px';
                document.documentElement.style.height = '480px';
                document.body.style.width = '640px';
                document.body.style.height = '480px';
                document.body.style.overflow = 'hidden';
            }
            """
        )

    async def screenshot(self) -> Image.Image:
        image_bytes = await self.page.screenshot(
            type="png",
            full_page=False,
            animations="allow",
        )

        image = Image.open(io.BytesIO(image_bytes))
        return image.convert("RGB")

    async def close(self):
        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()