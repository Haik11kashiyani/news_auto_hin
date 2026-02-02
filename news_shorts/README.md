# Hindi News Shorts Automation

This system automatically fetches trending Hindi news, curates the best story using Gemini AI, generates an engaging script, creates voiceover, and compiles a vertical video for YouTube Shorts.

## Setup

1.  **Install Python Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Playwright Browsers**:

    ```bash
    playwright install chromium
    ```

3.  **Environment Variables**:
    Create a `.env` file in this directory or set the variable:
    ```
    GEMINI_API_KEY=your_api_key_here
    ```

## Usage

Run the main automation script:

```bash
python main.py
```

- The script will run immediately once, then schedule itself to run every 3 hours.
- Generated videos will appear in the `outputs/` folder.
- Processed news links are stored in `processed_news.json` to avoid duplicates.

## Features

- **Multi-Source RSS**: Fetches from Jagran, Amar Ujala, Zee News, BBC Hindi, etc.
- **AI Curation**: Gemini selects the most viral/impactful story.
- **Smart Visuals**: Automatically resizes and blurs images to fit 9:16 vertical format.
- **Karaoke Text**: Highlights words in sync with the audio (heuristic).
- **Scheduling**: Built-in 3-hour loop.
