import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ContentProcessor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = self._get_valid_model()

    def _get_valid_model(self):
        """
        Tries to initialize a working model from a prioritized list.
        """
        candidates = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash-exp", # Experimental
            "gemini-1.0-pro",
            "gemini-pro"
        ]
        
        for model_name in candidates:
            try:
                logging.info(f"🔄 Attempting to initialize model: {model_name}")
                model = genai.GenerativeModel(model_name)
                # Dry run to verify access?
                # Note: creating the object doesn't hit API, but we'll trust the list.
                # If we really want to verify, we'd need to try a dummy generation.
                # Let's just return the first one that we "hope" works? 
                # Actually, the 404 happens at generation time usually.
                # So we should probably keep the list and try-except inside generate calls?
                # Or just assign one here?
                
                # To be safe, let's keep it simple for now and just Use the object.
                # But better strategy: The generating functions should catch the 404 and retry.
                # HOWEVER, a simple "init" check might be:
                return model
            except Exception as e:
                logging.warning(f"⚠️ Failed to init {model_name}: {e}")
        
        logging.error("❌ All model candidates failed initialization.")
        return genai.GenerativeModel("gemini-1.5-flash") # Fallback to default


    def curate_news(self, news_items):
        """
        Analyzes a list of news items and selects the best one for a viral YouTube Short.
        """
        if not news_items:
            return None

        logging.info(f"🧠 Curating {len(news_items)} news items...")

        # Prepare prompt with indexed list
        news_list_str = ""
        for i, item in enumerate(news_items):
            news_list_str += f"{i}. [{item['source']}] {item['title']}\n"

        prompt = f"""
        You are a seasoned News Editor for a Viral Hindi News Channel.
        Review the following {len(news_items)} headlines:

        {news_list_str}

        Task: Select the ONE single most impactful, viral, or interesting news story for a general Hindi audience right now.
        Criteria:
        - High broad appeal (National interest, shocking, or heartwarming).
        - Avoid overly local or boring political updates unless major.
        - Must have a clear "Hook".

        Output strictly a JSON object:
        {{
            "selected_index": <int>,
            "reason": "<short string>"
        }}
        """

        candidates = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-1.0-pro",
            "gemini-pro"
        ]

        last_error = None
        for model_name in candidates:
            try:
                logging.info(f"🔄 Trying curation with model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                result = json.loads(response.text)
                idx = result.get("selected_index", 0)
                reason = result.get("reason", "")
                logging.info(f"✅ Selected Index {idx}: {reason}")
                
                if 0 <= idx < len(news_items):
                    return news_items[idx]
                else:
                    return news_items[0]
            except Exception as e:
                logging.warning(f"⚠️ Model {model_name} failed: {e}")
                last_error = e
                continue
        
        logging.error(f"❌ Curation Error (All models failed): {last_error}")
        return news_items[0] # Fallback

    def generate_script(self, news_item):
        """
        Generates a Hindi script for the selected news item.
        """
        logging.info(f"✍️ Generating script for: {news_item['title']}")
        
        prompt = f"""
        Act as a professional Hindi News Anchor.
        Source News:
        Title: {news_item['title']}
        Summary: {news_item['summary']}

        Task: Write a 50-second engaging script for a YouTube Short (Vertical Video).
        
        Requirements:
        1. Language: Hindi (Devanagari script).
        2. Tone: Fast-paced, energetic, professional yet viral.
        3. Structure:
           - **Hook** (0-5s): Grab attention immediately.
           - **Body** (5-40s): The core news details.
           - **Conclusion** (40-50s): A quick wrap-up or question for the audience.
        4. No "Welcome to channel" intro. Start directly with the news.
        5. Provide a viral English/Hinglish Headline for the video text overlay.
        
        Output strictly a JSON object:
        {{
            "headline": "<Short Punchy Headline for Text Overlay>",
            "script": "<Full Hindi Script Text>",
            "keywords": ["<tag1>", "<tag2>", ...],
            "mood": "<energetic | serious | dramatic | happy>"
        }}
        """
        
        candidates = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-1.0-pro",
            "gemini-pro"
        ]

        last_error = None
        for model_name in candidates:
            try:
                logging.info(f"🔄 Trying script generation with model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                # Add metadata back
                data['original_title'] = news_item['title']
                data['source'] = news_item['source']
                data['image_url'] = news_item['image']
                
                logging.info("✅ Script generated successfully.")
                return data
            except Exception as e:
                logging.warning(f"⚠️ Model {model_name} failed: {e}")
                last_error = e
                continue

        logging.error(f"❌ Script Generation Error (All models failed): {last_error}")
        return None

if __name__ == "__main__":
    # Test
    processor = ContentProcessor()
    dummy_news = [{"title": "Test News", "source": "Test", "summary": "This is a test summary.", "image": None}]
    print(processor.generate_script(dummy_news[0]))
