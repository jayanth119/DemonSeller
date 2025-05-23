from agno.agent import Agent
import os
import sys
import time 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from tools.imagesTool import load_images_from_directory
from prompts.imagePrompts import Image_prompt
from models.gemini import model


imageAgent = Agent(
    name="ImageAgent",
    model = model,
    markdown=False,
    description=Image_prompt,    
)


if __name__ == "__main__":
    image_directory = "/Users/jayanth/Documents/GitHub/DemonSeller/Flats/flat7"
    response = imageAgent.run(Image_prompt, tools_input={"load_images_from_directory": {"directory_path": image_directory}})
    print(response.content)