import os 
import sys 
import streamlit as st
import pandas as pd 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.database.dbman import DatabaseManager, DB_NAME
from components.utils.auth import create_user
def admin_panel_page():
    """Admin-specific functionality"""
    st.header("Admin Panel")
    st.subheader("User Management")
    
    # Show all users
    db = DatabaseManager(DB_NAME)
    users = db.fetch_all("SELECT * FROM users")
    db.close()
    
    st.dataframe(pd.DataFrame(users))
    
    # Add new user form
    with st.expander("Add New User"):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_full_name = st.text_input("Full Name")
                new_email = st.text_input("Email")
            with col2:
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["admin", "agent"])
            
            if st.form_submit_button("Create User"):
                if new_username and new_password and new_full_name and new_email:
                    if create_user(new_username, new_password, new_full_name, new_email, new_role):
                        st.success("User created successfully!")
                        st.rerun()
                    else:
                        st.error("Username already exists")
                else:
                    st.error("Please fill all fields")