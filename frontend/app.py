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


# Main content
st.title(f"{config.PAGE_ICON} {config.PAGE_TITLE}")

st.markdown("""
Welcome to the Cognitive AI Learning Platform! This platform helps you learn effectively
by generating personalized roadmaps, study materials, quizzes, and analytics.

### Getting Started

1. **📤 Input**: Upload your syllabus or question bank
2. **🗺️ Roadmap**: Generate a personalized learning roadmap
3. **📚 Content**: Access notes and cheat sheets for each module
4. **📝 Quiz**: Test your knowledge with AI-generated quizzes
5. **📊 Analytics**: Track your progress and identify weak areas
6. **❓ Doubt**: Ask questions about any module

Use the sidebar to navigate between pages.
""")

# Sidebar
with st.sidebar:
    st.header("Navigation")
    st.markdown("Use the pages above to navigate through the platform.")
    
    st.divider()
    
    # Session info
    st.subheader("Session Info")
    
    if st.session_state.backend_session_id:
        st.success("✅ Connected to backend")
        
        # Show session details
        with st.expander("Session Details"):
            st.text(f"Session ID: {st.session_state.backend_session_id[:16]}...")
            
            if st.session_state.current_input_id:
                st.text(f"Input ID: {st.session_state.current_input_id[:16]}...")
            
            if st.session_state.roadmap:
                st.text(f"Roadmap: {len(st.session_state.roadmap.get('modules', []))} modules")
            
            if st.session_state.current_module_id:
                st.text(f"Current Module: {st.session_state.current_module_id[:16]}...")
    else:
        st.warning("⚠️ Not connected to backend")
    
    # Refresh button
    if st.button("🔄 Refresh Session"):
        with st.spinner("Syncing with backend..."):
            if sync_backend_session():
                show_success("Session refreshed successfully")
                st.rerun()
            else:
                show_error("Failed to refresh session")
    
    st.divider()
    
    # Backend info
    st.subheader("Backend Info")
    st.text(f"URL: {config.BACKEND_URL}")
    
    # Health check
    if st.button("🏥 Check Backend Health"):
        with st.spinner("Checking backend health..."):
            if check_backend_health():
                show_success("Backend is healthy")
            else:
                show_error("Backend is not responding")
    
    st.divider()
    
    # Help section
    with st.expander("ℹ️ Help"):
        st.markdown("""
        **Need help?**
        
        - Check that the backend is running
        - Refresh the session if data seems out of sync
        - Navigate using the sidebar pages
        - Each page has its own instructions
        """)


# Footer
st.divider()
st.caption(f"Cognitive AI Learning Platform | Backend: {config.BACKEND_URL}")
