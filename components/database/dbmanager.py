import sqlite3
# Database Configuration
import sys
import os 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.utils.auth import hash_password

DB_NAME = "property_manager.db"
def init_db(DB_NAME):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Properties table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL,
        analysis_json TEXT NOT NULL,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    ''')
    
    # Property Images table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS property_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id TEXT NOT NULL,
        image_name TEXT NOT NULL,
        image_data BLOB NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(property_id)
    )
    ''')
    
    # Property Videos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS property_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id TEXT NOT NULL,
        video_name TEXT NOT NULL,
        video_data BLOB NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(property_id)
    )
    ''')
    
    # Search History table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        results_count INTEGER NOT NULL,
        searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Check if demo users already exist
    cursor.execute("SELECT COUNT(*) FROM users WHERE username IN ('admin', 'agent1', 'agent2')")
    demo_users_exist = cursor.fetchone()[0] > 0
    
    if not demo_users_exist:
        # Create demo users
        demo_users = [
            {
                'username': 'admin',
                'password': 'admin123',
                'full_name': 'Admin User',
                'email': 'admin@example.com',
                'role': 'admin'
            },
            {
                'username': 'agent1',
                'password': 'agent123',
                'full_name': 'Agent One',
                'email': 'agent1@example.com',
                'role': 'agent'
            },
            {
                'username': 'agent2',
                'password': 'agent123',
                'full_name': 'Agent Two',
                'email': 'agent2@example.com',
                'role': 'agent'
            }
        ]
        
        for user in demo_users:
            hashed_password = hash_password(user['password'])
            try:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
                    (user['username'], hashed_password, user['full_name'], user['email'], user['role'])
                )
            except sqlite3.IntegrityError:
                pass  # User already exists
        
        # Create some demo properties if needed
        # demo_properties = [
        #     {
        #         'property_id': 'prop_1001',
        #         'description': 'Modern 2-bedroom apartment with balcony and AC',
        #         'analysis_json': json.dumps({
        #             'property_type': 'apartment',
        #             'location': 'Downtown',
        #             'price': 250000,
        #             'features': ['balcony', 'AC', 'modern kitchen'],
        #             'amenities': ['gym', 'pool'],
        #             'condition': 'excellent'
        #         }),
        #         'created_by': 1  # admin user
        #     },
        #     {
        #         'property_id': 'prop_1002',
        #         'description': 'Cozy studio near university, no AC but has WiFi',
        #         'analysis_json': json.dumps({
        #             'property_type': 'studio',
        #             'location': 'University District',
        #             'price': 120000,
        #             'features': ['WiFi', 'furnished'],
        #             'amenities': ['laundry', 'bike storage'],
        #             'condition': 'good'
        #         }),
        #         'created_by': 2  # agent1
        #     }
        # ]
        
        # for prop in demo_properties:
        #     try:
        #         cursor.execute(
        #             "INSERT INTO properties (property_id, description, analysis_json, created_by) VALUES (?, ?, ?, ?)",
        #             (prop['property_id'], prop['description'], prop['analysis_json'], prop['created_by'])
        #         )
            except sqlite3.IntegrityError:
                pass  # Property already exists
    
    conn.commit()
    conn.close()
