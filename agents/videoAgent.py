from agno.agent import Agent
import os
import sys
import cv2
import tempfile
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from tools.imagesTool import load_images_from_directory
from prompts.videoPrompts import Video_prompt
from models.gemini import model

class VideoAnalysisAgent:
    def __init__(self):
        self.agent = Agent(
            name="VideoAgent",
            model=model,
            markdown=False,
            description=Video_prompt,
        )
        self.temp_dir = None

    def create_temp_directory(self):
        """Create a temporary directory for video frame extraction"""
        if self.temp_dir:
            self.cleanup()
        self.temp_dir = tempfile.mkdtemp()
        return self.temp_dir

    def extract_frames(self, video_path, frame_interval=30):
        """Extract frames from video at specified intervals"""
        temp_dir = self.create_temp_directory()
        frames_dir = os.path.join(temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video file: {video_path}")

            frame_count = 0
            saved_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_interval == 0:
                    frame_path = os.path.join(frames_dir, f"frame_{saved_count:04d}.jpg")
                    cv2.imwrite(frame_path, frame)
                    saved_count += 1

                frame_count += 1

            cap.release()
            return frames_dir

        except Exception as e:
            self.cleanup()
            raise Exception(f"Error processing video: {str(e)}")

    def analyze_video(self, video_path):
        """Analyze video and return the results"""
        frames_dir = self.extract_frames(video_path)
        try:
            response = self.agent.run(
                Video_prompt,
                tools_input={"load_images_from_directory": {"directory_path": frames_dir}}
            )
            return response.content
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None


if __name__ == "__main__":
    agent = VideoAnalysisAgent()
    video_path = "/Users/jayanth/Documents/GitHub/DemonSeller/Flats/flat7/WhatsApp Video 2025-02-19 at 11.04.42 PM.mp4"
    result = agent.analyze_video(video_path)
    print(result)