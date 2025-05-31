import os
import json
import re
import tempfile
import shutil
import uuid
from datetime import datetime
import logging
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from agents.mainAgent import MainAnalysisAgent
from agents.searchAgent import PropertySearchAgent
from models.vectorStore import QdrantVectorStoreClient

# Logging Setup
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f"app_{ts}.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
logger.info("Flat Broker System starting up")

# Initialize Agents & Vector Store
main_agent = MainAnalysisAgent()
vector_store = QdrantVectorStoreClient(
)
search_agent = PropertySearchAgent(vector_store)

# Streamlit Config & Styles
st.set_page_config(page_title="Flat Broker System", page_icon="🏠", layout="wide")
st.markdown(
    """
    <style>
      .stButton>button { width: 100%; }
      .property-card { padding: 1rem; border-radius: 0.5rem; border: 1px solid #ddd; margin-bottom: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state for storing analysis results
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'temp_files' not in st.session_state:
    st.session_state.temp_files = None
if 'property_id' not in st.session_state:
    st.session_state.property_id = None

# Helpers
def generate_unique_property_id():
    """Generate a unique property ID using UUID"""
    return str(uuid.uuid4())

def save_uploaded_files(uploaded_files, dest_dir):
    """Save uploaded files to destination directory"""
    paths = []
    os.makedirs(dest_dir, exist_ok=True)
    for f in uploaded_files:
        target = os.path.join(dest_dir, f.name)
        try:
            with open(target, "wb") as out:
                out.write(f.getbuffer())
            paths.append(target)
            logger.info(f"Saved {target}")
        except Exception as e:
            logger.error(f"Failed to save {f.name}: {e}")
            st.error(f"Failed to save {f.name}: {e}")
    return paths

def clean_and_parse(raw_text: str):
    """Clean and parse JSON response"""
    if isinstance(raw_text, dict):
        return raw_text
    
    cleaned = re.sub(r"```(?:json)?", "", str(raw_text)).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse as JSON: {e}, returning raw string.")
        return {"raw_output": cleaned, "description": cleaned}

def copy_files_safely(src_dir, dest_dir):
    """Safely copy files from source to destination"""
    try:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        if os.path.exists(src_dir):
            for item in os.listdir(src_dir):
                src_path = os.path.join(src_dir, item)
                dest_path = os.path.join(dest_dir, item)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dest_path)
                    logger.info(f"Copied {src_path} to {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Error copying files from {src_dir} to {dest_dir}: {e}")
        return False

def get_property_folder_info(property_id):
    """Get folder information for a specific property ID"""
    properties_dir = os.path.join(os.path.dirname(__file__), "properties")
    property_path = os.path.join(properties_dir, property_id)
    
    folder_info = {
        'property_id': property_id,
        'exists': False,
        'images': [],
        'videos': [],
        'text_files': [],
        'profile_data': None
    }
    
    if os.path.exists(property_path):
        folder_info['exists'] = True
        
        # Get images
        img_dir = os.path.join(property_path, "images")
        if os.path.exists(img_dir):
            folder_info['images'] = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Get videos
        vid_dir = os.path.join(property_path, "videos")
        if os.path.exists(vid_dir):
            folder_info['videos'] = [f for f in os.listdir(vid_dir) if f.lower().endswith(('.mp4', '.mov', '.avi'))]
        
        # Get text files
        text_dir = os.path.join(property_path, "text")
        if os.path.exists(text_dir):
            folder_info['text_files'] = [f for f in os.listdir(text_dir)]
            
            # Load profile data if exists
            profile_file = os.path.join(text_dir, "profile.json")
            if os.path.exists(profile_file):
                try:
                    with open(profile_file, "r", encoding='utf-8') as f:
                        folder_info['profile_data'] = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load profile data for {property_id}: {e}")
        
        logger.info(f"Retrieved folder info for property {property_id}")
    else:
        logger.warning(f"Property folder not found: {property_path}")
    
    return folder_info

# Main UI
st.title("🏠 Flat Broker System")
page = st.sidebar.radio("Navigation", ["Register Property", "Search Properties"])

if page == "Register Property":
    st.header("📝 Register New Property")
    description = st.text_area("Property Description", height=200)
    images = st.file_uploader("Upload Images", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    video = st.file_uploader("Upload Video", type=["mp4", "mov", "avi"], accept_multiple_files=False)

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Analyze Property"):
            if not description:
                st.error("Please provide a property description.")
            elif not images:
                st.error("Please upload at least one image.")
            elif not video:
                st.error("Please upload a video.")
            else:
                with st.spinner("Analyzing property..."):
                    try:
                        # Generate unique property ID at the start
                        property_id = generate_unique_property_id()
                        st.session_state.property_id = property_id
                        logger.info(f"Generated property ID: {property_id}")
                        
                        # Create temporary directory for processing
                        temp_dir = tempfile.mkdtemp()
                        logger.info(f"Created temp directory: {temp_dir}")
                        
                        # Create property structure
                        prop_dir = os.path.join(temp_dir, "property")
                        img_dir = os.path.join(prop_dir, "images")
                        vid_dir = os.path.join(prop_dir, "videos")
                        text_dir = os.path.join(prop_dir, "text")
                        
                        # Create directories
                        for directory in [img_dir, vid_dir, text_dir]:
                            os.makedirs(directory, exist_ok=True)
                        
                        # Save uploaded files
                        img_paths = save_uploaded_files(images, img_dir)
                        vid_paths = save_uploaded_files([video], vid_dir)
                        
                        # Save description
                        desc_file = os.path.join(text_dir, "description.txt")
                        with open(desc_file, "w", encoding='utf-8') as f:
                            f.write(description)
                        logger.info(f"Saved description to {desc_file}")
                        
                        # Analyze property
                        logger.info(f"Analyzing property in directory: {prop_dir}")
                        raw_profile = main_agent.analyze_property(prop_dir)
                        profile = clean_and_parse(raw_profile)
                        
                        # Add property ID to profile
                        profile['property_id'] = property_id
                        profile['created_at'] = datetime.now().isoformat()
                        
                        # Store results in session state
                        st.session_state.analysis_result = profile
                        st.session_state.temp_files = {
                            'prop_dir': prop_dir,
                            'img_dir': img_dir,
                            'vid_dir': vid_dir,
                            'text_dir': text_dir,
                            'temp_dir': temp_dir
                        }
                        
                        logger.info("Analysis completed successfully")
                        st.success(f"Property analysis completed! Property ID: {property_id}")
                        
                    except Exception as e:
                        logger.error(f"Error during analysis: {e}")
                        st.error(f"Error during analysis: {e}")

    # Display analysis results
    if st.session_state.analysis_result and st.session_state.property_id:
        st.subheader("📊 Analysis Result")
        st.write(f"**Property ID:** {st.session_state.property_id}")
        st.json(st.session_state.analysis_result)
        
        with col2:
            if st.button("✅ Register Property"):
                try:
                    with st.spinner("Registering property..."):
                        property_id = st.session_state.property_id
                        
                        # Create storage directory using property ID
                        storage = os.path.join(os.path.dirname(__file__), "properties")
                        os.makedirs(storage, exist_ok=True)
                        
                        # Use property ID as folder name
                        dest_dir = os.path.join(storage, property_id)
                        
                        # Create destination structure
                        dest_img_dir = os.path.join(dest_dir, "images")
                        dest_vid_dir = os.path.join(dest_dir, "videos")
                        dest_text_dir = os.path.join(dest_dir, "text")
                        
                        for directory in [dest_img_dir, dest_vid_dir, dest_text_dir]:
                            os.makedirs(directory, exist_ok=True)
                        
                        # Copy files from temp to permanent storage
                        temp_files = st.session_state.temp_files
                        success = True
                        
                        success &= copy_files_safely(temp_files['img_dir'], dest_img_dir)
                        success &= copy_files_safely(temp_files['vid_dir'], dest_vid_dir)
                        success &= copy_files_safely(temp_files['text_dir'], dest_text_dir)
                        
                        if not success:
                            st.error("Failed to copy some files")
                            logger.error("File copy operation failed")
                        else:
                            # Prepare document for vector store
                            profile_data = st.session_state.analysis_result
                            profile_data['property_id'] = property_id
                            profile_data['description'] = description
                            
                            # Add to vector store with property_id
                            document = {
                                "id": property_id,  # Use property_id as document ID
                                "property_id": property_id,
                                "text_description": json.dumps(profile_data, ensure_ascii=False),
                                "description": description,
                                "created_at": datetime.now().isoformat()
                            }
                            
                            vector_store.add_documents([document])
                            
                            # Force flush to ensure immediate searchability
                            try:
                                vector_store.qdrant_client.flush(collection_name="sample", wait=True)
                                logger.info(f"Flushed Qdrant after adding property {property_id}")
                            except Exception as e:
                                logger.warning(f"Flush operation failed: {e}")
                            
                            # Save JSON profile to file system
                            profile_file = os.path.join(dest_text_dir, "profile.json")
                            with open(profile_file, "w", encoding='utf-8') as f:
                                json.dump(profile_data, f, indent=2, ensure_ascii=False)
                            
                            logger.info(f"Property {property_id} registered successfully")
                            st.success(f"✅ Property registered successfully! ID: {property_id}")
                            
                            # Clean up temp files
                            try:
                                shutil.rmtree(temp_files['temp_dir'])
                                logger.info("Cleaned up temporary files")
                            except Exception as e:
                                logger.warning(f"Failed to cleanup temp files: {e}")
                            
                            # Reset session state
                            st.session_state.analysis_result = None
                            st.session_state.temp_files = None
                            st.session_state.property_id = None
                            
                            # Show property summary
                            st.subheader("📋 Property Summary")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**Property ID:** {property_id}")
                                st.write(f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            with col_b:
                                st.write(f"**Images:** {len(os.listdir(dest_img_dir)) if os.path.exists(dest_img_dir) else 0}")
                                st.write(f"**Videos:** {len(os.listdir(dest_vid_dir)) if os.path.exists(dest_vid_dir) else 0}")
                
                except Exception as e:
                    logger.error(f"Error during registration: {e}")
                    st.error(f"Registration failed: {e}")

elif page == "Search Properties":
    st.header("🔍 Search Properties")
    query = st.text_input("Search Query", placeholder="e.g., Flats contains of no ac, not having elevator and Newly renovated")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_button = st.button("🔍 Search Properties")
    with col2:
        max_results = st.selectbox("Max Results", [5, 10, 15, 20], index=0)
    
    if search_button:
        if not query.strip():
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Searching properties..."):
                try:
                    logger.info(f"Searching for query: {query}")
                    
                    # Use search agent to get results with property IDs
                    results = search_agent.search(query.strip(), k=max_results)
                    logger.info(f"Search returned {len(results)} results")
                    
                    if results:
                        st.subheader(f"🏠 Found {len(results)} matching properties")
                        
                        for i, result in enumerate(results, 1):
                            property_id = result.get('property_id')
                            score = result.get('score', 0)
                            matched_features = result.get('matched_features', [])
                            missing_features = result.get('missing_features', [])
                            feature_match_percentage = result.get('feature_match_percentage', 0)
                            
                            with st.expander(f"Property {i}: {property_id} (Score: {score:.3f}, Match: {feature_match_percentage}%)"):
                                
                                # Get folder information for this property ID
                                folder_info = get_property_folder_info(property_id)
                                
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.write(f"**Property ID:** {property_id}")
                                    st.write(f"**Match Score:** {score:.3f}")
                                    st.write(f"**Feature Match:** {feature_match_percentage}%")
                                
                                with col_b:
                                    st.write(f"**Images:** {len(folder_info['images'])}")
                                    st.write(f"**Videos:** {len(folder_info['videos'])}")
                                    st.write(f"**Folder Exists:** {'✅' if folder_info['exists'] else '❌'}")
                                
                                # Show matched and missing features
                                if matched_features:
                                    st.subheader("✅ Matched Features")
                                    st.success(", ".join(matched_features))
                                
                                if missing_features:
                                    st.subheader("❌ Missing Features")
                                    st.warning(", ".join(missing_features))
                                
                                # Show folder contents
                                if folder_info['exists']:
                                    st.subheader("📁 Folder Contents")
                                    
                                    col_c, col_d, col_e = st.columns(3)
                                    with col_c:
                                        if folder_info['images']:
                                            st.write("**Images:**")
                                            for img in folder_info['images']:
                                                st.write(f"• {img}")
                                    
                                    with col_d:
                                        if folder_info['videos']:
                                            st.write("**Videos:**")
                                            for vid in folder_info['videos']:
                                                st.write(f"• {vid}")
                                    
                                    with col_e:
                                        if folder_info['text_files']:
                                            st.write("**Text Files:**")
                                            for txt in folder_info['text_files']:
                                                st.write(f"• {txt}")
                                
                                # Show property profile data if available
                                if folder_info['profile_data']:
                                    st.subheader("📊 Property Analysis")
                                    
                                    # Show original description if available
                                    if 'description' in folder_info['profile_data']:
                                        st.write("**Original Description:**")
                                        st.text_area("", value=folder_info['profile_data']['description'], height=100, disabled=True, key=f"desc_{i}_{property_id}")
                                    
                                    # Show analysis data
                                    with st.expander("View Full Analysis Data"):
                                        st.json(folder_info['profile_data'])
                                else:
                                    st.warning("No detailed property analysis data found in folder.")
                    else:
                        st.info("No matching properties found. Try adjusting your search terms.")
                        
                except Exception as e:
                    logger.error(f"Search error: {e}")
                    st.error(f"Search failed: {e}")
                    # Show the error details for debugging
                    with st.expander("Error Details"):
                        st.code(str(e))

# Cleanup section in sidebar
with st.sidebar:
    st.markdown("---")
    st.subheader("🗂️ System Info")
    
    # Show properties count
    properties_dir = os.path.join(os.path.dirname(__file__), "properties")
    if os.path.exists(properties_dir):
        prop_count = len([d for d in os.listdir(properties_dir) if os.path.isdir(os.path.join(properties_dir, d))])
        st.write(f"**Registered Properties:** {prop_count}")
    else:
        st.write("**Registered Properties:** 0")
    
    # Show logs info
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        st.write(f"**Log Files:** {len(log_files)}")
    
    st.markdown("---")
    st.subheader("💡 Search Tips")
    st.write("Use natural language like:")
    st.write("• 'Flats contains of no ac, not having elevator'")
    st.write("• 'Newly renovated apartment with balcony'")
    st.write("• 'House with parking and WiFi'")
    st.write("• 'No AC and no elevator properties'")
