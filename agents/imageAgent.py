from agno.agent import Agent
import os
import sys
import time
import shutil
import tempfile
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from tools.imagesTool import load_images_from_directory
from prompts.imagePrompts import Image_prompt
from models.gemini import model
# from agno.memory.v2.db.sqlite import SqliteMemoryDb
# from agno.memory.v2.memory import Memory

class ImageAnalysisAgent:
    def __init__(self):
        # memory_db = SqliteMemoryDb(db_file="agent_memory.db")
        # agent_memory = Memory(db=memory_db)
        self.agent = Agent(
            name="ImageAgent",
            model=model,
            markdown=False,
            description=Image_prompt,
            #  memory=agent_memory,
        )
        self.temp_dir = None

    def create_temp_directory(self):
        """Create a temporary directory for image processing"""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
        self.temp_dir = tempfile.mkdtemp()
        return self.temp_dir

    def copy_images_to_temp(self, image_directory):
        """Copy images from source directory to temp directory"""
        temp_dir = self.create_temp_directory()
        if os.path.isfile(image_directory):
            # Single image case
            shutil.copy2(image_directory, temp_dir)
        else:
            # Directory case
            for file in os.listdir(image_directory):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    shutil.copy2(os.path.join(image_directory, file), temp_dir)
        return temp_dir

    def analyze_images(self, image_path):
        """Analyze images and return the results"""
        temp_dir = self.copy_images_to_temp(image_path)
        try:
            response = self.agent.run(
                Image_prompt,
                tools_input={"load_images_from_directory": {"directory_path": temp_dir}}
            )
            return response.content
        finally:
            # Cleanup
            if self.temp_dir:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None



if __name__ == "__main__":
    agent = ImageAnalysisAgent()
    image_directory = "/Users/jayanth/Documents/GitHub/DemonSeller/Flats/flat7"
    result = agent.analyze_images(image_directory)
    print(result)
