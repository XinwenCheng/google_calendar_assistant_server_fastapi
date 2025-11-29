import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from helpers.prompt_helper import PromptHelper


load_dotenv()  # Load environment variables from .env file

openAIClient = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
openAIModel = "gpt-5.1-2025-11-13"
whisperModel = "whisper-1"
open_ai_response_format = {"type": "json_object"}


class OpenAIHelper:
    def audio_to_text(filename: str):
        print(f"audio_to_text() filename: {filename}")

        with open(filename, "rb") as audio_file:
            transcription = openAIClient.audio.transcriptions.create(
                model=whisperModel, file=audio_file
            )  # Transcribe audio using OpenAI Whisper.
        print(f"audio_to_text() transcription.text: {transcription.text}")

        return transcription.text

    def text_to_event(text: str):
        system_prompt = PromptHelper.get_prompt_transcription_to_json()
        print(f"receive_audio() system_prompt: {system_prompt}")

        response = openAIClient.chat.completions.create(
            model=openAIModel,
            response_format=open_ai_response_format,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )

        return response.choices[0].message.content

    def check_conflict(schedule_text: str, event_data: object):
        prompt = PromptHelper.get_prompt_check_conflict(
            schedule_text=schedule_text, event_data=event_data
        )

        conflict_response = openAIClient.chat.completions.create(
            model=openAIModel,
            response_format=open_ai_response_format,
            messages=[{"role": "user", "content": prompt}],
        )

        conflict_data = json.loads(conflict_response.choices[0].message.content)

        print(
            f"OpenAIHelper check_conflict() conflict_data: {json.dumps(conflict_data)}"
        )

        if conflict_data.get("conflict"):
            print(
                f"OpenAIHelper check_conflict() conflict reason: {conflict_data.get('reason')}"
            )

            raise Exception("Conflict with existing agendas.")
