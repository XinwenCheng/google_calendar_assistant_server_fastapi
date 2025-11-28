from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import os
import asyncio

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
            
            await page.wait_for_url(calenaer_url+"**", timeout=0) # 0 timeout means wait indefinitely            
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
    
    return {"status": "received", "filename": audio_blob.filename}