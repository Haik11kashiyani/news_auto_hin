import os
import requests
from PIL import Image, ImageFilter
from io import BytesIO

class MediaProcessor:
    def __init__(self):
        self.assets_dir = "assets/temp"
        os.makedirs(self.assets_dir, exist_ok=True)

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
