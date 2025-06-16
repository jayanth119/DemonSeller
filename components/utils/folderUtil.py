import streamlit as st
import os
import uuid
import re 
import json 
import shutil
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
            # loggger.info(f"Saved {target}")
        except Exception as e:
            # loggger.error(f"Failed to save {f.name}: {e}")
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
        # loggger.warning(f"Failed to parse as JSON: {e}, returning raw string.")
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
                    # loggger.info(f"Copied {src_path} to {dest_path}")
        return True
    except Exception as e:
        # loggger.error(f"Error copying files from {src_dir} to {dest_dir}: {e}")
        return False

def get_property_folder_info(property_id):
    """Get folder information for a specific property ID"""
    properties_dir = os.path.join(os.path.dirname(__file__), "properties")
    property_path = os.path.join(properties_dir, property_id)
    
    folder_info = {
        'property_id': property_id,
        'exists': False,
        'images': [],
        # 'videos': [],
        'text_files': [],
        'profile_data': None,
        'image_paths': [],
        # 'video_paths': []
    }
    
    if os.path.exists(property_path):
        folder_info['exists'] = True
        
        # Get images with full paths
        img_dir = os.path.join(property_path, "images")
        if os.path.exists(img_dir):
            image_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            folder_info['images'] = image_files
            folder_info['image_paths'] = [os.path.join(img_dir, f) for f in image_files]
        
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
                    # loggger.error(f"Failed to load profile data for {property_id}: {e}")
        
        # loggger.info(f"Retrieved folder info for property {property_id}")
    else:
        pass 
        # loggger.warning(f"Property folder not found: {property_path}")
    
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
