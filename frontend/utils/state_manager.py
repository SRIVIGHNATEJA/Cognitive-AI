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
        
    if 'raw_input_text' not in st.session_state:
        st.session_state.raw_input_text = ""
        
    if '_hydrated' not in st.session_state:
        st.session_state._hydrated = False
    
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


def reset_course_state():
    """Reset all course, roadmap, and content session state."""
    st.session_state.roadmap = None
    st.session_state.roadmap_mode = None
    st.session_state.current_module_id = None
    st.session_state.current_module = None
    st.session_state.current_input_id = None
    st.session_state.input_data = None
    st.session_state.raw_input_text = ""
    st.session_state.cached_notes = {}
    st.session_state.cached_cheatsheets = {}
    st.session_state.doubt_history = []
    reset_quiz_state()


def reset_entire_platform():
    """
    Completely reset the platform back to its pristine initial state:
    1. Cascading backend purge: deletes roadmap, content, quizzes, analytics, and input cache.
    2. Resets backend session to a new session_id and writes clean session.json.
    3. Clears all Streamlit session_state keys.
    4. Reinitializes clean state keys and syncs backend_session_id.
    5. Sets _hydrated = True so cold-start hydration doesn't restore old data.
    """
    try:
        from services.api_client import api_client
        from services.roadmap_service import roadmap_service
        
        # 1. Cascading cache flushes on backend
        try:
            roadmap_service.delete_roadmap()
        except Exception:
            pass

        try:
            api_client.post("/api/session/reset")
        except Exception:
            pass

        # 2. Re-fetch pristine new session
        try:
            new_sess = api_client.get("/api/session")
        except Exception:
            new_sess = None
    except Exception:
        new_sess = None

    # 3. Clear all frontend session state keys
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # 4. Reinitialize default state structure
    init_session_state()

    # 5. Populate fresh session info
    if new_sess:
        st.session_state.backend_session_id = new_sess.get("session_id")
        st.session_state.backend_session_data = new_sess

    st.session_state._hydrated = True


def ensure_session_hydrated():
    """
    Hydrate frontend state from backend cache on cold browser refreshes (F5/CMD+R).
    Guarded by st.session_state._hydrated to run strictly once per browser tab session.
    """
    init_session_state()
    if st.session_state.get("_hydrated", False):
        return

    try:
        from services.api_client import api_client
        from services.roadmap_service import roadmap_service

        # 1. Fetch active session state from backend
        session_data = api_client.get("/api/session")
        if session_data:
            st.session_state.backend_session_id = session_data.get("session_id")
            st.session_state.backend_session_data = session_data
            input_id = session_data.get("current_input_id")
            if input_id:
                st.session_state.current_input_id = input_id

            # 2. If roadmap generated, fetch and hydrate roadmap
            if session_data.get("roadmap_generated"):
                cached_rm = roadmap_service.get_roadmap()
                if cached_rm and cached_rm.get("modules"):
                    st.session_state.roadmap = cached_rm
                    st.session_state.roadmap_mode = cached_rm.get(
                        "mode", session_data.get("roadmap_mode", "untimed")
                    )

                    # Hydrate active module
                    cur_mod_id = session_data.get("current_module_id")
                    modules = cached_rm.get("modules", [])
                    if cur_mod_id:
                        st.session_state.current_module_id = cur_mod_id
                        st.session_state.current_module = next(
                            (m for m in modules if m.get("module_id") == cur_mod_id),
                            modules[0] if modules else None,
                        )
                    elif modules:
                        st.session_state.current_module = modules[0]
                        st.session_state.current_module_id = modules[0].get("module_id")

            # 3. If input_id exists, fetch input details & restore raw text memory
            if input_id:
                try:
                    from services.input_service import input_service

                    inp_data = input_service.get_input_status(input_id)
                    if inp_data:
                        st.session_state.input_data = inp_data
                        if inp_data.get("extracted_text"):
                            st.session_state.raw_input_text = inp_data["extracted_text"]
                except Exception:
                    pass
    except Exception:
        # Graceful fallback if backend is momentarily unreachable
        pass
    finally:
        st.session_state._hydrated = True
