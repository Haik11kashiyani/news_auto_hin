import os
import requests
import json
import base64
import random
import google.generativeai as genai
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from io import BytesIO

class MediaProcessor:
    def __init__(self):
        self.assets_dir = "assets/temp"
        os.makedirs(self.assets_dir, exist_ok=True)
        
        # Configure GenAI
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)

    def generate_ai_image(self, prompt, filename="ai_generated.jpg"):
        """
        Generates an image using Gemini/Imagen model via REST API (Robuster than SDK).
        """
        print(f"🎨 Generating AI Image for: {prompt[:50]}...")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found.")
            return None

        # Try Imagen 4.0 Fast via REST (Available in user logs)
        # Endpoint for v1beta
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-fast-generate-001:predict?key={api_key}"
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "instances": [
                {
                    "prompt": f"Professional news thumbnail, high quality, realistic: {prompt}",
                    "aspectRatio": "3:4" # Supported by Imagen 3
                }
            ],
            "parameters": {
                "sampleCount": 1
            }
        }

        try:
            print(f"🔄 POST {url.split('?')[0]}...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"⚠️ Image Gen Failed ({response.status_code}): {response.text}")
                # Fallback to older model if 3.0 fails?
                return None
                
            result = response.json()
            # Parse 'predictions' -> 'bytesBase64Encoded'
            # Structure usually: {"predictions": [{"bytesBase64Encoded": "..."}]}
            
            if "predictions" in result and result["predictions"]:
                b64_data = result["predictions"][0].get("bytesBase64Encoded")
                if not b64_data:
                     # Check alternate structure (mimeType/bytesBase64Encoded)
                     b64_data = result["predictions"][0].get("bytesBase64Encoded")
                
                if b64_data:
                    img_data = base64.b64decode(b64_data)
                    image = Image.open(BytesIO(img_data))
                    path = os.path.join(self.assets_dir, filename)
                    image.save(path)
                    print(f"✅ AI Image saved at {path}")
                    return path
            
            print(f"❌ No image data in response: {result.keys()}")
            return self._create_gradient_fallback(prompt, filename)

        except Exception as e:
            print(f"❌ AI Image generation exception: {e}")
            return self._create_gradient_fallback(prompt, filename)
        
        return None

    def _create_gradient_fallback(self, text, filename):
        """
        Creates a local gradient image if AI generation fails.
        """
        try:
            print("🎨 Creating fallback gradient image...")
            width, height = 1024, 1024
            image = Image.new("RGB", (width, height), "#000000")
            draw = ImageDraw.Draw(image)
            
            # Simple Vertical Gradient (Dark Red to Black or Blue to Black)
            # Pick a random color scheme
            colors = [
                ((139, 0, 0), (0, 0, 0)), # Dark Red
                ((0, 0, 139), (0, 0, 0)), # Dark Blue
                ((50, 50, 50), (10, 10, 10)) # Dark Grey
            ]
            top_color, bottom_color = random.choice(colors)
            
            for y in range(height):
                r = int(top_color[0] + (bottom_color[0] - top_color[0]) * y / height)
                g = int(top_color[1] + (bottom_color[1] - top_color[1]) * y / height)
                b = int(top_color[2] + (bottom_color[2] - top_color[2]) * y / height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Add simple text overlay if possible
            # Using default font since we can't guarantee system fonts
            # For better results, one would bundle a .ttf file
            
            # Draw a center box
            box_w, box_h = 800, 200
            box_x, box_y = (width - box_w)//2, (height - box_h)//2
            draw.rectangle([box_x, box_y, box_x+box_w, box_y+box_h], outline="white", width=5)
            
            # We can't easily center text with load_default() font as it's tiny
            # So we rely on the video_generator's HTML overlay for the actual reading.
            # This just provides a "Newsy" texture.
            
            path = os.path.join(self.assets_dir, filename)
            image.save(path)
            print(f"✅ Fallback Image saved at {path}")
            return path
        except Exception as e:
            print(f"❌ Fallback generation failed: {e}")
            return None

    def download_image(self, url, filename):
        if not url:
            return None
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                path = os.path.join(self.assets_dir, filename)
                with open(path, 'wb') as f:
                    f.write(response.content)
                return path
        except Exception as e:
            print(f"Error downloading image: {e}")
        return None

    def process_image_for_shorts(self, image_path, output_path):
        """
        Converts any image into a 1080x1920 vertical format.
        - Background: Blurrred, zoomed version of original.
        - Foreground: Sharp original centered.
        """
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            original = Image.open(image_path).convert("RGBA")
            target_size = (1080, 1920)
            
            # Create Background
            # Resize to fill height/width based on aspect ratio to ensure coverage
            bg = original.copy()
            bg_ratio = bg.width / bg.height
            target_ratio = target_size[0] / target_size[1]
            
            if bg_ratio > target_ratio: # Wider than target
                new_height = target_size[1]
                new_width = int(new_height * bg_ratio)
            else: # Taller than target
                new_width = target_size[0]
                new_height = int(new_width / bg_ratio)
                
            bg = bg.resize((new_width, new_height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
            
            # Center Crop Background to exact 1080x1920
            left = (bg.width - target_size[0]) / 2
            top = (bg.height - target_size[1]) / 2
            bg = bg.crop((left, top, left + target_size[0], top + target_size[1]))
            
            # Create Foreground
            # Max width 1000, Max height 1000 (roughly)
            fg = original.copy()
            fg.thumbnail((950, 950), Image.Resampling.LANCZOS)
            
            # Center Foreground
            fg_x = (target_size[0] - fg.width) // 2
            fg_y = (target_size[1] - fg.height) // 2
            
            # specific request: "if image is small then fixed that as well"
            # The blurring technique handles small images by stretching them for BG
            # and keeping them sharp for FG.
            
            bg.paste(fg, (fg_x, fg_y), fg)
            
            bg.save(output_path)
            return output_path
            
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
