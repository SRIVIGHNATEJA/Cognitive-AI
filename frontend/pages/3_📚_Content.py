"""
Content page - View detailed notes and cheat sheets for modules.

Allows users to generate and view educational content for each module
in their learning roadmap.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from services.content_service import content_service
from utils.formatters import format_hours
from components.loading_spinner import with_loading
from components.error_display import (
    show_error, show_success, show_info, show_warning,
    handle_api_error, display_session_messages
)

# Page configuration
st.set_page_config(
    page_title="Content",
    page_icon="📚",
    layout=config.LAYOUT
)

st.title("📚 Module Content")

st.markdown("""
View detailed notes and cheat sheets for each module in your learning roadmap.
""")

# Display any session messages
display_session_messages()

# Check if roadmap exists
if not st.session_state.get('roadmap'):
    show_warning("No roadmap found. Please generate a roadmap first.")
    if st.button("Go to Roadmap Page", type="primary"):
        st.switch_page("pages/2_🗺️_Roadmap.py")
    st.stop()

# Get roadmap data
roadmap = st.session_state.roadmap
modules = roadmap.get('modules', [])
mode = roadmap.get('mode', 'unknown')

if not modules:
    show_error("No modules found in roadmap.")
    st.stop()

# Module selection
st.subheader("Select Module")

# Build module options for dropdown
module_options = {
    f"{m.get('order')}. {m.get('topic_name')}": m.get('module_id')
    for m in modules
}

# Pre-select current module if set
current_module_id = st.session_state.get('current_module_id')
default_index = 0

if current_module_id:
    # Find index of current module
    for idx, (label, mod_id) in enumerate(module_options.items()):
        if mod_id == current_module_id:
            default_index = idx
            break

# Module selector dropdown
selected_label = st.selectbox(
    "Choose a module:",
    options=list(module_options.keys()),
    index=default_index,
    help="Select a module to view its content"
)

selected_module_id = module_options[selected_label]

# Update session state if module changed
if selected_module_id != st.session_state.get('current_module_id'):
    st.session_state.current_module_id = selected_module_id
    # Find and store full module object
    for module in modules:
        if module.get('module_id') == selected_module_id:
            st.session_state.current_module = module
            break

# Get current module details
current_module = st.session_state.get('current_module', {})
topic_name = current_module.get('topic_name', 'Unknown')
estimated_hours = current_module.get('estimated_hours', 0)
order = current_module.get('order', 0)
prerequisites = current_module.get('prerequisites', [])

# Display module info
st.divider()

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown(f"### {order}. {topic_name}")
    
    if prerequisites:
        # Build module_id -> topic_name mapping
        module_id_to_name = {
            m.get('module_id'): m.get('topic_name', 'Unknown')
            for m in modules
        }
        prereq_names = [module_id_to_name.get(p, p) for p in prerequisites]
        st.caption(f"**Prerequisites:** {', '.join(prereq_names)}")
    else:
        st.caption("**Prerequisites:** None")

with col2:
    # Only show time in timed mode
    if mode != 'untimed':
        st.metric("Time", format_hours(estimated_hours))

st.divider()

# Initialize content cache in session state
if 'content_cache' not in st.session_state:
    st.session_state.content_cache = {}

if selected_module_id not in st.session_state.content_cache:
    st.session_state.content_cache[selected_module_id] = {
        'notes': None,
        'cheatsheet': None
    }

# Check if content exists to determine which tab to show
has_notes = st.session_state.content_cache[selected_module_id].get('notes') is not None
has_cheatsheet = st.session_state.content_cache[selected_module_id].get('cheatsheet') is not None

# Tab interface for Notes and Cheat Sheet
tab1, tab2 = st.tabs(["📝 Detailed Notes", "📄 Cheat Sheet"])

# Notes Tab
with tab1:
    st.subheader("Detailed Notes")
    
    # Check if notes are cached in session
    cached_notes = st.session_state.content_cache[selected_module_id].get('notes')
    
    if cached_notes:
        # Display cached notes
        if cached_notes.get('cached'):
            st.info("📋 Cached content (previously generated)")
        else:
            st.success("✨ Fresh content generated")
        
        # Render the content
        content_text = cached_notes.get('notes', '')
        if content_text:
            st.markdown(content_text)
        else:
            st.warning("Content is empty")
    
    else:
        # Try to fetch from backend
        try:
            with st.spinner("Checking for cached notes..."):
                backend_notes = content_service.get_notes(selected_module_id)
            
            if backend_notes:
                # Cache in session
                st.session_state.content_cache[selected_module_id]['notes'] = backend_notes
                st.info("📋 Cached content (previously generated)")
                content_text = backend_notes.get('notes', '')
                if content_text:
                    st.markdown(content_text)
                else:
                    st.warning("Content is empty")
            else:
                # No notes generated yet
                st.info("No notes generated yet for this module.")
                
                if st.button("🚀 Generate Notes", type="primary", use_container_width=True):
                    
                    def generate():
                        """Generate notes from backend."""
                        return content_service.generate_notes(selected_module_id)
                    
                    # Execute with loading indicator
                    try:
                        result = with_loading(
                            generate,
                            loading_message="Generating detailed notes...",
                            info_message="⏳ This may take up to 30 seconds. Please wait..."
                        )
                        
                        if result:
                            # Cache in session
                            st.session_state.content_cache[selected_module_id]['notes'] = result
                            
                            # Display success and content immediately (no rerun needed)
                            st.success("✨ Fresh content generated")
                            content_text = result.get('notes', '')
                            if content_text:
                                st.markdown(content_text)
                            else:
                                st.warning("Content is empty")
                            
                    except Exception as e:
                        handle_api_error(e, "Notes generation")
        
        except Exception as e:
            handle_api_error(e, "Notes retrieval")

# Cheat Sheet Tab
with tab2:
    st.subheader("Cheat Sheet")
    
    # Check if cheat sheet is cached in session
    cached_cheatsheet = st.session_state.content_cache[selected_module_id].get('cheatsheet')
    
    if cached_cheatsheet:
        # Display cached cheat sheet
        if cached_cheatsheet.get('cached'):
            st.info("📋 Cached content (previously generated)")
        else:
            st.success("✨ Fresh content generated")
        
        # Render the content
        content_text = cached_cheatsheet.get('cheat_sheet', '')
        if content_text:
            st.markdown(content_text)
        else:
            st.warning("Content is empty")
    
    else:
        # Try to fetch from backend
        try:
            with st.spinner("Checking for cached cheat sheet..."):
                backend_cheatsheet = content_service.get_cheatsheet(selected_module_id)
            
            if backend_cheatsheet:
                # Cache in session
                st.session_state.content_cache[selected_module_id]['cheatsheet'] = backend_cheatsheet
                st.info("📋 Cached content (previously generated)")
                content_text = backend_cheatsheet.get('cheat_sheet', '')
                if content_text:
                    st.markdown(content_text)
                else:
                    st.warning("Content is empty")
            else:
                # No cheat sheet generated yet
                st.info("No cheat sheet generated yet for this module.")
                
                if st.button("🚀 Generate Cheat Sheet", type="primary", use_container_width=True):
                    
                    def generate():
                        """Generate cheat sheet from backend."""
                        return content_service.generate_cheatsheet(selected_module_id)
                    
                    # Execute with loading indicator
                    try:
                        result = with_loading(
                            generate,
                            loading_message="Generating cheat sheet...",
                            info_message="⏳ This may take up to 30 seconds. Please wait..."
                        )
                        
                        if result:
                            # Cache in session
                            st.session_state.content_cache[selected_module_id]['cheatsheet'] = result
                            
                            # Display success and content immediately (no rerun needed)
                            st.success("✨ Fresh content generated")
                            content_text = result.get('cheat_sheet', '')
                            if content_text:
                                st.markdown(content_text)
                            else:
                                st.warning("Content is empty")
                            
                    except Exception as e:
                        handle_api_error(e, "Cheat sheet generation")
        
        except Exception as e:
            handle_api_error(e, "Cheat sheet retrieval")

# Navigation and action buttons
st.divider()

st.subheader("Actions")

col1, col2, col3 = st.columns(3)

with col1:
    # Previous module button
    current_index = order - 1  # order is 1-based
    is_first = current_index == 0
    
    if st.button("← Previous Module", disabled=is_first, use_container_width=True):
        if current_index > 0:
            prev_module = modules[current_index - 1]
            st.session_state.current_module_id = prev_module.get('module_id')
            st.session_state.current_module = prev_module
            st.rerun()

with col2:
    # Take Quiz button
    if st.button("📝 Take Quiz", type="primary", use_container_width=True):
        st.info("Go to the **Quiz** page to test your knowledge.")

with col3:
    # Next module button
    is_last = current_index == len(modules) - 1
    
    if st.button("Next Module →", disabled=is_last, use_container_width=True):
        if current_index < len(modules) - 1:
            next_module = modules[current_index + 1]
            st.session_state.current_module_id = next_module.get('module_id')
            st.session_state.current_module = next_module
            st.rerun()

# Help section
st.divider()

with st.expander("ℹ️ Help"):
    st.markdown("""
    ### How to use this page
    
    **Viewing Content:**
    1. Select a module from the dropdown
    2. Choose between "Detailed Notes" or "Cheat Sheet" tabs
    3. Click "Generate" button if content not yet created
    4. Wait for generation (up to 30 seconds)
    5. View the generated content
    
    **Navigation:**
    - Use "Previous Module" / "Next Module" to browse modules
    - Click "Take Quiz" to test your knowledge
    - Content is cached permanently after first generation
    
    ### Content Types
    
    **Detailed Notes:**
    - Comprehensive study material
    - In-depth explanations
    - Examples and use cases
    - Best for initial learning
    
    **Cheat Sheet:**
    - Quick reference guide
    - Key concepts and terms
    - Essential commands/formulas
    - Best for review and exam prep
    
    ### Cache Indicators
    
    - **✨ Fresh content** - Just generated
    - **📋 Cached content** - Previously generated (loads instantly)
    
    ### Tips
    
    - Generate both notes and cheat sheet for complete coverage
    - Review notes first, then use cheat sheet for quick reference
    - Content is generated once and cached permanently
    - Use Previous/Next to navigate through your learning path
    """)
