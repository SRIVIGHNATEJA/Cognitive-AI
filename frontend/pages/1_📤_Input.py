"""
Input page - Upload files or enter text.

Allows users to provide educational content (syllabus or question bank)
via file upload or direct text input.
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from services.input_service import input_service
from services.roadmap_service import roadmap_service
from utils.state_manager import ensure_session_hydrated, reset_course_state
from utils.validators import validate_file_upload, validate_text_input
from utils.formatters import format_file_size
from components.loading_spinner import with_loading
from components.error_display import (
    show_error, show_success, show_info, show_warning,
    handle_api_error, display_session_messages
)
from components.navigation import render_page_header, render_bottom_nav
import importlib
import ui.sidebar
importlib.reload(ui.sidebar)
from ui.sidebar import render_sidebar

# Page configuration
st.set_page_config(
    page_title="Input",
    layout=config.LAYOUT
)

# Ensure state is hydrated from backend cache before rendering
ensure_session_hydrated()

# Render sidebar
render_sidebar()

HELP_TEXT = """
### How to use this page

1. **Choose your input method:**
   - Upload a file (PDF, PPT, DOCX) via the **Upload File** tab.
   - Or paste plain text directly in the **Direct Text Input** tab.

2. **Provide your content:**
   - **Syllabus:** Course outline, topics, schedule.
   - **Question Bank:** Practice questions, past papers.
   - **Mixed:** Combination of syllabus and questions.

3. **Process your input:**
   - Click the process button.
   - Verification typically takes 5–15 seconds.
   - Once validated, click **Proceed to Roadmap**.

### Specifications
- Supported formats: PDF, PPT, PPTX, DOC, DOCX.
- Maximum file size: 10 MB.
- Content is automatically normalized and parsed into structural topics.
"""

# Render clean modern page header with popover help and stage stepper
render_page_header(
    title="Input & Content Ingestion",
    subtitle="Provide course syllabus or notes to initialize your personalized curriculum",
    current_stage=1,
    help_text=HELP_TEXT
)

# Display any session messages
display_session_messages()


# ========================================
# INTENT CONFIRMATION DIALOG (MODAL)
# ========================================
@st.dialog("Active Course Detected")
def confirm_replace_dialog(action_type: str, action_data: dict):
    active_rm = st.session_state.get('roadmap', {})
    total_mods = active_rm.get('total_modules', len(active_rm.get('modules', [])))
    
    st.markdown(
        f"""
        You already have an active learning course with **{total_mods} structured modules** in progress.
        
        Submitting this new material will reset your active roadmap, notes, and quiz progress to build a **brand-new curriculum** tailored to this content.
        """
    )
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        if st.button("✨ Replace & Start Fresh", type="primary", use_container_width=True, key="dialog_btn_replace"):
            try:
                roadmap_service.delete_roadmap()
            except Exception:
                pass
            reset_course_state()
            
            if action_type == "text":
                _execute_text_submission(action_data["content"], action_data["hint"])
            elif action_type == "file":
                _execute_file_upload(action_data["file_bytes"], action_data["filename"])
    with col2:
        if st.button("📖 Keep Existing Course", use_container_width=True, key="dialog_btn_keep"):
            st.switch_page("pages/2_🗺️_Roadmap.py")


# ========================================
# SUBMISSION EXECUTION HANDLERS
# ========================================
def _execute_text_submission(content: str, hint: Optional[str]):
    def submit_action():
        return input_service.submit_text(content, hint)

    try:
        result = with_loading(
            submit_action,
            loading_message="Analyzing text content...",
            info_message="Extracting topics and detecting structure..."
        )
        if result:
            st.session_state.current_input_id = result.get('input_id')
            st.session_state.input_data = {
                'input_id': result.get('input_id'),
                'detected_type': result.get('detected_type'),
                'extracted_text_length': result.get('extracted_text_length'),
                'original_filename': None
            }
            st.session_state.raw_input_text = content
            show_success("Text processed successfully.")
            st.switch_page("pages/2_🗺️_Roadmap.py")
    except Exception as e:
        handle_api_error(e, "Text submission")


def _execute_file_upload(file_bytes: bytes, filename: str):
    def upload_action():
        return input_service.upload_file(file_bytes, filename)

    try:
        result = with_loading(
            upload_action,
            loading_message="Uploading and extracting text...",
            info_message="Processing document structure. Please wait..."
        )
        if result:
            st.session_state.current_input_id = result.get('input_id')
            st.session_state.input_data = {
                'input_id': result.get('input_id'),
                'detected_type': result.get('detected_type'),
                'extracted_text_length': result.get('extracted_text_length'),
                'original_filename': result.get('original_filename')
            }
            if result.get('extracted_text'):
                st.session_state.raw_input_text = result['extracted_text']
            show_success("File processed successfully.")
            st.switch_page("pages/2_🗺️_Roadmap.py")
    except Exception as e:
        handle_api_error(e, "File upload")


# ========================================
# NON-BLOCKING ACTIVE COURSE HERO BANNER
# ========================================
active_roadmap = st.session_state.get('roadmap')
if active_roadmap and active_roadmap.get('modules'):
    total_mods = active_roadmap.get('total_modules', len(active_roadmap.get('modules', [])))
    first_mod_title = active_roadmap['modules'][0].get('topic_name', 'Active Topic')
    pacing_mode = active_roadmap.get('mode', 'untimed').title()

    with st.container(border=True):
        c_banner_text, c_banner_btn = st.columns([3, 1], gap="medium", vertical_alignment="center")
        with c_banner_text:
            st.markdown(
                f"""
                <div style="padding: 0.1rem 0;">
                    <span style="font-size: 0.72rem; font-weight: 700; color: #6366f1; letter-spacing: 0.8px; text-transform: uppercase;">Active Learning Curriculum</span>
                    <h4 style="margin: 0.2rem 0 0.1rem 0; color: #1e293b; font-size: 1.15rem; font-weight: 700;">{first_mod_title} & modules</h4>
                    <p style="margin: 0; color: #64748b; font-size: 0.88rem;">{total_mods} structured modules &bull; {pacing_mode} pacing mode active</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c_banner_btn:
            if st.button("Resume Roadmap ➔", type="primary", use_container_width=True, key="btn_resume_banner"):
                st.switch_page("pages/2_🗺️_Roadmap.py")


