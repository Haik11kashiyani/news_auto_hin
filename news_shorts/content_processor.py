import os
import json
import logging
import time
import random
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
        self.model = self._discover_and_init_model()

    def _discover_and_init_model(self):
        """
        Dynamically discovers the best available model supporting generateContent.
        Prioritizes: 2.0-flash > 1.5-flash > 1.5-pro > 1.0-pro
        """
        try:
            logging.info("🕵️ Discovering available Gemini models...")
            models = list(genai.list_models())
            
            # Filter for generateContent support
            candidates = []
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    name = m.name.lower()
                    candidates.append(name)
            
            logging.info(f"📋 Available models: {candidates}")
            
            # Priority Search
            priority_list = [
                "models/gemini-2.5-flash",
                "models/gemini-2.0-flash-exp",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-flash-latest",
                "models/gemini-1.5-flash-001",
                "models/gemini-1.5-pro",
                "models/gemini-1.5-pro-latest",
                "models/gemini-1.5-pro-001",
                "models/gemini-1.0-pro",
                "models/gemini-pro"
            ]
            
            chosen_model = None
            
            # 1. Check priority exact matches from reported list
            for p in priority_list:
                if p in candidates:
                    chosen_model = p
                    break
            
            # 2. If no exact priority match, look for partials
            if not chosen_model:
                for cand in candidates:
                    if "flash" in cand and "1.5" in cand:
                        chosen_model = cand
                        break
            
            # 3. Fallback to any valid
            if not chosen_model and candidates:
                chosen_model = candidates[0]
                
            if chosen_model:
                logging.info(f"✅ Selected Model: {chosen_model}")
                # Clean name for instantiation if needed, usually passed as is
                # genai.GenerativeModel handles 'models/' prefix or without it
                return genai.GenerativeModel(chosen_model.replace("models/", ""))
            else:
                logging.error("❌ No models found supporting 'generateContent'.")
                return genai.GenerativeModel("gemini-1.5-flash") # Blind fallback

        except Exception as e:
            logging.warning(f"⚠️ Model discovery failed: {e}. Using fallback.")
            return genai.GenerativeModel("gemini-1.5-flash") # Fallback to default

    def _generate_content_safe(self, prompt, mime_type="application/json"):
        """
        Robust wrapper for generate_content with handling for 429 (Rate Limit)
        and automatic fallback to older models if newer ones are exhausted.
        """
        retries = 3
        base_delay = 20 # seconds
        
        current_model = self.model
        
        for attempt in range(retries + 1):
            try:
                logging.info(f"🔄 Generating with {current_model.model_name} (Attempt {attempt+1}/{retries+1})...")
                response = current_model.generate_content(
                    prompt, 
                    generation_config={"response_mime_type": mime_type}
                )
                return response
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower():
                    wait_time = base_delay * (2 ** attempt) + random.uniform(1, 5)
                    logging.warning(f"⏳ Rate Limit hit (429). Sleeping for {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    
                    # If we exhausted retries with this model, or if we are already seeing persistent fails
                    if attempt >= 1:
                         logging.info("♻️ Switching to fallback model 'gemini-2.0-flash' to bypass rate limit.")
                         current_model = genai.GenerativeModel("gemini-2.0-flash")

                    if attempt == retries:
                         logging.error(f"❌ Rate limit persistent on {current_model.model_name}.")
                else:
                    # Non-rate-limit error?
                    logging.error(f"❌ API Error: {e}")
                    # If it's a 404 or other fatal error, maybe switch model?
                    if "404" in err_str:
                         logging.info("♻️ Switching to fallback model due to 404...")
                         current_model = genai.GenerativeModel("gemini-1.5-flash")
                         continue
                    break # Don't retry for random crashes unless we want to
        
        return None



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

        last_error = None
        
        try:
            logging.info(f"🔄 Trying curation with selected model...")
            response = self._generate_content_safe(prompt, mime_type="application/json")
            if not response:
                raise Exception("Max retries exceeded or API failed.")
            
            result = json.loads(response.text)
            idx = result.get("selected_index", 0)
            reason = result.get("reason", "")
            logging.info(f"✅ Selected Index {idx}: {reason}")
            
            if 0 <= idx < len(news_items):
                return news_items[idx]
            else:
                return news_items[0]
        except Exception as e:
            logging.error(f"❌ Curation Error: {e}")
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
        
        last_error = None
        try:
            logging.info(f"🔄 Trying script generation with selected model...")
            response = self._generate_content_safe(prompt, mime_type="application/json")
            if not response:
                 raise Exception("Max retries exceeded or API failed.")

            data = json.loads(response.text)
            
            # Add metadata back
            data['original_title'] = news_item['title']
            data['source'] = news_item['source']
            data['image_url'] = news_item['image']
            
            logging.info("✅ Script generated successfully.")
            return data
        except Exception as e:
            logging.error(f"❌ Script Generation Error: {e}")
            return None

if __name__ == "__main__":
    # Test
    processor = ContentProcessor()
    dummy_news = [{"title": "Test News", "source": "Test", "summary": "This is a test summary.", "image": None}]
    print(processor.generate_script(dummy_news[0]))
