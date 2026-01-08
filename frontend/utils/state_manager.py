"""
Session state management utilities for Streamlit.

Provides helpers for initializing and managing session state keys.
"""

import streamlit as st
from typing import Any, Optional


def init_session_state():
    """
    Initialize all mandatory session state keys.
    
    Should be called once on app load to ensure all keys exist.
    """
    # Backend session tracking
    if 'backend_session_id' not in st.session_state:
        st.session_state.backend_session_id = None
    
    if 'backend_session_data' not in st.session_state:
        st.session_state.backend_session_data = None
    
    # Input tracking
    if 'current_input_id' not in st.session_state:
        st.session_state.current_input_id = None
    
    if 'input_data' not in st.session_state:
        st.session_state.input_data = None
    
    # Roadmap tracking
    if 'roadmap' not in st.session_state:
        st.session_state.roadmap = None
    
    if 'roadmap_mode' not in st.session_state:
        st.session_state.roadmap_mode = None
    
    # Module tracking
    if 'current_module_id' not in st.session_state:
        st.session_state.current_module_id = None
    
    if 'current_module' not in st.session_state:
        st.session_state.current_module = None
    
    # Content caching (frontend-side)
    if 'cached_notes' not in st.session_state:
        st.session_state.cached_notes = {}
    
    if 'cached_cheatsheets' not in st.session_state:
        st.session_state.cached_cheatsheets = {}
    
    # Quiz tracking
    if 'current_quiz' not in st.session_state:
        st.session_state.current_quiz = None
    
    if 'quiz_answers' not in st.session_state:
        st.session_state.quiz_answers = {}
    
    if 'quiz_start_time' not in st.session_state:
        st.session_state.quiz_start_time = None
    
    if 'quiz_submitted' not in st.session_state:
        st.session_state.quiz_submitted = False
    
    # Doubt tracking (frontend-only)
    if 'doubt_history' not in st.session_state:
        st.session_state.doubt_history = []
    
    # UI state
    if 'loading' not in st.session_state:
        st.session_state.loading = False
    
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None
    
    if 'success_message' not in st.session_state:
        st.session_state.success_message = None


def get_state(key: str, default: Any = None) -> Any:
    """
    Safely get session state value.
    
    Args:
        key: Session state key
        default: Default value if key doesn't exist
        
    Returns:
        Session state value or default
    """
    return st.session_state.get(key, default)


def set_state(key: str, value: Any):
    """
    Set session state value.
    
    Args:
        key: Session state key
        value: Value to set
    """
    st.session_state[key] = value


def clear_state(key: str):
    """
    Clear session state value.
    
    Args:
        key: Session state key to clear
    """
    if key in st.session_state:
        st.session_state[key] = None


def reset_quiz_state():
    """Reset all quiz-related session state."""
    st.session_state.current_quiz = None
    st.session_state.quiz_answers = {}
    st.session_state.quiz_start_time = None
    st.session_state.quiz_submitted = False


def reset_all_state():
    """Reset all session state (except backend session)."""
    # Keep backend session
    backend_session_id = st.session_state.backend_session_id
    backend_session_data = st.session_state.backend_session_data
    
    # Clear all state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Reinitialize
    init_session_state()
    
    # Restore backend session
    st.session_state.backend_session_id = backend_session_id
    st.session_state.backend_session_data = backend_session_data
