from agno.agent import Agent
import os
import sys
import time 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from tools.imagesTool import load_images_from_directory
from prompts.videoPrompts import Video_prompt
from models.gemini import model


videoAgent = Agent(
    name="VideoAgent",
    model = model,
    markdown=False,
    description=Video_prompt,    
)


if __name__ == "__main__":
    video_path = "/Users/jayanth/Documents/GitHub/DemonSeller/Flats/flat7/WhatsApp Video 2025-02-19 at 11.04.42 PM.mp4"
    response = videoAgent.run(Video_prompt, tools_input={"extract_frames_from_video": {"video_path": video_path}})
    print(response.content)