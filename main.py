import streamlit as st
import tempfile
import os
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import logging
import json

# Import agents and models
from agents.mainAgent import MainAnalysisAgent
from agents.searchAgent import PropertySearchAgent
from models.vectorStore import PropertyVectorStore

# Set up logging
def setup_logging():
    """Set up logging configuration"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'app_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logging
logger = setup_logging()
logger.info("Application started")

# Initialize agents
main_agent = MainAnalysisAgent()
search_agent = PropertySearchAgent()

# Set page config
st.set_page_config(
    page_title="Flat Broker System",
    page_icon="🏠",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .property-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

def save_uploaded_files(uploaded_files, temp_dir):
    """Save uploaded files to temporary directory"""
    saved_paths = []
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            saved_paths.append(file_path)
            logger.info(f"Saved uploaded file: {file_path}")
    return saved_paths

def display_property_images(image_paths):
    """Display property images in a grid"""
    if image_paths:
        cols = st.columns(min(3, len(image_paths)))
        for idx, img_path in enumerate(image_paths):
            with cols[idx % 3]:
                try:
                    st.image(img_path, use_column_width=True)
                except Exception as e:
                    st.error(f"Error loading image: {e}")

def display_property_video(video_path):
    """Display property video"""
    if video_path and os.path.exists(video_path):
        st.video(video_path)
    else:
        st.warning("Video file not found")

def register_property(text_description, image_paths, video_path, properties_dir):
    """Register a new property with all its data"""
    try:
        # Create property directory
        property_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        property_dir = os.path.join(properties_dir, property_id)
        os.makedirs(property_dir, exist_ok=True)
        
        # Create subdirectories
        images_dir = os.path.join(property_dir, "images")
        videos_dir = os.path.join(property_dir, "videos")
        text_dir = os.path.join(property_dir, "text")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)
        os.makedirs(text_dir, exist_ok=True)
        
        # Save text description
        text_path = os.path.join(text_dir, "description.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_description)
        
        # Save images
        for img_path in image_paths:
            dest_path = os.path.join(images_dir, os.path.basename(img_path))
            os.rename(img_path, dest_path)
        
        # Save video
        if video_path:
            dest_path = os.path.join(videos_dir, os.path.basename(video_path))
            os.rename(video_path, dest_path)
        
        logger.info(f"Property registered successfully: {property_id}")
        return property_id
        
    except Exception as e:
        logger.error(f"Error registering property: {str(e)}", exc_info=True)
        raise

def main():
    st.title("🏠 Flat Broker System")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Choose a page", ["Register Property", "Search Properties"])
    
    if page == "Register Property":
        st.header("📝 Register New Property")
        
        # Create a form for property registration
        with st.form("property_registration", clear_on_submit=True):
            # Text description
            text_description = st.text_area(
                "Property Description",
                help="Enter detailed description of the property including type (1BHK, 2BHK, etc.), rent amount, and location",
                height=200
            )
            
            # Image upload
            st.subheader("Property Images")
            uploaded_images = st.file_uploader(
                "Upload Property Images",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                help="Upload multiple images of the property"
            )
            
            # Video upload
            st.subheader("Property Video")
            uploaded_video = st.file_uploader(
                "Upload Property Video",
                type=['mp4', 'mov'],
                help="Upload a video tour of the property"
            )
            
            # Submit button
            submitted = st.form_submit_button("Register Property")
            
            if submitted:
                # Validate all required content is provided
                if not text_description:
                    st.error("Please provide a property description")
                    return
                if not uploaded_images:
                    st.error("Please upload at least one property image")
                    return
                if not uploaded_video:
                    st.error("Please upload a property video")
                    return
                
                try:
                    with st.spinner("Processing property registration..."):
                        # Create temporary directory for files
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # Save uploaded files
                            image_paths = save_uploaded_files(uploaded_images, temp_dir)
                            video_path = save_uploaded_files([uploaded_video], temp_dir)[0] if uploaded_video else None
                            
                            # Register property
                            properties_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "properties")
                            os.makedirs(properties_dir, exist_ok=True)
                            
                            property_id = register_property(
                                text_description=text_description,
                                image_paths=image_paths,
                                video_path=video_path,
                                properties_dir=properties_dir
                            )
                            
                            st.success(f"Property registered successfully! Property ID: {property_id}")
                            logger.info(f"Property registration completed: {property_id}")
                            
                except Exception as e:
                    st.error(f"Error registering property: {str(e)}")
                    logger.error(f"Error in property registration: {str(e)}", exc_info=True)
    
    else:  # Search Properties page
        st.header("🔍 Search Properties")
        
        # Search form
        with st.form("property_search"):
            # Search Query
            search_query = st.text_input(
                "Search Query",
                help="Enter your search query (e.g., '2BHK flats with rent 20k in Koramangala' or '3BHK apartments near MG Road')"
            )
            
            search_button = st.form_submit_button("Search Properties")
            
            if search_button:
                if not search_query:
                    st.warning("Please enter a search query")
                else:
                    try:
                        with st.spinner("Searching properties..."):
                            logger.info(f"Starting property search with query: {search_query}")
                            
                            # Use search agent to find properties
                            properties_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "properties")
                            results = search_agent.search_properties(
                                query=search_query,
                                properties_dir=properties_dir
                            )
                            
                            # Display results
                            if results:
                                st.subheader(f"Found {len(results)} properties")
                                
                                for idx, property_data in enumerate(results, 1):
                                    with st.expander(f"Property {property_data['property_id']} (Score: {property_data['relevance_score']:.2f})"):
                                        analysis = property_data['analysis']
                                        
                                        # Display property analysis
                                        st.markdown(analysis)
                                        
                                        # Display property media
                                        st.subheader("Property Media")
                                        
                                        # Get property path
                                        property_path = os.path.join(properties_dir, property_data['property_id'])
                                        
                                        # Display images
                                        image_dir = os.path.join(property_path, "images")
                                        if os.path.exists(image_dir):
                                            image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir) 
                                                         if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                                            if image_paths:
                                                st.subheader("Images")
                                                display_property_images(image_paths)
                                        
                                        # Display video
                                        video_dir = os.path.join(property_path, "videos")
                                        if os.path.exists(video_dir):
                                            video_files = [f for f in os.listdir(video_dir) 
                                                         if f.lower().endswith(('.mp4', '.mov', '.avi'))]
                                            if video_files:
                                                st.subheader("Video")
                                                video_path = os.path.join(video_dir, video_files[0])
                                                display_property_video(video_path)
                            else:
                                st.info("No properties found matching your criteria")
                                logger.info("No properties found matching the search criteria")
                                
                    except Exception as e:
                        st.error(f"Error searching properties: {str(e)}")
                        logger.error(f"Error in property search: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()