# ========================================
# PROCESSED INPUT BANNER (IF INPUT EXISTS)
# ========================================
has_input = bool(st.session_state.get('current_input_id'))

if has_input and not active_roadmap:
    input_data = st.session_state.get('input_data', {})
    detected_type = input_data.get('detected_type', 'Unknown').replace('_', ' ').title()
    text_len = input_data.get('extracted_text_length', 0)
    filename = input_data.get('original_filename') or "Direct Text Input"

    with st.container(border=True):
        st.markdown(f"### Document Ready: **{filename}**")
        st.caption("Content validated and extracted into normalized text.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Detected Type", detected_type)
        with c2:
            st.metric("Text Length", f"{text_len:,} characters")
        with c3:
            st.metric("Source Format", "Uploaded File" if input_data.get('original_filename') else "Text Input")

        st.markdown("")
        col_act1, col_act2 = st.columns([2, 1], gap="medium")
        with col_act1:
            if st.button("Proceed to Roadmap", type="primary", use_container_width=True, key="btn_proceed_roadmap"):
                st.switch_page("pages/2_🗺️_Roadmap.py")
        with col_act2:
            if st.button("Replace with New Content", use_container_width=True, key="btn_replace_input"):
                st.session_state.current_input_id = None
                st.session_state.input_data = None
                st.rerun()

    st.markdown("---")
    st.caption("To update or submit different content, use the options below.")


# ========================================
# TAB-BASED INPUT METHODS (ALWAYS OPEN)
# ========================================
tab_file, tab_text = st.tabs(["Upload Document File", "Direct Text Input"])

# -------- TAB 1: FILE UPLOAD --------
with tab_file:
    with st.container(border=True):
        st.markdown("#### Upload Syllabus Document")
        st.caption(f"Supported formats: {', '.join(config.SUPPORTED_FORMATS).upper()} | Maximum size: {config.MAX_FILE_SIZE_MB}MB")

        uploaded_file = st.file_uploader(
            "Select document file",
            type=config.SUPPORTED_FORMATS,
            help="Upload your course syllabus or question bank file",
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.metric("Filename", uploaded_file.name)
            with col_f2:
                st.metric("Size", format_file_size(uploaded_file.size))

            is_valid, message = validate_file_upload(uploaded_file)
            if not is_valid:
                show_error("Invalid file", message)
            else:
                if st.button("Process Uploaded File", type="primary", use_container_width=True, key="btn_upload_process"):
                    file_bytes = uploaded_file.getvalue()
                    if active_roadmap:
                        confirm_replace_dialog(
                            action_type="file",
                            action_data={"file_bytes": file_bytes, "filename": uploaded_file.name}
                        )
                    else:
                        _execute_file_upload(file_bytes, uploaded_file.name)

# -------- TAB 2: TEXT INPUT --------
with tab_text:
    with st.container(border=True):
        st.markdown("#### Paste Course Text")
        st.caption("Paste course syllabus or lecture notes text directly")

        input_type_options = ["Auto-detect", "Syllabus", "Question Bank", "Mixed"]
        input_type_hint = st.pills(
            "Content type hint:",
            options=input_type_options,
            default="Auto-detect",
            help="Guide the system in recognizing the nature of your input"
        )

        input_type_map = {
            "Auto-detect": None,
            "Syllabus": "syllabus",
            "Question Bank": "question_bank",
            "Mixed": "mixed"
        }

        # Safe pre-seeding of session state to avoid Streamlit state mutation exceptions
        if "raw_input_text" not in st.session_state:
            st.session_state.raw_input_text = ""

        text_content = st.text_area(
            "Content text:",
            key="raw_input_text",
            height=240,
            placeholder="Paste syllabus modules, lecture notes, or question lists here...\n(Min: 10 chars, Max: 10,000 chars)",
            label_visibility="collapsed"
        )

        if text_content:
            char_count = len(text_content.strip())
            st.caption(f"Character count: {char_count:,}")

        if st.button("Process Text Input", type="primary", use_container_width=True, key="btn_text_process"):
            is_valid, message = validate_text_input(text_content)
            if not is_valid:
                show_error("Invalid text input", message)
            else:
                hint = input_type_map.get(input_type_hint)
                if active_roadmap:
                    confirm_replace_dialog(
                        action_type="text",
                        action_data={"content": text_content, "hint": hint}
                    )
                else:
                    _execute_text_submission(text_content, hint)


# ========================================
# STANDARDIZED BOTTOM NAVIGATION DECK
# ========================================
render_bottom_nav(
    prev_label="Home Overview",
    prev_page="app.py",
    next_label="Proceed to Roadmap",
    next_page="pages/2_🗺️_Roadmap.py",
    next_disabled=not bool(st.session_state.get('current_input_id') or active_roadmap)
)
