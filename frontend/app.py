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
from components.error_display import show_error, show_warning
from ui.sidebar import render_sidebar


# ========================================
# PAGE CONFIGURATION
# ========================================
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state="expanded",
)


# ========================================
# BACKEND HEALTH & SESSION SYNC
# ========================================
def check_backend_health() -> bool:
    try:
        return api_client.health_check()
    except Exception:
        return False


def sync_backend_session():
    try:
        session_data = api_client.get("/api/session")

        st.session_state.backend_session_id = session_data.get("session_id")
        st.session_state.backend_session_data = session_data
        st.session_state.current_input_id = session_data.get("current_input_id")

        if session_data.get("roadmap_generated"):
            st.session_state.roadmap_mode = session_data.get("roadmap_mode")

        if session_data.get("current_module_id"):
            st.session_state.current_module_id = session_data.get("current_module_id")

        return True

    except Exception as e:
        show_error("Failed to sync with backend", str(e))
        return False


def initialize_app():
    init_session_state()

    if not check_backend_health():
        show_error(
            "Cannot connect to backend",
            f"Please ensure the backend server is running at {config.BACKEND_URL}",
        )
        st.stop()

    if st.session_state.backend_session_id is None:
        sync_backend_session()


# ========================================
# INITIALIZE APP
# ========================================
initialize_app()

# Render premium sidebar (already transformed)
render_sidebar()


# ========================================
# HEADER
# ========================================
st.markdown(
    """
<div style="padding: 1rem 0 0.5rem 0;">
    <h1 style="margin:0;font-size:2rem;">🧠 Cognitive AI Learning Platform</h1>
    <p style="margin-top:0.4rem;color:#666;">
        Your AI-powered learning companion
    </p>
</div>
""",
    unsafe_allow_html=True,
)

st.divider()


# ========================================
# MAIN DASHBOARD GRID
# ========================================
col_left, col_right = st.columns(2, gap="large")


# -------- LEFT: LEARNING OVERVIEW --------
with col_left:
    with st.container():
        st.markdown("### 📊 Learning Overview")

        roadmap = st.session_state.get("roadmap")
        current_module = st.session_state.get("current_module")

        m1, m2, m3 = st.columns(3)

        with m1:
            st.metric(
                "Mode",
                roadmap.get("mode", "—").title() if roadmap else "—",
            )

        with m2:
            st.metric(
                "Modules",
                roadmap.get("total_modules", "—") if roadmap else "—",
            )

        with m3:
            if roadmap and current_module:
                st.metric(
                    "Position",
                    f"{current_module.get('order')} / {roadmap.get('total_modules')}",
                )
            else:
                st.metric("Position", "—")

        st.divider()

        if current_module:
            st.markdown(
                f"**Current Module:** {current_module.get('topic_name', 'Unknown')}"
            )
            st.caption("Continue where you last stopped")
        else:
            st.info("📍 Upload a syllabus to start your learning journey")


# -------- RIGHT: QUICK ACTIONS --------
with col_right:
    with st.container():
        st.markdown("### ⚡ Quick Actions")

        if st.session_state.get("current_module_id"):
            st.button(
                "📚 Continue Learning",
                type="primary",
                use_container_width=True,
                key="home_continue",
                on_click=lambda: st.switch_page("pages/3_📚_Content.py"),
            )

            st.button(
                "🧪 Take Quiz",
                use_container_width=True,
                key="home_quiz",
                on_click=lambda: st.switch_page("pages/4_🧪_Quiz.py"),
            )

            st.caption("Resume your active learning path")

        else:
            if not st.session_state.get("current_input_id"):
                st.button(
                    "📤 Upload Syllabus",
                    type="primary",
                    use_container_width=True,
                    key="home_input",
                    on_click=lambda: st.switch_page("pages/1_📤_Input.py"),
                )

            elif not st.session_state.get("roadmap"):
                st.button(
                    "🗺️ Generate Roadmap",
                    type="primary",
                    use_container_width=True,
                    key="home_roadmap",
                    on_click=lambda: st.switch_page("pages/2_🗺️_Roadmap.py"),
                )

st.divider()


# ========================================
# CONTEXTUAL GUIDANCE (ALIVE FEEL)
# ========================================
with st.container():
    st.markdown("### 🧭 What’s Next")

    if st.session_state.get("current_module_id"):
        st.info(
            "➡️ **Recommended:** Study the current module, then attempt the quiz to reinforce learning."
        )
    elif st.session_state.get("roadmap"):
        st.info("➡️ **Recommended:** Select a module from the roadmap to begin.")
    else:
        st.info("➡️ **Recommended:** Upload a syllabus to generate your learning path.")


st.divider()


# ========================================
# SESSION STATUS SNAPSHOT
# ========================================
with st.container():
    st.markdown("### 🧠 Session Status")

    s1, s2, s3 = st.columns(3)

    with s1:
        st.success("Roadmap Ready" if st.session_state.get("roadmap") else "No Roadmap")

    with s2:
        st.success(
            "Content Available" if st.session_state.get("roadmap") else "—"
        )

    with s3:
        st.success(
            "Quiz Attempts Found"
            if st.session_state.get("quiz_attempts")
            else "No Quiz Attempts"
        )

st.divider()


# ========================================
# HOW IT WORKS — DENSE GRID
# ========================================
with st.container():
    st.markdown("### 🎯 How It Works")

    h1, h2, h3, h4 = st.columns(4)

    with h1:
        st.markdown("**📤 Upload**")
        st.caption("Provide syllabus or notes")

    with h2:
        st.markdown("**🗺️ Roadmap**")
        st.caption("AI builds learning path")

    with h3:
        st.markdown("**📚 Study**")
        st.caption("Notes & cheat sheets")

    with h4:
        st.markdown("**🧪 Quiz**")
        st.caption("Test & track progress")

st.divider()

st.caption("Use the sidebar to navigate your learning journey.")
