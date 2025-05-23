from agno.tools import tool
import os
import cv2
import tempfile
from agno.media import Image

@tool(description="Extract frames from video for analysis")
def extract_frames_from_video(video_path: str, max_frames: int = 10):
    """
    Extract representative frames from a video file.
    
    Args:
        video_path (str): Path to the video file
        max_frames (int): Maximum number of frames to extract
        
    Returns:
        List of extracted frame paths or error message
    """
    if not os.path.isfile(video_path):
        return f"Video file not found: {video_path}"
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return f"Cannot open video file: {video_path}"
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            return "Video has no frames"
        
        # Calculate frame interval
        frame_interval = max(1, total_frames // max_frames)
        
        # Create temp directory for frames
        temp_dir = tempfile.mkdtemp()
        frame_paths = []
        
        frame_count = 0
        saved_count = 0
        
        while saved_count < max_frames and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                frame_filename = os.path.join(temp_dir, f"frame_{saved_count:04d}.jpg")
                cv2.imwrite(frame_filename, frame)
                frame_paths.append(frame_filename)
                saved_count += 1
                
            frame_count += 1
        
        cap.release()
        
        if not frame_paths:
            return "No frames could be extracted from video"
        
        # Convert to Image objects for analysis
        images = [Image(filepath=frame_path) for frame_path in frame_paths]
        return f"Extracted {len(frame_paths)} frames from video for analysis"
        
    except Exception as e:
        return f"Error processing video: {str(e)}"