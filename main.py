import streamlit as st
import requests
from PIL import Image
import json
import io

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change this to your FastAPI server URL

st.set_page_config(page_title="FlatSeller AI", layout="wide")

st.title("🏡 FlatSeller AI Agent Team")
st.markdown("Upload flat data (text, image, or video) and get a perfect pitch summary to sell!")

# Initialize session state
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = {}

def check_api_health():
    """Check if the FastAPI backend is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def call_text_analysis_api(text_content):
    """Call the text analysis API endpoint"""
    try:
        payload = {"text_content": text_content}
        response = requests.post(
            f"{API_BASE_URL}/analyze-text",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None

def call_multimodal_analysis_api(text_file=None, image_file=None, video_file=None):
    """Call the multimodal analysis API endpoint"""
    try:
        files = {}
        
        if text_file:
            files['text_file'] = (text_file.name, text_file.getvalue(), 'text/plain')
        
        if image_file:
            files['image_file'] = (image_file.name, image_file.getvalue(), image_file.type)
        
        if video_file:
            files['video_file'] = (video_file.name, video_file.getvalue(), video_file.type)
        
        response = requests.post(
            f"{API_BASE_URL}/analyze-multimodal",
            files=files,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None

# Check API health
api_healthy = check_api_health()

if not api_healthy:
    st.error("🚨 **FastAPI Backend Not Available**")
    st.error("Please make sure the FastAPI server is running on http://localhost:8000")
    st.info("Run the FastAPI server with: `uvicorn main:app --reload`")
    st.stop()

st.success("✅ Connected to FastAPI backend")

# Sidebar for file uploads
with st.sidebar:
    st.header("🔍 Upload Flat Data")
    uploaded_text = st.file_uploader("📄 Upload Text Description", type=["txt"])
    uploaded_image = st.file_uploader("🖼️ Upload Room Images", type=["jpg", "jpeg", "png"])
    uploaded_video = st.file_uploader("🎥 Upload Flat Walkthrough Video", type=["mp4", "mov", "avi"])

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    # Display uploaded files
    files_uploaded = False
    
    if uploaded_text:
        st.subheader("📄 Text Description")
        text_content = uploaded_text.read().decode("utf-8", errors="ignore")
        st.text_area("Content Preview:", text_content[:500] + "..." if len(text_content) > 500 else text_content, height=150)
        files_uploaded = True

    if uploaded_image:
        st.subheader("🖼️ Room Image")
        img = Image.open(uploaded_image)
        st.image(img, caption="Uploaded Room Image", use_container_width=True)
        files_uploaded = True

    if uploaded_video:
        st.subheader("🎥 Flat Walkthrough Video")
        st.video(uploaded_video)
        files_uploaded = True

with col2:
    st.subheader("🚀 Analysis Options")
    
    # Analysis type selection
    analysis_type = st.radio(
        "Choose Analysis Method:",
        ["Text Only", "Multimodal (All Files)"],
        help="Text Only uses just the text description. Multimodal analyzes all uploaded files together."
    )
    
    # Generate button
    if files_uploaded:
        if st.button("🚀 Generate Flat Pitch", type="primary", use_container_width=True):
            with st.spinner("🧠 AI Team is analyzing the flat..."):
                
                if analysis_type == "Text Only" and uploaded_text:
                    # Text-only analysis
                    uploaded_text.seek(0)  # Reset file pointer
                    text_content = uploaded_text.read().decode("utf-8", errors="ignore")
                    result = call_text_analysis_api(text_content)
                    
                elif analysis_type == "Multimodal":
                    # Reset file pointers
                    if uploaded_text:
                        uploaded_text.seek(0)
                    if uploaded_image:
                        uploaded_image.seek(0)
                    if uploaded_video:
                        uploaded_video.seek(0)
                    
                    result = call_multimodal_analysis_api(
                        text_file=uploaded_text,
                        image_file=uploaded_image,
                        video_file=uploaded_video
                    )
                else:
                    st.error("Please upload a text file for text-only analysis.")
                    result = None
                
                # Display results
                if result and result.get('success'):
                    st.success("✅ Analysis completed successfully!")
                    
                    # Display the analysis in the main area
                    st.markdown("### 📝 Flat Analysis & Pitch Summary")
                    st.markdown("---")
                    st.markdown(result.get('analysis', 'No analysis available'))
                    
                    # Download option
                    st.download_button(
                        label="📥 Download Analysis",
                        data=result.get('analysis', ''),
                        file_name="flat_analysis.md",
                        mime="text/markdown"
                    )
                    
                elif result:
                    st.error(f"❌ Analysis failed: {result.get('message', 'Unknown error')}")
                else:
                    st.error("❌ Failed to get response from the analysis service.")
    else:
        st.info("👆 Please upload at least one type of data to get started.")

# Information panels
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("""
    **📄 Text Analysis**
    
    Upload a text file with property details, descriptions, or specifications for AI-powered analysis.
    """)

with col2:
    st.info("""
    **🖼️ Image Analysis**
    
    Upload room images for visual analysis of space, lighting, and features.
    """)

with col3:
    st.info("""
    **🎥 Video Analysis**
    
    Upload walkthrough videos for comprehensive property assessment.
    """)

# API Status in sidebar
with st.sidebar:
    st.markdown("---")
    st.subheader("🔧 System Status")
    if api_healthy:
        st.success("✅ FastAPI Backend: Online")
    else:
        st.error("❌ FastAPI Backend: Offline")
    
    with st.expander("🔍 API Information"):
        st.code(f"API URL: {API_BASE_URL}")
        st.write("Available endpoints:")
        st.write("- `/health` - Health check")
        st.write("- `/analyze-text` - Text analysis")
        st.write("- `/analyze-multimodal` - Multimodal analysis")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
💡 <strong>Tip</strong>: For best results, provide detailed text descriptions along with clear images or videos.
<br>
🔧 Powered by FastAPI backend for scalable processing
</div>
""", unsafe_allow_html=True)