from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from openai import OpenAI
from dotenv import load_dotenv
import os
import shutil
import json
from helpers.extraction_helper import ExtractionHelper
from helpers.open_ai_helper import OpenAIHelper
from helpers.storage_helper import StorageHelper
from helpers.google_calendar_helper import GoogleCalendarHelper


load_dotenv() # Load environment variables from .env file

openAIClient=OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
openAIModel="gpt-5.1-2025-11-13"
open_ai_response_format={ "type": "json_object" }

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return "Hey there, I'm your Google Calendar Assistant."

STORAGE_STATE_PATH = f'{StorageHelper.get_path('state')}'
playwright = None
browser = None
browser_context = None

@app.on_event("startup")
async def initialize_google_calendar():
    global playwright, browser,browser_context

    if playwright is None:
        playwright = await async_playwright().start()

    if browser is None:
        browser = await playwright.chromium.launch(
            headless=False, 
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"] # Hide the feature of automation or Chrome will see this as a robot.
        )

    sessionExists = os.path.exists(STORAGE_STATE_PATH)
    print(f'initialize_google_calendar() sessionExists: {sessionExists}')

    if sessionExists:
        browser_context = await browser.new_context(storage_state=STORAGE_STATE_PATH) # Bypass the sign in process with the existing state.
    else:
        browser_context = await browser.new_context()

    await browser_context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") # Disable webdriver detection for avoiding the anti-scraping.

    page = await browser_context.new_page()
    calenaer_url = "https://calendar.google.com/"

    await page.goto(calenaer_url)

    try:
        await page.wait_for_load_state("networkidle") # Wait until the page was loaded completely.
        
        signInRequired = "accounts.google.com" in page.url or "workspace.google.com" in page.url
        print(f'initialize_google_calendar() signInRequired: {signInRequired}')

        if signInRequired:
            await page.wait_for_url(f"{calenaer_url}**", timeout=0) # 0 timeout means wait indefinitely
            await browser_context.storage_state(path=STORAGE_STATE_PATH) # Save state after signed in for reuse.
    
    except Exception as e:
        print(f"initialize_google_calendar() e: {e}")
    
    return {"status": "initialized", "message": "Google Calendar session checked/created."}

@app.post("/audio-recording")
async def receive_audio(audio_blob: UploadFile = File(...)):
    global browser_context

    print(f"receive_audio() audio_blob.filename: {audio_blob.filename}, audio_blob.size: {audio_blob.size}")
    
    temp_filename = f"temp_{audio_blob.filename}"

    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(audio_blob.file, buffer) # Save the uploaded file temporarily.

    try:
        user_text = OpenAIHelper.audio_to_text(filename=temp_filename)
        
        # demoResult = ExtractionHelper.parse_text_to_event(user_text=user_text) # Demo purpose ONLY.
        # print(f'receive_audio() demoResult: ${json.dumps(demoResult)}')

        result_json = OpenAIHelper.text_to_event(text=user_text)
        print(f"receive_audio() result_json: {result_json}")

        try:
            event_data = json.loads(result_json) # Parse JSON string to dict
        except json.JSONDecodeError:
            print("receive_audio() error: Failed to parse JSON from AI response")

            return {"status": "error", "message": "Invalid JSON from AI"}

        # Simply see the event_data is OK if 'title' exists.
        if "title" in event_data:
            try:
                await GoogleCalendarHelper.check_conflict(context=browser_context,user_text=user_text,result_json=result_json)

            except Exception as e:
                return {"status": "error", "message": str(e)}

            await GoogleCalendarHelper.append_event(context=browser_context,event_data=event_data)

            return {"status": "processed", "transcription": user_text, "data": result_json}

    except Exception as e:
        print(f"receive_audio() e: {e}")

        return {"status": "error", "message": str(e)}
    
    finally:
        # 4. Cleanup
        if os.path.exists(temp_filename):
            os.remove(temp_filename)