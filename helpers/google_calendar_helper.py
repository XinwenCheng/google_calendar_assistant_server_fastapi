import asyncio
import urllib.parse
from datetime import datetime
from helpers.open_ai_helper import OpenAIHelper
from helpers.storage_helper import StorageHelper


STORAGE_STATE_PATH = f"{StorageHelper.get_path('state')}"


class GoogleCalendarHelper:
    async def open_calendar(context: any):
        page = await context.new_page()
        calenaer_url = "https://calendar.google.com/"

        await page.goto(calenaer_url)

        try:
            await page.wait_for_load_state(
                "networkidle"
            )  # Wait until the page was loaded completely.

            signInRequired = (
                "accounts.google.com" in page.url or "workspace.google.com" in page.url
            )
            print(f"initialize_google_calendar() signInRequired: {signInRequired}")

            if signInRequired:
                await page.wait_for_url(
                    f"{calenaer_url}**", timeout=0
                )  # 0 timeout means wait indefinitely
                await context.storage_state(
                    path=STORAGE_STATE_PATH
                )  # Save state after signed in for reuse.

        except Exception as e:
            print(f"initialize_google_calendar() e: {e}")

    async def check_conflict(
        context: any, event_data: object, user_text: str, result_json: object
    ):
        print(
            f"GoogleCalendarHelper check_conflict() event_data: {event_data}, user_text: {user_text}, result_json: {result_json}"
        )

        if context is None:
            raise ValueError(
                "GoogleCalendarHelper check_conflict() browser context is None."
            )
        elif event_data is None:
            raise ValueError(
                "GoogleCalendarHelper check_conflict() event_data is None."
            )

        page = await context.new_page()

        try:
            start_dt = datetime.fromisoformat(event_data.get("start_time"))
            # Agenda view for the specific date
            agenda_url = f"https://calendar.google.com/calendar/u/0/r/agenda/{start_dt.year}/{start_dt.month}/{start_dt.day}"

            await page.goto(agenda_url)
            await page.wait_for_load_state("domcontentloaded")

            # Wait for the main grid/list to appear
            main_role = page.locator("div[role='main']")
            await main_role.wait_for()

            # Extract text from the agenda view which usually contains times and titles of existing events.
            schedule_text = await main_role.inner_text()

            conflict = OpenAIHelper.check_conflict(
                schedule_text=schedule_text,
                event_data=event_data,
                user_text=user_text,
                result_json=result_json,
            )

            if conflict != None:
                raise Exception(f"Agenda conflict: {conflict.get('reason')}")

            print(
                "GoogleCalendarHelper check_conflict() No conflict detected. Proceeding to create event."
            )

        except Exception as conflict_err:
            print(
                f"GoogleCalendarHelper check_conflict() Warning: Could not check conflicts: {conflict_err}"
            )
            # Proceed anyway if conflict check fails

        finally:
            await page.close()

    async def append_event(context: any, event_data: object):
        print(f"GoogleCalendarHelper append_event() event_data: {event_data}")

        if context is None:
            raise ValueError(
                "GoogleCalendarHelper append_event() browser context is None."
            )
        elif event_data is None or "title" not in event_data:
            raise ValueError(
                f"GoogleCalendarHelper append_event() invalid event_data: {event_data}"
            )

        # Handle dates for Google Calendar URL with format: YYYYMMDDTHHMMSS or YYYYMMDD.
        # Example: https://www.google.com/calendar/render?action=TEMPLATE&text=My+Event&dates=20251225T100000Z/20251225T110000Z
        start_str = event_data.get("start_time", "").replace("-", "").replace(":", "")
        end_str = event_data.get("end_time", "").replace("-", "").replace(":", "")

        title = urllib.parse.quote(event_data.get("title", ""))

        calendar_url = (
            f"https://calendar.google.com/calendar/u/0/r/eventedit?"
            f"text={title}"
            f"&dates={start_str}/{end_str}"
        )

        page = await context.new_page()

        await page.goto(calendar_url)
        await page.wait_for_load_state("domcontentloaded")

        save_button = page.get_by_role("button", name="Save")

        await save_button.wait_for()  # Wait for it to be visible.
        await asyncio.sleep(1)  # Small delay to ensure interactivity.
        await save_button.click()
        await asyncio.sleep(2)  # Wait for saving process completed.
        await page.close()

        print(
            "GoogleCalendarHelper append_event() Event added successfully via Playwright."
        )
