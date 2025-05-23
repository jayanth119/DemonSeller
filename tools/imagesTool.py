from agno.tools import tool
from agno.media import Image
import os

@tool(description="Load and analyze images from a directory")
def load_images_from_directory(directory_path: str):
    """
    Load images from a directory for analysis.
    
    Args:
        directory_path (str): Path to directory containing images
        
    Returns:
        List of Image objects for analysis
    """
    if not os.path.exists(directory_path):
        return f"Directory not found: {directory_path}"
        
    supported_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    image_files = []
    
    for file in os.listdir(directory_path):
        if file.lower().endswith(supported_extensions):
            full_path = os.path.join(directory_path, file)
            if os.path.isfile(full_path):
                image_files.append(full_path)
    
    if not image_files:
        return f"No supported image files found in {directory_path}"
    
    # Return image objects for the AI to analyze
    images = [Image(filepath=img_path) for img_path in image_files]
    return f"Loaded {len(images)} images for analysis: {[os.path.basename(f) for f in image_files]}"
