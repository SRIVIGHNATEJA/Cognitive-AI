"""
Roadmap page - Generate and view learning roadmap.

Allows users to generate a personalized learning roadmap from their input
and view the modules in their learning path.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from services.roadmap_service import roadmap_service
from utils.formatters import format_hours
from components.loading_spinner import with_loading
from components.error_display import (
    show_error, show_success, show_info, show_warning,
    handle_api_error, display_session_messages
)

# Page configuration
st.set_page_config(
    page_title="Roadmap",
    page_icon="🗺️",
    layout=config.LAYOUT
)

st.title("🗺️ Learning Roadmap")

st.markdown("""
Generate your personalized learning roadmap based on your input. Choose between
timed or untimed learning modes.
""")

# Display any session messages
display_session_messages()

# Check if input exists
if not st.session_state.get('current_input_id'):
    show_warning("No input found. Please go to the **Input** page and upload a file or enter text first.")
    st.stop()

# Check if roadmap already exists
has_roadmap = st.session_state.get('roadmap') is not None

# Roadmap Generation Section
if not has_roadmap:
    st.subheader("Generate Roadmap")
    
    st.info(f"""
    **Current Input ID:** `{st.session_state.current_input_id[:20]}...`  
    
    Choose your learning mode and generate your personalized roadmap.
    """)
    
    # Mode selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🕐 Timed Mode")
        st.markdown("""
        - Fixed time limits for each module
        - Structured learning schedule
        - Recommended for exam preparation
        - Includes time-based quizzes
        """)
    
    with col2:
        st.markdown("### ♾️ Untimed Mode")
        st.markdown("""
        - Learn at your own pace
        - No time pressure
        - Flexible schedule
        - Focus on understanding
        """)
    
    st.divider()
    
    # Mode selector
    mode = st.radio(
        "Select learning mode:",
        ["Untimed", "Timed"],
        horizontal=True,
        help="Choose how you want to learn"
    )
    
    # Map display name to API value
    mode_value = mode.lower()
    
    # Generate button
    if st.button("🚀 Generate Roadmap", type="primary", use_container_width=True):
        
        def generate():
            """Generate roadmap from backend."""
            return roadmap_service.generate_roadmap(
                st.session_state.current_input_id,
                mode_value
            )
        
        # Execute with loading indicator
        try:
            result = with_loading(
                generate,
                loading_message="Generating your personalized roadmap...",
                info_message="⏳ This may take up to 30 seconds. Please wait..."
            )
            
            if result:
                # Update session state
                st.session_state.roadmap = result
                st.session_state.roadmap_mode = result.get('mode')
                
                # Show success
                show_success(f"Roadmap generated successfully! {result.get('total_modules', 0)} modules created.")
                
                # Rerun to show roadmap
                st.rerun()
                
        except Exception as e:
            handle_api_error(e, "Roadmap generation")

# Display Roadmap Section
else:
    roadmap = st.session_state.roadmap
    mode = roadmap.get('mode', 'unknown')
    
    # Roadmap header
    # In untimed mode, hide time information
    if mode == 'untimed':
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("Your Learning Path")
        
        with col2:
            mode_display = mode.title()
            st.metric("Mode", mode_display)
    else:
        # Timed mode: show all metrics including time
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader("Your Learning Path")
        
        with col2:
            mode_display = mode.title()
            st.metric("Mode", mode_display)
        
        with col3:
            total_hours = roadmap.get('total_estimated_hours', 0)
            st.metric("Total Time", format_hours(total_hours))
    
    # Roadmap info
    total_modules = roadmap.get('total_modules', 0)
    cached = roadmap.get('cached', False)
    
    if cached:
        st.info(f"📋 Showing cached roadmap with {total_modules} modules")
    else:
        st.success(f"✨ Fresh roadmap with {total_modules} modules")
    
    st.divider()
    
    # Modules display
    modules = roadmap.get('modules', [])
    
    if not modules:
        show_warning("No modules found in roadmap.")
    else:
        st.subheader(f"Modules ({len(modules)})")
        
        # Build module_id -> topic_name mapping for prerequisite display
        module_id_to_name = {
            module.get('module_id'): module.get('topic_name', 'Unknown')
            for module in modules
        }
        
        # Display modules as cards
        for module in modules:
            module_id = module.get('module_id', 'unknown')
            topic_name = module.get('topic_name', 'Untitled Module')
            estimated_hours = module.get('estimated_hours', 0)
            prerequisites = module.get('prerequisites', [])
            order = module.get('order', 0)
            
            # Create expandable card for each module
            with st.expander(f"**{order}. {topic_name}**", expanded=False):
                # In untimed mode, don't show time metric
                if mode == 'untimed':
                    st.write(f"**Module ID:** `{module_id}`")
                    
                    if prerequisites:
                        prereq_count = len(prerequisites)
                        st.write(f"**Prerequisites:** {prereq_count} module(s)")
                        with st.expander("View Prerequisites"):
                            for prereq_id in prerequisites:
                                # Map prerequisite ID to name, fallback to ID if not found
                                prereq_name = module_id_to_name.get(prereq_id, prereq_id)
                                st.text(f"• {prereq_name}")
                    else:
                        st.write("**Prerequisites:** None")
                else:
                    # Timed mode: show time metric
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Module ID:** `{module_id}`")
                        
                        if prerequisites:
                            prereq_count = len(prerequisites)
                            st.write(f"**Prerequisites:** {prereq_count} module(s)")
                            with st.expander("View Prerequisites"):
                                for prereq_id in prerequisites:
                                    # Map prerequisite ID to name, fallback to ID if not found
                                    prereq_name = module_id_to_name.get(prereq_id, prereq_id)
                                    st.text(f"• {prereq_name}")
                        else:
                            st.write("**Prerequisites:** None")
                    
                    with col2:
                        st.metric("Time", format_hours(estimated_hours))
                
                # Action buttons
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if st.button(
                        "📚 View Content",
                        key=f"content_{module_id}",
                        use_container_width=True
                    ):
                        # Set current module and navigate to content page
                        st.session_state.current_module_id = module_id
                        st.session_state.current_module = module
                        st.switch_page("pages/3_📚_Content.py")
                
                with col_b:
                    if st.button(
                        "📝 Take Quiz",
                        key=f"quiz_{module_id}",
                        use_container_width=True
                    ):
                        # Set current module and navigate to quiz page
                        st.session_state.current_module_id = module_id
                        st.session_state.current_module = module
                        st.info("Go to the **Quiz** page to test your knowledge.")
    
    st.divider()
    
    # Roadmap actions
    st.subheader("Roadmap Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Refresh roadmap
        if st.button("🔄 Refresh Roadmap", use_container_width=True):
            try:
                with st.spinner("Fetching roadmap..."):
                    result = roadmap_service.get_roadmap()
                    
                    # Update session state
                    st.session_state.roadmap = result
                    st.session_state.roadmap_mode = result.get('mode')
                    
                    show_success("Roadmap refreshed")
                    st.rerun()
                    
            except Exception as e:
                handle_api_error(e, "Roadmap refresh")
    
    with col2:
        # Reset roadmap (with confirmation)
        if st.button("🗑️ Reset Roadmap", use_container_width=True, type="secondary"):
            st.session_state.confirm_reset = True
    
    # Confirmation dialog for reset
    if st.session_state.get('confirm_reset', False):
        st.warning("⚠️ Are you sure you want to reset the roadmap? This action cannot be undone.")
        
        col_yes, col_no = st.columns(2)
        
        with col_yes:
            if st.button("✅ Yes, Reset", type="primary", use_container_width=True):
                try:
                    with st.spinner("Resetting roadmap..."):
                        roadmap_service.delete_roadmap()
                        
                        # Clear session state
                        st.session_state.roadmap = None
                        st.session_state.roadmap_mode = None
                        st.session_state.current_module_id = None
                        st.session_state.current_module = None
                        st.session_state.confirm_reset = False
                        
                        show_success("Roadmap reset successfully")
                        st.rerun()
                        
                except Exception as e:
                    handle_api_error(e, "Roadmap reset")
                    st.session_state.confirm_reset = False
        
        with col_no:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()

# Help section
st.divider()

with st.expander("ℹ️ Help"):
    st.markdown("""
    ### How to use this page
    
    **If you don't have a roadmap yet:**
    1. Choose your learning mode (Timed or Untimed)
    2. Click "Generate Roadmap"
    3. Wait for the AI to create your personalized path
    4. View your modules below
    
    **If you already have a roadmap:**
    1. Browse your modules
    2. Click "View Content" to see notes and cheat sheets
    3. Click "Take Quiz" to test your knowledge
    4. Use "Refresh" to reload from backend
    5. Use "Reset" to start over (requires confirmation)
    
    ### Learning Modes
    
    **Timed Mode:**
    - Best for exam preparation
    - Fixed time limits per module
    - Structured schedule
    - Time-based quizzes
    
    **Untimed Mode:**
    - Best for self-paced learning
    - No time pressure
    - Flexible schedule
    - Focus on understanding
    
    ### Module Information
    
    Each module shows:
    - **Topic Name**: What you'll learn
    - **Estimated Hours**: Time to complete
    - **Prerequisites**: Required prior modules
    - **Order**: Sequence in learning path
    
    ### Next Steps
    
    After viewing your roadmap:
    1. Go to **Content** page to study
    2. Go to **Quiz** page to test yourself
    3. Go to **Analytics** page to track progress
    4. Go to **Doubt** page to ask questions
    """)
