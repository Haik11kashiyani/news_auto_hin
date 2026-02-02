import os
import asyncio
import json
import logging
import urllib.parse
from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip, AudioArrayClip
import nest_asyncio
from playwright.async_api import async_playwright

nest_asyncio.apply()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoGenerator:
    def __init__(self):
        self.width = 1080
        self.height = 1920
        self.template_path = os.path.abspath("news_shorts/templates/news_scene.html")
        self.temp_dir = "assets/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    async def _render_scene(self, image_path, headline, duration, word_timings):
        """
        Renders the scene frame-by-frame using Playwright.
        """
        scene_id = hash(headline)
        frames_dir = os.path.join(self.temp_dir, f"frames_{scene_id}")
        os.makedirs(frames_dir, exist_ok=True)

        # Prepare URL
        img_url = f"file:///{image_path.replace(os.sep, '/')}"
        headline_enc = urllib.parse.quote(headline)
        url = f"file:///{self.template_path.replace(os.sep, '/')}?img={img_url}&headline={headline_enc}"

        fps = 30
        total_frames = int(duration * fps)
        frames = []

        logging.info(f"   🎬 Rendering {total_frames} frames for scene...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = await browser.new_page(viewport={"width": self.width, "height": self.height})
            
            await page.goto(url)
            
            # Inject Subtitles
            # word_timings is list of {word, start, end}
            json_timings = json.dumps(word_timings)
            await page.evaluate(f"window.setSubtitles({json_timings})")
            
            await page.wait_for_timeout(500) # Warmup

            for i in range(total_frames):
                t = i / fps
                await page.evaluate(f"window.seek({t})")
                
                path = os.path.join(frames_dir, f"frame_{i:04d}.png")
                await page.screenshot(path=path, type="png")
                frames.append(path)
            
            await browser.close()
        
        return frames

    def create_video(self, image_path, headline, audio_path, word_timings, output_path):
        """
        Main entry point to create a video from assets.
        """
        try:
            # 1. Load Audio to get duration
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # 2. Render Frames via Playwright
            frames = asyncio.run(self._render_scene(image_path, headline, duration, word_timings))
            
            if not frames:
                logging.error("❌ No frames rendered!")
                return None
                
            # 3. Assemble Video
            video_clip = ImageSequenceClip(frames, fps=30)
            video_clip = video_clip.set_audio(audio_clip)
            
            # 4. Write File
            video_clip.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", threads=4)
            logging.info(f"✅ Video saved: {output_path}")
            
            return output_path
            
        except Exception as e:
            logging.error(f"❌ Video Generation Error: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    # Dummy Test
    pass
