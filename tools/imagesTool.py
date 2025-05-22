
from agno.tools import tool
from agno.media import Image
import os

@tool(show_result=True, stop_after_tool_call=True)
def load_images_from_directory(directory_path):
    """
    Load images from a directory.
    """
    supported_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    image_files = [
        os.path.join(directory_path, file)
        for file in os.listdir(directory_path)
        if file.lower().endswith(supported_extensions)
    ]
    return [Image(filepath=img_path) for img_path in image_files]