import sys
import os
import json
import dotenv
import streamlit as st
import time 
from streamlit_option_menu import option_menu
import pandas as pd
dotenv.load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.mainAgent import MainAnalysisAgent
from agents.searchAgent import PropertySearchAgent
from models.vectorStore import QdrantVectorStoreClient 
from components.css.css import CSS
from components.database.dbmanager import init_db
from components.utils.auth import logout_user , TOKEN_FILE 
from components.screens.registerpage import register_property_page
from components.screens.proppage import search_properties_page
from components.screens.dashboard import dashboard_page
from  components.screens.adminpage import admin_panel_page
from components.screens.loginpage import login_page 

DB_NAME = "property_manager.db"
init_db(DB_NAME)



# Initialize Agents & Vector Store
main_agent = MainAnalysisAgent()
vector_store = QdrantVectorStoreClient(
    url=os.getenv("url"),
    api_key=os.getenv("api_key"),
    collection=os.getenv("collection"),
    google_api_key=os.getenv("google_api_key"),
)
search_agent = PropertySearchAgent(vector_store)

# Streamlit Config & Styles
st.set_page_config(page_title="Flat Seller System", page_icon="🏠", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# Session State Management
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'property_id' not in st.session_state:
    st.session_state.property_id = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = None
if 'email_sent' not in st.session_state:
    st.session_state.email_sent = False
if 'email_status' not in st.session_state:
    st.session_state.email_status = None



# Property Registration Page






# Main App
def main():
    # Check for token in URL parameters
    token = st.query_params.get("token")
    
    # If not authenticated but has valid token, restore session
    if not st.session_state.get("authenticated") and token:
        try:
            with open(TOKEN_FILE, "r") as f:
                token_map = json.load(f)
            if token in token_map:
                user_data = token_map[token]
                # Check if token is expired
                if time.time() < user_data.get("expires_at", 0):
                    st.session_state.user = user_data
                    st.session_state.authenticated = True
                    st.session_state.token = token
                    st.session_state.login_time = time.time()
                    st.rerun()
                else:
                    # Token expired, remove it
                    del token_map[token]
                    with open(TOKEN_FILE, "w") as f:
                        json.dump(token_map, f)
        except Exception as e:
            st.error("Session recovery failed. Please log in again.")
            print("Token error:", e)

    # Check session timeout (1 hour)
    if st.session_state.get("authenticated") and st.session_state.get("login_time"):
        if time.time() - st.session_state.login_time > 3600:  # 1 hour timeout
            logout_user(st.session_state.token)
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.token = None
            st.session_state.login_time = None
            st.error("Your session has expired. Please log in again.")
            st.rerun()

    if not st.session_state.get("authenticated"):
        login_page()
    else:
        # Navigation for authenticated users
        with st.sidebar:
            st.image("https://www.luxurychicagoapartments.com/wp-content/uploads/2023/03/pexels-george-becker-129494-scaled-2.jpg", 
                   use_column_width=True)
            st.write(f"Welcome, **{st.session_state.user['full_name']}**")
            st.write(f"Role: **{st.session_state.user['role'].title()}**")
            
            menu_options = ["🏠 Dashboard", "📝 Register Property", "🔍 Search Properties"]
            if st.session_state.user['role'] == 'admin':
                menu_options.append("⚙️ Admin")
            
            selected = option_menu(
                menu_title="Main Menu",
                options=menu_options,
                icons=["house", "pencil-square", "search", "gear"],
                menu_icon="cast",
                default_index=0
            )
            
            st.markdown("---")
            if st.button("🚪 Logout"):
                logout_user(st.session_state.token)
                st.session_state.authenticated = False
                st.session_state.user = None
                st.session_state.token = None
                st.session_state.login_time = None
                st.query_params.clear()  # Remove token from URL
                st.rerun()
        
        # Page routing
        if selected == "🏠 Dashboard":
            dashboard_page()
        elif selected == "📝 Register Property":
            register_property_page(main_agent,vector_store)
        elif selected == "🔍 Search Properties":
            search_properties_page(search_agent)
        elif selected == "⚙️ Admin" and st.session_state.user['role'] == 'admin':
            st.header("Admin Panel")
            admin_panel_page()  # You would create this function

if __name__ == "__main__":
    main()