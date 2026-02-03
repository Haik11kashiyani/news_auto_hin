
import os
import sys
import logging
from datetime import datetime
from rss_fetcher import RSSFetcher
from content_processor import ContentProcessor
from media_processor import MediaProcessor
from video_generator import VideoGenerator
from tts_engine import TTSEngine

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_pipeline():
    logging.info("🚀 Starting News Automation Pipeline...")
    
    # Initialize Modules
    rss = RSSFetcher()
    content_ai = ContentProcessor()
    media_proc = MediaProcessor()
    video_gen = VideoGenerator()
    tts = TTSEngine()

    # 1. Fetch Fresh News
    news_items = rss.fetch_all_news()
    if not news_items:
        logging.info("😴 No fresh news found.")
        return # Success but no work done

    # 2. Curate Best Story
    # Batch first 30 items
    batch = news_items[:30]
    selected_news = content_ai.curate_news(batch)
    
    if not selected_news:
        logging.error("❌ No news selected.")
        sys.exit(1)

    logging.info(f"🎯 Selected Story: {selected_news['title']}")
    
    # Mark as processed so we don't pick it again
    rss.mark_processed(selected_news['link'])

    # 3. Generate Script
    script_data = content_ai.generate_script(selected_news)
    if not script_data:
        logging.error("❌ Script generation failed.")
        sys.exit(1)

    # 4. Prepare Assets
    # Image
    raw_img_path = media_proc.download_image(selected_news['image'], "raw_image.jpg")
    final_img_path = "assets/temp/final_bg.png"
    
    if raw_img_path:
        processed_img = media_proc.process_image_for_shorts(raw_img_path, final_img_path)
    else:
        # Fallback? Or fail? 
        # For now, let's assume we need an image. If not, generate one?
        # TODO: Add image generation fallback if RSS has no image.
        logging.warning("⚠️ No image found in RSS. Automation might look bad.")
        logging.info("🎨 Attempting AI Image Generation...")
        ai_img_path = media_proc.generate_ai_image(selected_news['title'], "ai_generated.jpg")
        if ai_img_path:
            processed_img = media_proc.process_image_for_shorts(ai_img_path, final_img_path)
        else:
            processed_img = None 


    if not processed_img or not os.path.exists(processed_img):
        logging.error("❌ Image processing failed.")
        sys.exit(1)

    # Audio
    audio_path = "assets/temp/speech.mp3"
    _, timings = tts.generate_sync(script_data['script'], audio_path)

    # 5. Generate Video
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"outputs/NewsShort_{timestamp}.mp4"
    os.makedirs("outputs", exist_ok=True)
    
    final_video = video_gen.create_video(
        image_path=os.path.abspath(processed_img),
        headline=script_data['headline'],
        audio_path=os.path.abspath(audio_path),
        word_timings=timings,
        output_path=output_filename
    )

    if final_video:
        logging.info(f"✨ Video Created Successfully: {final_video}")
        # TODO: Upload Logic
    else:
        logging.error("❌ Video Creation Failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
