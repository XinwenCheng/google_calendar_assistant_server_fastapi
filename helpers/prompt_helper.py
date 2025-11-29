from datetime import datetime


class PromptHelper:
    def get_prompt_transcription_to_json():
        current_date = datetime.now().strftime("%Y-%m-%d %A")

        return f"""
        You are a effective calendar assistant.
        Today is {current_date}.
        Extract event details from the user's input.
        Return ONLY a JSON object with the following keys:
        - title (string): Title of the event
        - start_time (string): ISO 8601 format (e.g., 2023-10-27T10:00:00)
        - end_time (string): ISO 8601 format
        
        If the date is relative (like "tomorrow", "yesterday", "the day after tomorrow", however, user might speak in English or Mandarin), calculate the exact date based on today ({current_date}).

        If you cannot understand user's input or cannot extract available information to generate the JSON object, please guide user to provide useful and detailed information politely.
        """

    def get_prompt_check_conflict(schedule_text: str, event_data: object):
        if schedule_text is None:
            raise ValueError(
                "PromptHelper get_prompt_check_conflict() schedule_text is None."
            )
        elif (
            event_data is None
            or "start_time" not in event_data
            or "end_time" not in event_data
        ):
            raise ValueError(
                f"PromptHelper get_prompt_check_conflict() invalid event_data: {event_data}"
            )

        return f"""
        Analyze the following schedule text from Google Calendar and determine if the new event conflicts with any existing events.
        
        Existing Schedule Text:
        {schedule_text}
        
        New Event:
        Start: {event_data.get("start_time")}
        End: {event_data.get("end_time")}
        
        Return JSON: {{ "conflict": boolean, "reason": "explanation of conflict or 'No conflict'" }}
        """
