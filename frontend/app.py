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
from utils.state_manager import init_session_state, ensure_session_hydrated
from components.error_display import show_error
from components.navigation import render_stage_stepper
import importlib
import ui.sidebar
importlib.reload(ui.sidebar)
from ui.sidebar import render_sidebar


# ========================================
# PAGE CONFIGURATION
# ========================================
st.set_page_config(
    page_title=config.PAGE_TITLE,
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


def initialize_app():
    if not check_backend_health():
        show_error(
            "Cannot connect to backend",
            f"Please ensure the backend server is running at {config.BACKEND_URL}",
        )
        st.stop()

    # Fast guarded hydration from backend cache
    ensure_session_hydrated()


# Initialize app and render sidebar
initialize_app()
render_sidebar()


# ========================================
# APP HEADER & PIPELINE STEPPER
# ========================================
st.markdown(
    """
    <div style="padding: 0.5rem 0 1rem 0;">
        <h1 style="margin: 0; font-size: 2.2rem; font-weight: 700;">Cognitive AI Learning Platform</h1>
        <p style="margin-top: 0.3rem; color: #4b5563; font-size: 1.05rem;">
            Intelligent Adaptive Learning System
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Current stage resolution
roadmap = st.session_state.get("roadmap")
current_input_id = st.session_state.get("current_input_id")
current_module = st.session_state.get("current_module")

if roadmap and current_module:
    active_stage = 3
elif roadmap:
    active_stage = 2
elif current_input_id:
    active_stage = 2
else:
    active_stage = 1

render_stage_stepper(active_stage)
st.divider()


# ========================================
# COMMAND CENTER: ACTIVE LEARNING HERO CARD
# ========================================
with st.container(border=True):
    col_hero_info, col_hero_action = st.columns([3, 2], gap="large", vertical_alignment="center")

    with col_hero_info:
        if roadmap and current_module:
            order = current_module.get('order', 1)
            total = roadmap.get('total_modules', 1)
            topic = current_module.get('topic_name', 'Current Topic')
            mode = roadmap.get('mode', 'untimed').title()

            st.markdown(f"### Active Module: **{topic}**")
            st.caption(f"Curriculum Position: Module {order} of {total} | Pacing: **{mode} Mode**")
            
            progress_pct = min(1.0, max(0.05, order / float(total)))
            st.progress(progress_pct, text=f"Course Progress: {order}/{total} Modules")

        elif roadmap:
            total = roadmap.get('total_modules', len(roadmap.get('modules', [])))
            st.markdown("### Learning Roadmap Ready")
            st.caption(f"Personalized curriculum generated with **{total} sequential modules**.")

        elif current_input_id:
            input_data = st.session_state.get('input_data', {})
            detected = input_data.get('detected_type', 'Syllabus').replace('_', ' ').title()
            st.markdown(f"### Document Ingested: **{detected}**")
            st.caption("Content validated and ready for automated roadmap generation.")

        else:
            st.markdown("### Welcome to the Learning Platform")
            st.caption("Submit course materials to generate an automated curriculum with study notes and quizzes.")

    with col_hero_action:
        if roadmap and current_module:
            if st.button("Resume Study Notes", type="primary", use_container_width=True, key="hero_btn_resume"):
                st.switch_page("pages/3_📚_Content.py")
            if st.button("Take Module Quiz", use_container_width=True, key="hero_btn_quiz"):
                st.switch_page("pages/4_🧪_Quiz.py")
        elif roadmap:
            if st.button("Open Roadmap", type="primary", use_container_width=True, key="hero_btn_open_roadmap"):
                st.switch_page("pages/2_🗺️_Roadmap.py")
        elif current_input_id:
            if st.button("Generate Roadmap", type="primary", use_container_width=True, key="hero_btn_gen_roadmap"):
                st.switch_page("pages/2_🗺️_Roadmap.py")
        else:
            if st.button("Upload Syllabus Document", type="primary", use_container_width=True, key="hero_btn_upload_doc"):
                st.switch_page("pages/1_📤_Input.py")

st.markdown("")


# ========================================
# THE 4-STAGE PIPELINE CARDS (SOLID BUTTONS)
# ========================================
st.markdown("### Learning Journey Stages")
st.caption("Click any accessible stage button to navigate directly")

p1, p2, p3, p4 = st.columns(4, gap="medium")

with p1:
    with st.container(border=True):
        st.markdown("#### Step 1: Ingestion")
        st.caption("Upload PDF, PPT, DOCX or paste notes directly.")
        if st.button("Open Input", use_container_width=True, key="pipeline_btn_1"):
            st.switch_page("pages/1_📤_Input.py")

with p2:
    with st.container(border=True):
        st.markdown("#### Step 2: Roadmap")
        st.caption("Structured curriculum with prerequisite graph.")
        can_open_roadmap = bool(current_input_id or roadmap)
        if st.button("View Roadmap", disabled=not can_open_roadmap, use_container_width=True, key="pipeline_btn_2"):
            st.switch_page("pages/2_🗺️_Roadmap.py")

with p3:
    with st.container(border=True):
        st.markdown("#### Step 3: Study")
        st.caption("In-depth study notes, cheat sheets, and doubt clearing.")
        can_open_study = bool(roadmap)
        if st.button("Study Modules", disabled=not can_open_study, use_container_width=True, key="pipeline_btn_3"):
            st.switch_page("pages/3_📚_Content.py")

with p4:
    with st.container(border=True):
        st.markdown("#### Step 4: Assessment")
        st.caption("Targeted quizzes with automated scoring and feedback.")
        can_open_quiz = bool(roadmap)
        if st.button("Module Quizzes", disabled=not can_open_quiz, use_container_width=True, key="pipeline_btn_4"):
            st.switch_page("pages/4_🧪_Quiz.py")


st.divider()

# Footer status
col_foot1, col_foot2 = st.columns(2)
with col_foot1:
    st.caption("Backend Status: Active session synchronized with local LLM service.")
with col_foot2:
    st.caption("Persistence: All generated notes and quizzes are permanently cached.")
