from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import os
import shutil
from PIL import Image
import json

# Import your agent (adjust the import path as needed)
from agents.mainAgent import flat_seller_team

app = FastAPI(title="FlatSeller AI API", version="1.0.0")

# Add CORS middleware for Streamlit communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextInput(BaseModel):
    text_content: str

class AnalysisResponse(BaseModel):
    success: bool
    message: str
    analysis: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "FlatSeller AI API is running!"}

@app.post("/analyze-text", response_model=AnalysisResponse)
async def analyze_text(text_input: TextInput):
    """Analyze flat data from text description only"""
    try:
        full_message = f"""
        Text Description: {text_input.text_content}
        
        Please provide a comprehensive analysis of this flat/property including:
        1. Key features and highlights
        2. Market positioning
        3. Target audience
        4. Selling points
        5. Pricing recommendations (if applicable)
        
        Generate a compelling sales pitch based on the provided data.
        """
        
        response = flat_seller_team.run(full_message)
        
        # Handle different response types
        if hasattr(response, 'content'):
            analysis_result = response.content
        else:
            analysis_result = str(response)
            
        return AnalysisResponse(
            success=True,
            message="Analysis completed successfully",
            analysis=analysis_result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/analyze-multimodal", response_model=AnalysisResponse)
async def analyze_multimodal(
    text_file: Optional[UploadFile] = File(None),
    image_file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None)
):
    """Analyze flat data from multiple input types (text, image, video)"""
    
    if not any([text_file, image_file, video_file]):
        raise HTTPException(status_code=400, detail="At least one file must be provided")
    
    temp_dir = None
    user_message = ""
    
    try:
        # Create temporary directory for files
        temp_dir = tempfile.mkdtemp()
        
        # Process text file
        if text_file:
            text_content = (await text_file.read()).decode("utf-8", errors="ignore")
            user_message += f"Text Description: {text_content}\n\n"
        
        # Process image file
        if image_file:
            # Validate image file
            if not image_file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid image file type")
            
            # Save image to temp directory
            image_path = os.path.join(temp_dir, f"uploaded_image.{image_file.filename.split('.')[-1]}")
            
            with open(image_path, "wb") as buffer:
                content = await image_file.read()
                buffer.write(content)
            
            # Validate image can be opened
            try:
                img = Image.open(image_path)
                img.verify()  # Verify it's a valid image
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
            
            user_message += f"Please analyze the image located at: {image_path}\n\n"
        
        # Process video file
        if video_file:
            # Validate video file type
            allowed_video_types = ['video/mp4', 'video/quicktime', 'video/x-msvideo']
            if video_file.content_type not in allowed_video_types:
                raise HTTPException(status_code=400, detail="Invalid video file type")
            
            # Save video to temp directory
            video_path = os.path.join(temp_dir, f"uploaded_video.{video_file.filename.split('.')[-1]}")
            
            with open(video_path, "wb") as buffer:
                content = await video_file.read()
                buffer.write(content)
            
            user_message += f"Please analyze the video located at: {video_path}\n\n"
        
        # Create full analysis message
        full_message = f"""
        {user_message}
        
        Please provide a comprehensive analysis of this flat/property including:
        1. Key features and highlights
        2. Market positioning
        3. Target audience
        4. Selling points
        5. Pricing recommendations (if applicable)
        
        Generate a compelling sales pitch based on the provided data.
        """
        
        # Run the team analysis
        response = flat_seller_team.run(full_message)
        
        # Handle different response types
        if hasattr(response, 'content'):
            analysis_result = response.content
        else:
            analysis_result = str(response)
            
        return AnalysisResponse(
            success=True,
            message="Multimodal analysis completed successfully",
            analysis=analysis_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "FlatSeller AI API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)