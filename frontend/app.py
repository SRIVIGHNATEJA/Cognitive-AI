"""
Main Streamlit application for Cognitive AI Learning Platform.

Entry point for the frontend application with navigation,
session management, and backend connectivity.
"""

import streamlit as st
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from services.api_client import api_client
from utils.state_manager import init_session_state
from components.error_display import show_error, show_success, show_info, show_warning
from ui.sidebar import render_sidebar


# Page configuration
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state="expanded"
)


def check_backend_health() -> bool:
    """
    Check if backend is reachable and healthy.
    
    Returns:
        True if backend is healthy, False otherwise
    """
    try:
        return api_client.health_check()
    except Exception as e:
        return False


def sync_backend_session():
    """
    Sync frontend state with backend session.
    
    Fetches backend session and updates frontend state.
    """
    try:
        session_data = api_client.get("/api/session")
        
        # Update frontend state
        st.session_state.backend_session_id = session_data.get('session_id')
        st.session_state.backend_session_data = session_data
        st.session_state.current_input_id = session_data.get('current_input_id')
        
        # Update roadmap state if generated
        if session_data.get('roadmap_generated', False):
            st.session_state.roadmap_mode = session_data.get('roadmap_mode')
        
        # Update current module
        if session_data.get('current_module_id'):
            st.session_state.current_module_id = session_data.get('current_module_id')
        
        return True
    
    except Exception as e:
        show_error("Failed to sync with backend", str(e))
        return False


def initialize_app():
    """Initialize application on first load."""
    # Initialize session state
    init_session_state()
    
    # Check backend health
    if not check_backend_health():
        show_error(
            "Cannot connect to backend",
            f"Please ensure the backend server is running at {config.BACKEND_URL}"
        )
        st.stop()
    
    # Sync with backend session
    if st.session_state.backend_session_id is None:
        if not sync_backend_session():
            show_warning("Could not sync with backend session. Some features may not work correctly.")


# Initialize app
initialize_app()

# Render premium sidebar
render_sidebar()

# ========================================
# COMPACT HEADER
# ========================================
st.markdown("""
<div style="padding: 1rem 0 0.5rem 0;">
    <h1 style="margin: 0; font-size: 2rem;">🧠 Cognitive AI Learning Platform</h1>
    <p style="margin: 0.5rem 0 0 0; font-size: 1rem; color: #666;">Your AI-powered learning companion</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ========================================
# MAIN DASHBOARD GRID (2 COLUMNS)
# ========================================
col_left, col_right = st.columns(2, gap="large")

# LEFT COLUMN — LEARNING OVERVIEW CARD
with col_left:
    with st.container():
        st.markdown("### 📊 Learning Overview")
        
        # Read from existing session state (read-only)
        roadmap = st.session_state.get('roadmap')
        current_module = st.session_state.get('current_module')
        
        if roadmap:
            mode = roadmap.get('mode', 'unknown').title()
            total_modules = roadmap.get('total_modules', 0)
            
            # Display learning info
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.metric("Learning Mode", mode)
            with col_info2:
                st.metric("Total Modules", total_modules)
            
            if current_module:
                topic_name = current_module.get('topic_name', 'Unknown')
                order = current_module.get('order', 0)
                
                st.divider()
                st.markdown(f"**Current Module:** {topic_name}")
                st.caption(f"Module {order} of {total_modules}")
            else:
                st.divider()
                st.caption("No module selected yet")
        else:
            # No roadmap data
            st.caption("Learning Mode: —")
            st.caption("Total Modules: —")
            st.caption("Current Module: —")
            st.caption("Module Position: —")
            
            st.divider()
            st.info("📍 Upload a syllabus to get started")

# RIGHT COLUMN — QUICK ACTIONS CARD
with col_right:
    with st.container():
        st.markdown("### ⚡ Quick Actions")
        
        current_module_id = st.session_state.get('current_module_id')
        
        if current_module_id:
            # Show action buttons
            if st.button("📚 Continue Learning", type="primary", use_container_width=True, key="home_continue"):
                st.switch_page("pages/3_📚_Content.py")
            
            if st.button("🧪 Take Quiz", use_container_width=True, key="home_quiz"):
                st.switch_page("pages/4_🧪_Quiz.py")
            
            st.divider()
            st.caption("Navigate to your current module")
        else:
            st.caption("Complete setup to unlock quick actions")
            
            st.divider()
            
            # Show setup guidance
            if not st.session_state.get('current_input_id'):
                if st.button("📤 Upload Syllabus", type="primary", use_container_width=True, key="home_input"):
                    st.switch_page("pages/1_📤_Input.py")
            elif not st.session_state.get('roadmap'):
                if st.button("🗺️ Generate Roadmap", type="primary", use_container_width=True, key="home_roadmap"):
                    st.switch_page("pages/2_🗺️_Roadmap.py")

st.divider()

# ========================================
# CONDENSED "HOW IT WORKS" CARD
# ========================================
with st.container():
    st.markdown("### 🎯 How It Works")
    
    # 2x2 grid layout
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        st.markdown("""
        **1. 📤 Upload Syllabus**  
        Provide your course content
        
        **2. 🗺️ Generate Roadmap**  
        AI creates personalized path
        """)
    
    with col2:
        st.markdown("""
        **3. 📚 Study Materials**  
        Access notes & cheat sheets
        
        **4. 🧪 Test Knowledge**  
        Take quizzes & track progress
        """)

st.divider()

# Footer
st.caption("Use the sidebar to navigate your learning journey.")
