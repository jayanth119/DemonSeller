import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import json
from typing import List, Dict, Any
import uuid
import pickle
import shutil
from datetime import datetime

class PropertyVectorStore:
    def __init__(self, persist_directory: str = "property_db"):
        self.persist_directory = persist_directory
        self.media_directory = os.path.join(persist_directory, "media")
        os.makedirs(persist_directory, exist_ok=True)
        os.makedirs(self.media_directory, exist_ok=True)
        
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize FAISS index
        self.dimension = 384  # dimension of the embeddings
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Load existing data if available
        self.properties = {}
        self.load_data()
    
    def _save_media_file(self, file_path: str, property_id: str, file_type: str) -> str:
        """Save media file to the media directory"""
        if not os.path.exists(file_path):
            return None
            
        # Create property-specific directory
        property_dir = os.path.join(self.media_directory, property_id)
        os.makedirs(property_dir, exist_ok=True)
        
        # Generate new filename
        filename = f"{file_type}_{os.path.basename(file_path)}"
        new_path = os.path.join(property_dir, filename)
        
        # Copy file to media directory
        shutil.copy2(file_path, new_path)
        return new_path
    
    def load_data(self):
        """Load existing data from disk"""
        try:
            # Load index
            if os.path.exists(os.path.join(self.persist_directory, "index.faiss")):
                self.index = faiss.read_index(os.path.join(self.persist_directory, "index.faiss"))
            
            # Load properties metadata
            if os.path.exists(os.path.join(self.persist_directory, "properties.pkl")):
                with open(os.path.join(self.persist_directory, "properties.pkl"), "rb") as f:
                    self.properties = pickle.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            self.properties = {}
    
    def save_data(self):
        """Save data to disk"""
        try:
            # Save index
            faiss.write_index(self.index, os.path.join(self.persist_directory, "index.faiss"))
            
            # Save properties metadata
            with open(os.path.join(self.persist_directory, "properties.pkl"), "wb") as f:
                pickle.dump(self.properties, f)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def add_property(self, 
                    text_description: str,
                    images: List[str] = None,
                    video_path: str = None,
                    metadata: Dict[str, Any] = None) -> str:
        """
        Add a new property to the vector store
        """
        property_id = str(uuid.uuid4())
        
        # Save media files
        saved_image_paths = []
        if images:
            for img_path in images:
                saved_path = self._save_media_file(img_path, property_id, "image")
                if saved_path:
                    saved_image_paths.append(saved_path)
        
        saved_video_path = None
        if video_path:
            saved_video_path = self._save_media_file(video_path, property_id, "video")
        
        # Prepare metadata
        property_metadata = {
            "property_id": property_id,
            "text_description": text_description,
            "has_images": bool(saved_image_paths),
            "has_video": bool(saved_video_path),
            "image_paths": saved_image_paths,
            "video_path": saved_video_path,
            "registered_date": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        # Generate embedding
        embedding = self.model.encode([text_description])[0]
        
        # Add to FAISS index
        self.index.add(np.array([embedding]))
        
        # Store metadata
        self.properties[property_id] = {
            "embedding_index": self.index.ntotal - 1,  # Store the index in FAISS
            "metadata": property_metadata
        }
        
        # Save to disk
        self.save_data()
        
        return property_id
    
    def search_properties(self, 
                         query: str,
                         n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for properties based on query
        """
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]
        
        # Search in FAISS
        distances, indices = self.index.search(np.array([query_embedding]), n_results)
        
        # Prepare results
        properties = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # Skip invalid indices
                continue
                
            # Find property with this index
            property_id = None
            for pid, data in self.properties.items():
                if data["embedding_index"] == idx:
                    property_id = pid
                    break
            
            if property_id:
                metadata = self.properties[property_id]["metadata"]
                properties.append({
                    'id': property_id,
                    'description': metadata['text_description'],
                    'metadata': metadata,
                    'distance': float(distance)
                })
        
        return properties
    
    def get_property(self, property_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific property by ID
        """
        if property_id not in self.properties:
            return None
            
        metadata = self.properties[property_id]["metadata"]
        return {
            'id': property_id,
            'description': metadata['text_description'],
            'metadata': metadata
        }
    
    def update_property(self,
                       property_id: str,
                       text_description: str = None,
                       metadata: Dict[str, Any] = None) -> bool:
        """
        Update an existing property
        """
        try:
            if property_id not in self.properties:
                return False
                
            current = self.properties[property_id]
            current_metadata = current["metadata"]
            
            # Update metadata
            if metadata:
                current_metadata.update(metadata)
            
            # Update text and embedding if description changed
            if text_description:
                current_metadata["text_description"] = text_description
                new_embedding = self.model.encode([text_description])[0]
                
                # Update FAISS index
                self.index.reconstruct(current["embedding_index"], new_embedding)
            
            # Save changes
            self.save_data()
            return True
            
        except Exception as e:
            print(f"Error updating property: {e}")
            return False
    
    def delete_property(self, property_id: str) -> bool:
        """
        Delete a property from the vector store
        """
        try:
            if property_id not in self.properties:
                return False
                
            # Remove from FAISS index
            idx = self.properties[property_id]["embedding_index"]
            self.index.remove_ids(np.array([idx]))
            
            # Remove media files
            property_dir = os.path.join(self.media_directory, property_id)
            if os.path.exists(property_dir):
                shutil.rmtree(property_dir)
            
            # Remove from properties
            del self.properties[property_id]
            
            # Update indices for remaining properties
            for pid, data in self.properties.items():
                if data["embedding_index"] > idx:
                    data["embedding_index"] -= 1
            
            # Save changes
            self.save_data()
            return True
            
        except Exception as e:
            print(f"Error deleting property: {e}")
            return False 