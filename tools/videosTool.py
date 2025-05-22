from agno.tools import tool
import os
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import uuid


@tool(show_result=True, stop_after_tool_call=True)
def extract_frames_from_video(video_path: str, similarity_threshold: float = 0.92, max_frames: int = 15):
    """
    Extract distinct frames from a video file based on structural similarity.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError("Valid video file path is required.")

    temp_folder = f"temp_frames_{uuid.uuid4().hex}"
    os.makedirs(temp_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, int(total_frames / max_frames))

    frame_paths = []
    saved_count = 0
    prev_gray = None
    frame_index = 0

    while saved_count < max_frames and cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            score, _ = ssim(prev_gray, gray, full=True)
            if score >= similarity_threshold:
                frame_index += frame_interval
                continue

        frame_filename = os.path.join(temp_folder, f"frame_{saved_count:04d}.jpg")
        cv2.imwrite(frame_filename, frame)
        frame_paths.append(frame_filename)
        saved_count += 1
        prev_gray = gray

        frame_index += frame_interval

    cap.release()

    if not frame_paths:
        raise ValueError("No frames were extracted from the video.")

    return frame_paths
