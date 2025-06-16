import streamlit as st
import os
import sys 
import time 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.utils.auth import authenticate_user, create_user 

# Login Page
def login_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="login-header">
            <h1>🏠 Flat Seller System</h1>
            <p>Professional Property Management Platform</p>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Sign Up"])
    
    with tab1:
        st.markdown("### Welcome Back")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit_button:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.success(f"Welcome back, {user['full_name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
       
        st.markdown("---")
        st.info("""
        **Demo Credentials:**
        - **Admin:** admin / admin123
        - **Agent 1:** agent1 / agent123  
        - **Agent 2:** agent2 / agent123
        """)
    
    with tab2:
        st.markdown("### Create New Account")
        with st.form("signup_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", placeholder="Choose a username")
                new_full_name = st.text_input("Full Name*", placeholder="Enter your full name")
                new_email = st.text_input("Email*", placeholder="Enter your email")
            
            with col2:
                new_password = st.text_input("Password*", type="password", placeholder="Choose a password")
                new_role = st.selectbox("Role*", ["agent", "admin"])
            
            signup_button = st.form_submit_button("Create Account", use_container_width=True)
            
            if signup_button:
                if new_username and new_password and new_full_name and new_email:
                    if len(new_password) < 6:
                        st.error("⚠️ Password must be at least 6 characters long")
                    else:
                        success = create_user(new_username, new_password, new_full_name, new_email, new_role)
                        if success:
                            st.success("✅ Account created successfully! You can now sign in.")
                        else:
                            st.error("❌ Username already exists. Please choose a different username.")
                else:
                    st.error("⚠️ Please fill in all required fields")
    
    st.markdown("</div>", unsafe_allow_html=True)