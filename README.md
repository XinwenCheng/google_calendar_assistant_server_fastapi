# Setup Instructions

1. **Install Python Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Install Playwright Browsers**:
   This is required for the calendar automation to work.
   ```bash
   python3 -m playwright install
   ```

3. **Run the Server**:
   ```bash
   python3 -m uvicorn main:app --reload
   ```

# Project Overview
This project is a FastAPI-based backend service for the Google Calendar Assistant. It utilizes Playwright to automate interactions with Google Calendar, enabling programmatic management of events through browser automation where official APIs might be limited or for specific user simulation scenarios.

# Environment Dependencies & Installation
- **Python 3.8+**: Required to run the application.
- **Playwright**: Required for browser automation.

Installation steps:
1. Install Python requirements: `pip3 install -r requirements.txt`
2. Install Playwright browsers: `python3 -m playwright install`

# How to Run

1. **Start the Server**:
   ```bash
   python3 -m uvicorn main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`.

2. **First-time Google Login**:
   - When the application is triggered for the first time, a browser window (controlled by Playwright) will open.
   - Enter your Google account credentials (email and password) manually in this window.
   - Complete any 2-Step Verification if prompted.
   - Once logged in, the system will save the session state (cookies/storage) locally, allowing subsequent runs to operate without manual login (often in headless mode).

## Known Issues & Limitations
- **Bot Detection**: Google has strict anti-bot measures. Frequent logins or running in headless mode immediately might trigger CAPTCHAs or block access.
- **Session Expiry**: Saved session states may expire over time, requiring a manual re-login.
- **Performance**: Browser automation is heavier than direct API calls; expect slightly higher latency for requests.
