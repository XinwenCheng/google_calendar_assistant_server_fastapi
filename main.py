from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from helpers.extraction_helper import ExtractionHelper
from helpers.open_ai_helper import OpenAIHelper
from helpers.google_calendar_helper import GoogleCalendarHelper
from helpers.playwright_helper import PlaywrightHelper
from helpers.file_helper import FileHelper


load_dotenv()  # Load environment variables from .env file

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


browser_context = None
pending_event_data = None  # Temporarily store the conflict agenda.


@app.on_event("startup")
async def startup():
    global browser_context

    browser_context = await PlaywrightHelper.init()

    try:
        await GoogleCalendarHelper.init(context=browser_context)

    except Exception as e:
        print(f"startup() e: {e}")

        return {"status": "error", "message": "Server start up failed."}

    return {
        "status": "initialized",
        "message": "Google Calendar initialized.",
    }


@app.post("/audio-recording")
async def receive_audio(audio_blob: UploadFile = File(...)):
    global browser_context, pending_event_data

    print(
        f"receive_audio() audio_blob.filename: {audio_blob.filename}, audio_blob.size: {audio_blob.size}"
    )

    # temp_filename = f"temp_{audio_blob.filename}"

    # with open(temp_filename, "wb") as buffer:
    #     shutil.copyfileobj(
    #         audio_blob.file, buffer
    #     )  # Save the uploaded file temporarily.

    temp_filename = FileHelper.save(audio_blob)

    try:
        user_text = OpenAIHelper.audio_to_text(filename=temp_filename)

        # demoResult = ExtractionHelper.parse_text_to_event(user_text=user_text) # Demo purpose ONLY.
        # print(f"receive_audio() demoResult: ${json.dumps(demoResult)}"")

        result_json = OpenAIHelper.text_to_event(text=user_text)
        print(f"receive_audio() result_json: {result_json}")

        event_data = None

        try:
            event_data = json.loads(result_json)  # Parse JSON string to dict
            print(f"receive_audio() event_data: {event_data}")
        except json.JSONDecodeError:
            print("receive_audio() error: Failed to parse JSON from AI response")

            return {"status": "error", "message": "Invalid JSON from AI"}

        print(f"receive_audio() event_data: {event_data}")

        if "message" in event_data:
            return {"status": "error", "message": event_data["message"]}
        elif "start_time" in event_data:
            try:
                await GoogleCalendarHelper.check_conflict(
                    context=browser_context,
                    event_data=event_data,
                    user_text=user_text,
                    result_json=result_json,
                )

            except Exception as e:
                if pending_event_data is None:
                    pending_event_data = event_data

                return {"status": "conflict", "message": str(e)}

        if (
            pending_event_data is not None
            and "start_time" in event_data
            and "end_time" in event_data
        ):
            print(f"receive_audio() pending_event_data: {pending_event_data}")
            event_data["title"] = pending_event_data.get("title")

        await GoogleCalendarHelper.append_event(
            context=browser_context, event_data=event_data
        )

        pending_event_data = None

        return {"status": "succeed", "transcription": user_text, "data": result_json}

    except Exception as e:
        print(f"receive_audio() e: {e}")

        return {"status": "error", "message": str(e)}

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)  # Clean up.
