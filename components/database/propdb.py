
import sys
import os 
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.database.dbman import DatabaseManager, DB_NAME
import json 
# Property Management Functions
def save_property_to_db(property_id, description, analysis_json, created_by):
    db = DatabaseManager(DB_NAME)
    db.execute_query(
        "INSERT INTO properties (property_id, description, analysis_json, created_by) VALUES (?, ?, ?, ?)",
        (property_id, description, json.dumps(analysis_json), created_by)
    )
    db.close()

def save_image_to_db(property_id, image_name, image_data):
    db = DatabaseManager(DB_NAME)
    db.execute_query(
        "INSERT INTO property_images (property_id, image_name, image_data) VALUES (?, ?, ?)",
        (property_id, image_name, image_data)
    )
    db.close()

def save_video_to_db(property_id, video_name, video_data):
    db = DatabaseManager(DB_NAME)
    db.execute_query(
        "INSERT INTO property_videos (property_id, video_name, video_data) VALUES (?, ?, ?)",
        (property_id, video_name, video_data)
    )
    db.close()

def get_property_from_db(property_id):
    db = DatabaseManager(DB_NAME)
    property_data = db.fetch_one("SELECT * FROM properties WHERE property_id = ?", (property_id,))
    db.close()
    return property_data

def get_property_images(property_id):
    db = DatabaseManager(DB_NAME)
    images = db.fetch_all("SELECT * FROM property_images WHERE property_id = ?", (property_id,))
    db.close()
    return images

def get_property_videos(property_id):
    db = DatabaseManager(DB_NAME)
    videos = db.fetch_all("SELECT * FROM property_videos WHERE property_id = ?", (property_id,))
    db.close()
    return videos

def get_all_properties():
    db = DatabaseManager(DB_NAME)
    properties = db.fetch_all("SELECT * FROM properties ORDER BY created_at DESC")
    db.close()
    return properties

def log_search(user_id, query, results_count):
    db = DatabaseManager(DB_NAME)
    db.execute_query(
        "INSERT INTO search_history (user_id, query, results_count) VALUES (?, ?, ?)",
        (user_id, query, results_count)
    )
    db.close()
    

