import os
from playwright.async_api import async_playwright
from helpers.storage_helper import StorageHelper


STORAGE_STATE_PATH = f"{StorageHelper.get_path('state')}"


class PlaywrightHelper:
    async def init():
        print(f"PlaywrightHelper init()")

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled"
            ],  # Hide the feature of automation or Chrome will see this as a robot.
        )
        sessionExists = os.path.exists(STORAGE_STATE_PATH)
        print(f"PlaywrightHelper init() sessionExists: {sessionExists}")

        if sessionExists:
            browser_context = await browser.new_context(
                storage_state=STORAGE_STATE_PATH
            )  # Bypass the sign in process with the existing state.
        else:
            browser_context = await browser.new_context()

        await browser_context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )  # Disable webdriver detection for avoiding the anti-scraping.

        return browser_context
