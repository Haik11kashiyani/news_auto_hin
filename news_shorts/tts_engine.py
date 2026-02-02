import asyncio
import json
import os
import edge_tts
from moviepy.editor import AudioFileClip

class TTSEngine:
    def __init__(self):
        # Male Hindi Voice: hi-IN-MadhurNeural or hi-IN-SwaraNeural (Female)
        self.voice = "hi-IN-MadhurNeural" 
        self.rate = "+10%" # Slightly faster for news

    async def generate_audio(self, text, output_filename):
        """
        Generates MP3 and returns path + estimated word timings.
        """
        output_path = os.path.abspath(output_filename)
        
        # 1. Generate MP3
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(output_path)
        
        # 2. Estimate Word Timings (Heuristic)
        # Accurate word-level timestamps require Whisper or alignment. 
        # For simplicity/speed, we distribute based on length.
        
        try:
            clip = AudioFileClip(output_path)
            duration = clip.duration
            clip.close()
            
            words = text.split()
            total_chars = sum(len(w) for w in words)
            
            timings = []
            current_time = 0.0
            
            for word in words:
                # Calculate time share based on length relative to total
                word_dur = (len(word) / total_chars) * duration
                
                timings.append({
                    "word": word,
                    "start": current_time,
                    "end": current_time + word_dur
                })
                current_time += word_dur
                
            return output_path, timings
            
        except Exception as e:
            print(f"Error in TTS timing: {e}")
            return output_path, []

    def generate_sync(self, text, output_filename):
        return asyncio.run(self.generate_audio(text, output_filename))
