from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from openai import OpenAI
from dotenv import load_dotenv
import os
import asyncio
import shutil

# Load environment variables from .env file
load_dotenv()

openAIClient = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

STORAGE_STATE_PATH = "storage_state.json"
playwright = None
browser = None

@app.on_event("startup")
async def initialize_google_calendar():
    global playwright, browser

    if playwright is None:
        playwright = await async_playwright().start()

    if browser is None:
        browser = await playwright.chromium.launch(
            headless=False, 
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )

    # Check if storage state exists to reuse session
    if os.path.exists(STORAGE_STATE_PATH):
        print("Found existing session, trying to reuse...")
        context = await browser.new_context(storage_state=STORAGE_STATE_PATH)
    else:
        print("No existing session, starting fresh login...")
        context = await browser.new_context()

    # Disable webdriver detection
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    page = await context.new_page()
    calenaer_url = "https://calendar.google.com/"

    await page.goto(calenaer_url)

    try:
        # Wait a bit to see if we get redirected to login or calendar
        await page.wait_for_load_state("networkidle")
        
        if "accounts.google.com" in page.url or "workspace.google.com" in page.url:
            print("Login required. Please log in manually in the browser window.")
            
            await page.wait_for_url(f"{calenaer_url}**", timeout=0) # 0 timeout means wait indefinitely
            await context.storage_state(path=STORAGE_STATE_PATH)
            print("Login successful. Session saved.")
        else:
            print("Already logged in.")

    except Exception as e:
        print(f"An error occurred during initialization: {e}")

    
    return {"status": "initialized", "message": "Google Calendar session checked/created."}

@app.post("/audio-recording")
async def receive_audio(audio_blob: UploadFile = File(...)):
    print(f"Received audio: {audio_blob.filename}, size: {audio_blob.size}")
    
    # 1. Save the uploaded file temporarily
    temp_filename = f"temp_{audio_blob.filename}"

    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(audio_blob.file, buffer)

    try:
        # 2. Transcribe audio using OpenAI Whisper
        with open(temp_filename, "rb") as audio_file:
            transcription = openAIClient.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        user_text = transcription.text
        print(f"Transcribed text: {user_text}")

        # 3. Process text with LLM to get JSON
        system_prompt = """
        You are a effective calendar assistant.
        Extract event details from the user's input.
        Return ONLY a JSON object with the following keys:
        - summary (string): Title of the event
        - start_time (string): ISO 8601 format (e.g., 2023-10-27T10:00:00)
        - end_time (string): ISO 8601 format
        - description (string): Any extra details
        - location (string): Location if mentioned
        
        If the date is relative (like "tomorrow", "yesterday", "the day after tomorrow", however, user might speak in Mandarin), assume today is the current date.
        """

        response = openAIClient.chat.completions.create(
            model="gpt-3.5-turbo-0125", # or gpt-4-turbo
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )

        result_json = response.choices[0].message.content
        print(f"AI Result: {result_json}")

        return {"status": "processed", "transcription": user_text, "data": result_json}

    except Exception as e:
        print(f"Error processing audio: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        # 4. Cleanup
        if os.path.exists(temp_filename):
            os.remove(temp_filename)