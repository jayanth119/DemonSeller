import streamlit as st 
import os 
import sys 
import datetime
import tempfile
import shutil   
import json 
import io 
from PIL import Image
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.utils.folderUtil import clean_and_parse, generate_unique_property_id
from components.database.propdb import save_property_to_db,save_image_to_db,save_video_to_db

# Image Processing
def resize_image(image_data, max_size=(800, 800)):
    img = Image.open(io.BytesIO(image_data))
    img.thumbnail(max_size)
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return buffered.getvalue()
def register_property_page(main_agent, vector_store):
    st.header("📝 Register New Property")
    description = st.text_area("Property Description", height=200, placeholder="Enter detailed property description...")
    images = st.file_uploader("Upload Images", type=["jpg", "png", "jpeg", "gif", "bmp"], accept_multiple_files=True)
    # video = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv", "webm"], accept_multiple_files=False)

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Analyze Property"):
            if not description.strip():
                st.error("Please provide a property description.")
            elif not images:
                st.error("Please upload at least one image.")
            # elif not video:
            #     st.error("Please upload a video.")
            else:
                with st.spinner("Analyzing property..."):
                    try:
                        # Generate unique property ID at the start
                        property_id = generate_unique_property_id()
                        st.session_state.property_id = property_id
                        
                        # Create temporary directory for processing
                        temp_dir = tempfile.mkdtemp()
                        
                        # Create property structure
                        prop_dir = os.path.join(temp_dir, "property")
                        img_dir = os.path.join(prop_dir, "images")
                        # vid_dir = os.path.join(prop_dir, "videos")
                        text_dir = os.path.join(prop_dir, "text")
                        
                        # Create directories
                        for directory in [img_dir, text_dir]:
                            os.makedirs(directory, exist_ok=True)
                        
                        # Save uploaded files
                        for image in images:
                            image_path = os.path.join(img_dir, image.name)
                            with open(image_path, "wb") as f:
                                f.write(image.getbuffer())
                        
                        # Save description
                        desc_file = os.path.join(text_dir, "description.txt")
                        with open(desc_file, "w", encoding='utf-8') as f:
                            f.write(description)
                        
                        # Analyze property
                        raw_profile = main_agent.analyze_property(prop_dir)
                        profile = clean_and_parse(raw_profile)
                        
                        # Add property ID to profile
                        profile['property_id'] = property_id
                        profile['created_at'] = datetime.datetime.now().isoformat()
                        
                        # Store results in session state
                        st.session_state.analysis_result = profile
                        st.session_state.temp_files = {
                            'prop_dir': prop_dir,
                            'img_dir': img_dir,
                            # 'vid_dir': vid_dir,
                            'text_dir': text_dir,
                            'temp_dir': temp_dir,
                            'images': images  # Keep reference to uploaded images for DB storage
                        }
                        
                        st.success(f"Property analysis completed! Property ID: {property_id}")
                        
                    except Exception as e:
                        st.error(f"Error during analysis: {e}")
                        if 'temp_dir' in locals():
                            shutil.rmtree(temp_dir, ignore_errors=True)

    # Display analysis results
    if 'analysis_result' in st.session_state and st.session_state.analysis_result and 'property_id' in st.session_state and st.session_state.property_id:
        st.subheader("📊 Analysis Result")
        st.write(f"**Property ID:** {st.session_state.property_id}")
        st.json(st.session_state.analysis_result)
        
        with col2:
            if st.button("✅ Register Property"):
                try:
                    with st.spinner("Registering property..."):
                        property_id = st.session_state.property_id
                        temp_files = st.session_state.temp_files
                        
                        # Save property to database
                        save_property_to_db(
                            property_id=property_id,
                            description=description,
                            analysis_json=st.session_state.analysis_result,
                            created_by=st.session_state.user['id']
                        )
                        
                        # Save images to database
                        for image in temp_files['images']:
                            image_data = image.read()
                            compressed_image = resize_image(image_data)
                            save_image_to_db(property_id, image.name, compressed_image)
                        
                        # # Save video to database if exists
                        # if 'video' in temp_files and temp_files['video']:
                        #     video_data = temp_files['video'].read()
                        #     save_video_to_db(property_id, temp_files['video'].name, video_data)
                        
                        # Add to vector store
                        document = {
                            "id": property_id,
                            "property_id": property_id,
                            "text_description": json.dumps(st.session_state.analysis_result, ensure_ascii=False),
                            "description": description,
                            "created_at": datetime.datetime.now().isoformat()
                        }
                        
                        vector_store.add_documents([document])
                        
                        try:
                            vector_store.qdrant_client.flush(collection_name="sample", wait=True)
                        except Exception:
                            pass
                        
                        st.success(f"✅ Property registered successfully! ID: {property_id}")
                        
                        # Clean up temp files
                        try:
                            shutil.rmtree(temp_files['temp_dir'])
                        except Exception:
                            pass
                        
                        # Reset session state
                        st.session_state.analysis_result = None
                        st.session_state.temp_files = None
                        st.session_state.property_id = None
                
                except Exception as e:
                    st.error(f"Registration failed: {e}")
                    if 'temp_files' in st.session_state and st.session_state.temp_files:
                        shutil.rmtree(st.session_state.temp_files['temp_dir'], ignore_errors=True)