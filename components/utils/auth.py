
import hashlib


import sys
import os 
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.database.dbman import DatabaseManager, DB_NAME
import json 
# from agents.mainAgent import MainAnalysisAgent
# from agents.searchAgent import PropertySearchAgent
# from models.vectorStore import QdrantVectorStoreClient
# from components.utils.emailUtil import share_property_results 
# from components.css.css import CSS
# from components.utils.folderUtil import clean_and_parse, generate_unique_property_id
# from components.database.dbmanager import init_db

TOKEN_FILE = "tokens.json"
SESSION_TIMEOUT = 3600
def logout_user(token):
    """Remove token from active sessions"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token_map = json.load(f)
            if token in token_map:
                del token_map[token]
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_map, f)
    except Exception as e:
        print("Logout error:", e)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
# Initialize Database

def authenticate_user(username, password):
    db = DatabaseManager(DB_NAME)
    user = db.fetch_one("SELECT * FROM users WHERE username = ?", (username,))
    db.close()
    
    if user and verify_password(user['password_hash'], password):
        return dict(user)
    return None

def create_user(username, password, full_name, email, role):
    hashed_password = hash_password(password)
    try:
        db = DatabaseManager(DB_NAME)
        db.execute_query(
            "INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_password, full_name, email, role)
        )
        db.close()
        return True
    except sqlite3.IntegrityError:
        return False
    

def verify_password(hashed_password, user_password):
    return hashed_password == hash_password(user_password)