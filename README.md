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
