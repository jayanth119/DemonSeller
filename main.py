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
import base64

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from agents.mainAgent import MainAnalysisAgent
from agents.searchAgent import PropertySearchAgent
from models.vectorStore import QdrantVectorStoreClient


ts = datetime.now().strftime("%Y%m%d_%H%M%S")
# Initialize Agents & Vector Store
main_agent = MainAnalysisAgent()
vector_store = QdrantVectorStoreClient(
                url="https://886d811f-9d2e-41a5-8043-7354789c11a3.europe-west3-0.gcp.cloud.qdrant.io:6333",
                api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.w1474GJFXKREKXNFYEAQ_bMQ1HT3tKynM969KGHysi4",
                collection="sample",
                google_api_key="AIzaSyCmnhXgfxSw8iDPFsR9rm14Q8KFxntvUvk"
        )
search_agent = PropertySearchAgent(vector_store)

# Streamlit Config & Styles
st.set_page_config(page_title="Flat Broker System", page_icon="🏠", layout="wide")
st.markdown(
    """
    <style>
      .stButton>button { width: 100%; }
      .property-card { 
        padding: 1rem; 
        border-radius: 0.5rem; 
        border: 1px solid #ddd; 
        margin-bottom: 1rem; 
        background-color: #f9f9f9;
      }
      .media-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 10px 0;
      }
      .media-item {
        max-width: 200px;
        max-height: 150px;
      }
      .input-requirement {
        background-color: #e8f4f8;
        border-left: 4px solid #1f77b4;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
      }
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
    if not uploaded_files:
        return paths
        
    os.makedirs(dest_dir, exist_ok=True)
    for f in uploaded_files:
        target = os.path.join(dest_dir, f.name)
        try:
            with open(target, "wb") as out:
                out.write(f.getbuffer())
            paths.append(target)
            # logger.info(f"Saved {target}")
        except Exception as e:
            # logger.error(f"Failed to save {f.name}: {e}")
            st.error(f"Failed to save {f.name}: {e}")
    return paths

def validate_registration_inputs(description, images):
    """Validate that at least one input type is provided"""
    has_description = bool(description and description.strip())
    has_images = bool(images and len(images) > 0)
    # has_videos = bool(videos and len(videos) > 0)
    
    return {
        'has_description': has_description,
        'has_images': has_images,
        # 'has_videos': has_videos,
        'is_valid': has_description or has_images ,
        'provided_count': sum([has_description, has_images])
    }

def clean_and_parse(raw_text: str):
    """Clean and parse JSON response"""
    if isinstance(raw_text, dict):
        return raw_text
    
    cleaned = re.sub(r"```(?:json)?", "", str(raw_text)).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # logger.warning(f"Failed to parse as JSON: {e}, returning raw string.")
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
                    # logger.info(f"Copied {src_path} to {dest_path}")
        return True
    except Exception as e:
        # logger.error(f"Error copying files from {src_dir} to {dest_dir}: {e}")
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
        'profile_data': None,
        'image_paths': [],
        'video_paths': []
    }
    
    if os.path.exists(property_path):
        folder_info['exists'] = True
        
        # Get images with full paths
        img_dir = os.path.join(property_path, "images")
        if os.path.exists(img_dir):
            image_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            folder_info['images'] = image_files
            folder_info['image_paths'] = [os.path.join(img_dir, f) for f in image_files]
        
        # Get videos with full paths
        vid_dir = os.path.join(property_path, "videos")
        if os.path.exists(vid_dir):
            video_files = [f for f in os.listdir(vid_dir) if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))]
            folder_info['videos'] = video_files
            folder_info['video_paths'] = [os.path.join(vid_dir, f) for f in video_files]
        
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
                    pass 
                    
        
        
    else:
        # logger.warning(f"Property folder not found: {property_path}")
        print("reon")
    
    return folder_info

def display_images(image_paths, property_id):
    """Display images in a grid layout"""
    if not image_paths:
        st.write("No images available")
        return
    
    # Display images in columns
    cols_per_row = 3
    rows = [image_paths[i:i + cols_per_row] for i in range(0, len(image_paths), cols_per_row)]
    
    for row in rows:
        cols = st.columns(len(row))
        for idx, (col, img_path) in enumerate(zip(cols, row)):
            with col:
                try:
                    if os.path.exists(img_path):
                        st.image(img_path, caption=os.path.basename(img_path), use_container_width=True)
                    else:
                        st.error(f"Image not found: {os.path.basename(img_path)}")
                except Exception as e:
                    st.error(f"Error loading image {os.path.basename(img_path)}: {str(e)}")

def display_videos(video_paths, property_id):
    """Display videos"""
    if not video_paths:
        st.write("No videos available")
        return
    
    for video_path in video_paths:
        try:
            if os.path.exists(video_path):
                st.video(video_path)
                st.caption(f"Video: {os.path.basename(video_path)}")
            else:
                st.error(f"Video not found: {os.path.basename(video_path)}")
        except Exception as e:
            st.error(f"Error loading video {os.path.basename(video_path)}: {str(e)}")

def safe_search_properties(query, max_results=5):
    """Safely search properties with error handling"""
    try:
        
        
        # Perform the search
        results = search_agent.search(query.strip(), k=max_results)
        
        if not results:
            # logger.info("No results returned from search agent")
            return []
        
        # logger.info(f"Search agent returned {len(results)} results")
        
        # Process and validate results
        processed_results = []
        for idx, result in enumerate(results):
            try:
                # Ensure result has required fields
                property_id = result.get('property_id', f'unknown_{idx}')
                score = float(result.get('score', 0.0))
                
                # Get additional result data
                matched_features = result.get('matched_features', [])
                missing_features = result.get('missing_features', [])
                feature_match_percentage = result.get('feature_match_percentage', 0)
                
                # Validate property_id exists in filesystem
                folder_info = get_property_folder_info(property_id)
                
                processed_result = {
                    'property_id': property_id,
                    'score': score,
                    'matched_features': matched_features if isinstance(matched_features, list) else [],
                    'missing_features': missing_features if isinstance(missing_features, list) else [],
                    'feature_match_percentage': feature_match_percentage,
                    'folder_exists': folder_info['exists'],
                    'folder_info': folder_info
                }
                
                processed_results.append(processed_result)
                # logger.info(f"Processed result {idx + 1}: {property_id} (score: {score:.3f})")
                
            except Exception as e:
                # logger.error(f"Error processing result {idx}: {e}")
                continue
        
        return processed_results
        
    except Exception as e:
        # logger.error(f"Error in safe_search_properties: {e}")
        st.error(f"Search error: {str(e)}")
        return []

# Main UI
st.title("🏠 Flat Broker System")
page = st.sidebar.radio("Navigation", ["Register Property", "Search Properties"])

if page == "Register Property":
    st.header("📝 Register New Property")
    
    # Input requirements information
    # st.markdown("""
    # <div class="input-requirement">
    #     <strong>📋 Registration Requirements:</strong><br>
    #     You can register a property by providing <strong>at least one</strong> of the following:
    #     <ul>
    #         <li>📝 Property description text</li>
    #         <li>📸 Property images</li>
    #         <li>🎥 Property video</li>
    #     </ul>
    #     <em>Providing more information will result in better analysis and search results!</em>
    # </div>
    # """, unsafe_allow_html=True)
    
    # Input fields
    description = st.text_area(
        "Property Description (Optional)", 
        height=200, 
        placeholder="Enter detailed property description... (e.g., 2 BHK apartment with balcony, no AC, newly renovated)"
    )
    
    images = st.file_uploader(
        "Upload Images (Optional)", 
        type=["jpg", "png", "jpeg", "gif", "bmp"], 
        accept_multiple_files=True,
        help="Upload property images to help with visual analysis"
    )
    
    # videos = st.file_uploader(
    #     "Upload Videos (Optional)", 
    #     type=["mp4", "mov", "avi", "mkv", "webm"], 
    #     accept_multiple_files=True,
    #     help="Upload property videos for comprehensive analysis"
    # )
    
    # Validation and preview
    validation = validate_registration_inputs(description, images)
    
    # Show current input status
    col_status1, col_status2, col_status3 = st.columns(3)
    with col_status1:
        if validation['has_description']:
            st.success("✅ Description provided")
        else:
            st.info("📝 No description")
    
    with col_status2:
        if validation['has_images']:
            st.success(f"✅ {len(images)} image(s) uploaded")
        else:
            st.info("📸 No images")
    
    # with col_status3:
    #     if validation['has_videos']:
    #         st.success(f"✅ {len(videos)} video(s) uploaded")
    #     else:
    #         st.info("🎥 No videos")
    
    # Show what's provided
    if validation['provided_count'] > 0:
        st.info(f"📊 Inputs provided: {validation['provided_count']}/3 types")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Analyze Property", disabled=not validation['is_valid']):
            if not validation['is_valid']:
                st.error("❌ Please provide at least one input: description, images, or videos.")
            else:
                with st.spinner("Analyzing property..."):
                    try:
                        # Generate unique property ID at the start
                        property_id = generate_unique_property_id()
                        st.session_state.property_id = property_id
                        # logger.info(f"Generated property ID: {property_id}")
                        
                        # Create temporary directory for processing
                        temp_dir = tempfile.mkdtemp()
                        # logger.info(f"Created temp directory: {temp_dir}")
                        
                        # Create property structure
                        prop_dir = os.path.join(temp_dir, "property")
                        img_dir = os.path.join(prop_dir, "images")
                        # vid_dir = os.path.join(prop_dir, "videos")
                        text_dir = os.path.join(prop_dir, "text")
                        
                        # Create directories
                        for directory in [img_dir, text_dir]:
                            os.makedirs(directory, exist_ok=True)
                        
                        # Save uploaded files based on what was provided
                        img_paths = []
                        vid_paths = []
                        
                        if validation['has_images']:
                            img_paths = save_uploaded_files(images, img_dir)
                            # logger.info(f"Saved {len(img_paths)} images")
                        
                        # if validation['has_videos']:
                        #     vid_paths = save_uploaded_files(videos, vid_dir)
                        #     logger.info(f"Saved {len(vid_paths)} videos")
                        
                        # Save description if provided
                        if validation['has_description']:
                            desc_file = os.path.join(text_dir, "description.txt")
                            with open(desc_file, "w", encoding='utf-8') as f:
                                f.write(description.strip())
                            # logger.info(f"Saved description to {desc_file}")
                        
                        # Create a summary of what was provided for analysis
                        input_summary = {
                            'has_description': validation['has_description'],
                            'has_images': validation['has_images'],
                            # 'has_videos': validation['has_videos'],
                            'image_count': len(images) if images else 0,
                            # 'video_count': len(videos) if videos else 0,
                            'description_length': len(description.strip()) if description else 0
                        }
                        
                        # Save input summary for reference
                        summary_file = os.path.join(text_dir, "input_summary.json")
                        with open(summary_file, "w", encoding='utf-8') as f:
                            json.dump(input_summary, f, indent=2)
                        
                        # Analyze property
                        # logger.info(f"Analyzing property in directory: {prop_dir}")
                        # logger.info(f"Input summary: {input_summary}")
                        
                        raw_profile = main_agent.analyze_property(prop_dir)
                        profile = clean_and_parse(raw_profile)
                        
                        # Add property ID and metadata to profile
                        profile['property_id'] = property_id
                        profile['created_at'] = datetime.now().isoformat()
                        profile['input_summary'] = input_summary
                        
                        # Store results in session state
                        st.session_state.analysis_result = profile
                        st.session_state.temp_files = {
                            'prop_dir': prop_dir,
                            'img_dir': img_dir,
                            # 'vid_dir': vid_dir,
                            'text_dir': text_dir,
                            'temp_dir': temp_dir
                        }
                        
                        # logger.info("Analysis completed successfully")
                        st.success(f"✅ Property analysis completed! Property ID: {property_id}")
                        
                        # Show what was analyzed
                        st.info(f"📊 Analyzed using: " + 
                               ", ".join([
                                   "Description" if validation['has_description'] else "",
                                   f"{len(images)} Images" if validation['has_images'] else "",
                                #    f"{len(videos)} Videos" if validation['has_videos'] else ""
                               ]).strip(", "))
                        
                    except Exception as e:
                        # logger.error(f"Error during analysis: {e}")
                        st.error(f"❌ Error during analysis: {e}")

    # Display analysis results
    if st.session_state.analysis_result and st.session_state.property_id:
        st.subheader("📊 Analysis Result")
        st.write(f"**Property ID:** {st.session_state.property_id}")
        
        # Show input summary in the results
        if 'input_summary' in st.session_state.analysis_result:
            input_sum = st.session_state.analysis_result['input_summary']
            st.write("**Analysis Based On:**")
            analysis_info = []
            if input_sum['has_description']:
                analysis_info.append(f"📝 Description ({input_sum['description_length']} chars)")
            if input_sum['has_images']:
                analysis_info.append(f"📸 {input_sum['image_count']} Images")
            # if input_sum['has_videos']:
            #     analysis_info.append(f"🎥 {input_sum['video_count']} Videos")
            st.write(" • ".join(analysis_info))
        
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
                        # success &= copy_files_safely(temp_files['vid_dir'], dest_vid_dir)
                        success &= copy_files_safely(temp_files['text_dir'], dest_text_dir)
                        
                        if not success:
                            st.error("❌ Failed to copy some files")
                            # logger.error("File copy operation failed")
                        else:
                            # Prepare document for vector store
                            profile_data = st.session_state.analysis_result
                            profile_data['property_id'] = property_id
                            
                            # Use description if provided, otherwise use analysis result
                            description_text = description.strip() if description and description.strip() else json.dumps(profile_data, ensure_ascii=False)
                            profile_data['description'] = description_text
                            
                            # Add to vector store with property_id
                            document = {
                                "id": property_id,  # Use property_id as document ID
                                "property_id": property_id,
                                "text_description": json.dumps(profile_data, ensure_ascii=False),
                                "description": description_text,
                                "created_at": datetime.now().isoformat()
                            }
                            
                            vector_store.add_documents([document])
                            
                            # Force flush to ensure immediate searchability
                            try:
                                vector_store.qdrant_client.flush(collection_name="sample", wait=True)
                                # logger.info(f"Flushed Qdrant after adding property {property_id}")
                            except Exception as e:
                                pass 
                                # logger.warning(f"Flush operation failed: {e}")
                            
                            # Save JSON profile to file system
                            profile_file = os.path.join(dest_text_dir, "profile.json")
                            with open(profile_file, "w", encoding='utf-8') as f:
                                json.dump(profile_data, f, indent=2, ensure_ascii=False)
                            
                            # logger.info(f"Property {property_id} registered successfully")
                            st.success(f"✅ Property registered successfully! ID: {property_id}")
                            
                            # Clean up temp files
                            try:
                                shutil.rmtree(temp_files['temp_dir'])
                                # logger.info("Cleaned up temporary files")
                            except Exception as e:
                                pass 
                                # logger.warning(f"Failed to cleanup temp files: {e}")
                            
                            # Show property summary
                            st.subheader("📋 Property Summary")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**Property ID:** {property_id}")
                                st.write(f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            with col_b:
                                img_count = len(os.listdir(dest_img_dir)) if os.path.exists(dest_img_dir) else 0
                                vid_count = len(os.listdir(dest_vid_dir)) if os.path.exists(dest_vid_dir) else 0
                                st.write(f"**Images:** {img_count}")
                                st.write(f"**Videos:** {vid_count}")
                            
                            # Reset session state
                            st.session_state.analysis_result = None
                            st.session_state.temp_files = None
                            st.session_state.property_id = None
                
                except Exception as e:
                    # logger.error(f"Error during registration: {e}")
                    st.error(f"❌ Registration failed: {e}")

    # Show validation message at the bottom if no valid inputs
    if not validation['is_valid']:
        st.warning("⚠️ Please provide at least one input type to proceed with property registration.")

elif page == "Search Properties":
    st.header("🔍 Search Properties")
    
    # Search input section
    query = st.text_input("Search Query", 
                         placeholder="e.g., Flats contains of no ac, not having elevator and Newly renovated",
                         help="Use natural language to describe what you're looking for")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_button = st.button("🔍 Search Properties", type="primary")
    with col2:
        max_results = st.selectbox("Max Results", [1,2 ,3,5, 10, 15, 20], index=0)
    
    # Advanced search options
    with st.expander("🔧 Advanced Search Options"):
        include_images = st.checkbox("Display Images", value=True)
        include_videos = st.checkbox("Display Videos", value=True)
        show_full_analysis = st.checkbox("Show Full Analysis Data", value=False)
        show_file_details = st.checkbox("Show Detailed File Information", value=False)
    
    if search_button:
        if not query.strip():
            st.warning("⚠️ Please enter a search query.")
        else:
            with st.spinner("🔍 Searching properties..."):
                try:
                    # logger.info(f"Starting search for query: '{query}' with max_results: {max_results}")
                    
                    # Perform safe search
                    results = safe_search_properties(query, max_results)
                    
                    if results:
                        st.success(f"🏠 Found {len(results)} matching properties")
                        
                        # Display results
                        for i, result in enumerate(results, 1):
                            property_id = result['property_id']
                            score = result['score']
                            matched_features = result['matched_features']
                            missing_features = result['missing_features']
                            feature_match_percentage = result['feature_match_percentage']
                            folder_info = result['folder_info']
                            
                            # Create expandable section for each property
                            with st.expander(f"🏠 Property {i}: {property_id[:8]}... (Score: {score:.3f}, Match: {feature_match_percentage}%)", expanded=True):
                                
                                # Property info header
                                col_a, col_b, col_c = st.columns(3)
                                with col_a:
                                    st.metric("Property ID", property_id[:8] + "...")
                                    st.write(f"**Full ID:** `{property_id}`")
                                with col_b:
                                    st.metric("Match Score", f"{score:.3f}")
                                    st.metric("Feature Match", f"{feature_match_percentage}%")
                                with col_c:
                                    st.metric("Images", len(folder_info['images']))
                                    st.metric("Videos", len(folder_info['videos']))
                                
                                # Status indicators
                                status_col1, status_col2 = st.columns(2)
                                with status_col1:
                                    if folder_info['exists']:
                                        st.success("✅ Property folder exists")
                                    else:
                                        st.error("❌ Property folder not found")
                                
                                with status_col2:
                                    if folder_info['profile_data']:
                                        st.success("✅ Analysis data available")
                                        
                                        # Show input types used for this property
                                        if 'input_summary' in folder_info['profile_data']:
                                            input_sum = folder_info['profile_data']['input_summary']
                                            input_types = []
                                            if input_sum.get('has_description'):
                                                input_types.append("📝 Text")
                                            if input_sum.get('has_images'):
                                                input_types.append(f"📸 {input_sum.get('image_count', 0)} Images")
                                            if input_sum.get('has_videos'):
                                                input_types.append(f"🎥 {input_sum.get('video_count', 0)} Videos")
                                            
                                            if input_types:
                                                st.info(f"**Registered with:** {', '.join(input_types)}")
                                    else:
                                        st.warning("⚠️ No analysis data found")
                                
                                # Feature matching section
                                if matched_features or missing_features:
                                    st.subheader("🎯 Feature Analysis")
                                    
                                    if matched_features:
                                        st.success("✅ **Matched Features:**")
                                        for feature in matched_features:
                                            st.write(f"• {feature}")
                                    
                                    if missing_features:
                                        st.warning("❌ **Missing Features:**")
                                        for feature in missing_features:
                                            st.write(f"• {feature}")
                                
                                # Media display section
                                if folder_info['exists']:
                                    st.subheader("📁 Property Media")
                                    
                                    # Display Images
                                    if include_images and folder_info['image_paths']:
                                        st.write("**📸 Images:**")
                                        display_images(folder_info['image_paths'], property_id)
                                    elif include_images:
                                        st.info("No images available for this property")
                                    
                                    # Display Videos
                                    # if include_videos and folder_info['video_paths']:
                                    #     st.write("**🎥 Videos:**")
                                    #     display_videos(folder_info['video_paths'], property_id)
                                    # elif include_videos:
                                    #     st.info("No videos available for this property")
                                
                                # Property Analysis Data
                                if folder_info['profile_data']:
                                    st.subheader("📊 Property Analysis")
                                    
                                    # Show original description
                                    if 'description' in folder_info['profile_data']:
                                        st.write("**📝 Original Description:**")
                                        with st.container():
                                            st.text_area("", 
                                                       value=folder_info['profile_data']['description'], 
                                                       height=100, 
                                                       disabled=True, 
                                                       key=f"desc_{i}_{property_id}")
                                    
                                    # Show key analysis points
                                    if show_full_analysis:
                                        st.write("**🔍 Full Analysis Data:**")
                                        st.json(folder_info['profile_data'])
                                    else:
                                        # Show summary information
                                        analysis_data = folder_info['profile_data']
                                        if isinstance(analysis_data, dict):
                                            summary_keys = ['property_type', 'location', 'price', 'features', 'amenities', 'condition']
                                            summary_data = {k: v for k, v in analysis_data.items() if k in summary_keys and v}
                                            if summary_data:
                                                st.write("**📋 Key Features:**")
                                                st.json(summary_data)
                                
                                # Show file listing if enabled (moved inside main expander to avoid nesting)
                                if show_file_details and folder_info['exists']:
                                    st.subheader("📂 File Details")
                                    file_col1, file_col2, file_col3 = st.columns(3)
                                    
                                    with file_col1:
                                        if folder_info['images']:
                                            st.write("**📸 Image Files:**")
                                            for img in folder_info['images']:
                                                st.write(f"• {img}")
                                        else:
                                            st.write("**📸 Image Files:** None")
                                    
                                    # with file_col2:
                                    #     if folder_info['videos']:
                                    #         st.write("**🎥 Video Files:**")
                                    #         for vid in folder_info['videos']:
                                    #             st.write(f"• {vid}")
                                    #     else:
                                    #         st.write("**🎥 Video Files:** None")
                                    
                                    with file_col3:
                                        if folder_info['text_files']:
                                            st.write("**📄 Text Files:**")
                                            for txt in folder_info['text_files']:
                                                st.write(f"• {txt}")
                                        else:
                                            st.write("**📄 Text Files:** None")
                                
                                st.markdown("---")
                                
                    else:
                        st.info("🔍 No matching properties found. Try adjusting your search terms.")
                        
                        # Suggest alternative searches
                        st.subheader("💡 Search Suggestions")
                        st.write("Try searching for:")
                        suggestions = [
                            "apartment with balcony",
                            "house with parking",
                            "no AC no elevator",
                            "newly renovated",
                            "furnished flat",
                            "WiFi included"
                        ]
                        
                        suggestion_cols = st.columns(3)
                        for idx, suggestion in enumerate(suggestions):
                            with suggestion_cols[idx % 3]:
                                if st.button(f"🔍 {suggestion}", key=f"suggest_{suggestion}"):
                                    # Update the query and trigger search
                                    st.session_state.suggested_query = suggestion
                                    st.rerun()
                        
                except Exception as e:
                    # logger.error(f"Search error: {e}")
                    st.error(f"❌ Search failed: {str(e)}")
                    
                    # Show error details for debugging
                    with st.expander("🔧 Error Details (for debugging)"):
                        st.code(str(e))
                        st.write("**Search Parameters:**")
                        st.write(f"- Query: {query}")
                        st.write(f"- Max Results: {max_results}")

# Handle suggested queries
if 'suggested_query' in st.session_state:
    st.info(f"🔍 Suggested search: {st.session_state.suggested_query}")  
    # Clear the suggestion after showing it
    del st.session_state.suggested_query

# Sidebar Information
with st.sidebar:
    st.markdown("---")
    st.subheader("🗂️ System Information")
    
    # Show properties count
    properties_dir = os.path.join(os.path.dirname(__file__), "properties")
    if os.path.exists(properties_dir):
        try:
            prop_count = len([d for d in os.listdir(properties_dir) if os.path.isdir(os.path.join(properties_dir, d))])
            st.metric("Registered Properties", prop_count)
        except Exception as e:
            st.error(f"Error counting properties: {e}")
            st.write("**Registered Properties:** Error")
    else:
        st.write("**Registered Properties:** 0")
    
    # Show logs info
    # if os.path.exists(log_dir):
    #     try:
    #         log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    #         st.metric("Log Files", len(log_files))
    #     except Exception as e:
    #         st.error(f"Error reading logs: {e}")
    
    st.markdown("---")
    st.subheader("💡 Search Tips")
    st.write("**Use natural language like:**")
    st.code("• 'Flats contains of no ac, not having elevator'")
    st.code("• 'Newly renovated apartment with balcony'")
    st.code("• 'House with parking and WiFi'")
    st.code("• 'No AC and no elevator properties'")
    st.code("• 'Furnished apartment near metro'")
    
    st.markdown("---")
    st.subheader("📊 Performance")
    st.write(f"**Session State Items:** {len(st.session_state)}")
    st.write(f"**Current Time:** {datetime.now().strftime('%H:%M:%S')}")