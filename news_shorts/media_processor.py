import os
import requests
import google.generativeai as genai
from PIL import Image, ImageFilter
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
        Generates an image using Gemini/Imagen model as fallback.
        """
        print(f"🎨 Generating AI Image for: {prompt[:50]}...")
        try:
            # Try newer Imagen model first (from user logs)
            model_name = "imagen-4.0-fast-generate-001" 
            
            # The python SDK for Imagen is a bit distinct. 
            # Trying the standard generate_images pattern.
            # If that fails, we might need to fallback or catch.
            
            # Note: The availability depends on the specific API key tier.
            # We will try a few likely model names.
            
            result = genai.ImageGenerationModel(model_name, "v1beta").generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio="3:4", # Vertical-ish if supported, else "1:1"
                safety_filter_level="block_some",
                person_generation="allow_adult"
            )
            
            if result and result.images:
                image = result.images[0]
                path = os.path.join(self.assets_dir, filename)
                image.save(path)
                print(f"✅ AI Image saved at {path}")
                return path
                
        except Exception as e:
            print(f"⚠️ Primary image gen failed: {e}")
            try:
                # Fallback to gemini-2.0-flash-exp-image-generation?
                # Or just standard older Imagen if available?
                # Let's try a simpler call for Imagen 3 if 4 fails
                print("🔄 Retrying with 'imagen-3.0-generate-001'...")
                model = genai.ImageGenerationModel("imagen-3.0-generate-001", "v1beta")
                result = model.generate_images(prompt=prompt)
                if result and result.images:
                    image = result.images[0]
                    path = os.path.join(self.assets_dir, filename)
                    image.save(path)
                    print(f"✅ AI Image saved at {path}")
                    return path
            except Exception as e2:
                print(f"❌ AI Image generation failed completely: {e2}")
        
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
