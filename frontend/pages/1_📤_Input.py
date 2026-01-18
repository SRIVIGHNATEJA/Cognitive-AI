"""
Input page - Upload files or enter text.

Allows users to provide educational content (syllabus or question bank)
via file upload or direct text input.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from services.input_service import input_service
from utils.validators import validate_file_upload, validate_text_input
from utils.formatters import format_file_size
from components.loading_spinner import with_loading
from components.error_display import (
    show_error, show_success, show_info, show_warning,
    handle_api_error, display_session_messages
)

# Page configuration
st.set_page_config(
    page_title="Input",
    page_icon="📤",
    layout=config.LAYOUT
)

st.title("📤 Input")
st.caption("Upload your syllabus or question bank to get started")

st.divider()

# Display any session messages
display_session_messages()

# Input method selection
st.markdown("### Choose Input Method")
input_method = st.radio(
    "Select how you want to provide your content:",
    ["📁 Upload File", "📝 Enter Text"],
    horizontal=True,
    label_visibility="collapsed"
)

st.divider()

# File Upload Section
if input_method == "📁 Upload File":
    st.markdown("### 📁 Upload File")
    
    st.info(f"""
    **Supported formats:** {', '.join(config.SUPPORTED_FORMATS)}  
    **Maximum size:** {config.MAX_FILE_SIZE_MB}MB
    """)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=config.SUPPORTED_FORMATS,
        help="Upload your syllabus or question bank"
    )
    
    if uploaded_file is not None:
        # Display file info
        file_size = format_file_size(uploaded_file.size)
        st.write(f"**File:** {uploaded_file.name}")
        st.write(f"**Size:** {file_size}")
        
        # Validate file
        is_valid, message = validate_file_upload(uploaded_file)
        
        if not is_valid:
            show_error("Invalid file", message)
        else:
            # Upload button
            if st.button("🚀 Upload and Process", type="primary", use_container_width=True):
                
                def upload_file():
                    """Upload file to backend."""
                    # Read file data
                    file_data = uploaded_file.read()
                    
                    # Upload to backend
                    response = input_service.upload_file(file_data, uploaded_file.name)
                    
                    return response
                
                # Execute with loading indicator
                try:
                    result = with_loading(
                        upload_file,
                        loading_message="Uploading and processing file...",
                        info_message="⏳ This may take up to 30 seconds. Please wait..."
                    )
                    
                    if result:
                        # Update session state
                        st.session_state.current_input_id = result.get('input_id')
                        st.session_state.input_data = {
                            'input_id': result.get('input_id'),
                            'detected_type': result.get('detected_type'),
                            'extracted_text_length': result.get('extracted_text_length'),
                            'original_filename': result.get('original_filename')
                        }
                        
                        # Show success
                        show_success(f"✅ File processed successfully!")
                        
                        # Display processing results
                        st.divider()
                        st.markdown("### Processing Results")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Detected Type", result.get('detected_type', 'Unknown').replace('_', ' ').title())
                        with col2:
                            st.metric("Text Length", f"{result.get('extracted_text_length', 0):,} chars")
                        
                        st.info("✅ Ready to continue! Go to the **Roadmap** page to generate your learning path.")
                        
                except Exception as e:
                    handle_api_error(e, "File upload")

# Text Input Section
else:
    st.markdown("### 📝 Enter Text")
    
    st.info("""
    Paste your syllabus or question bank content directly.  
    **Minimum:** 10 characters  
    **Maximum:** 10,000 characters
    """)
    
    # Input type hint
    input_type_hint = st.selectbox(
        "Content type (optional hint):",
        ["Auto-detect", "Syllabus", "Question Bank", "Mixed"],
        help="Help the system understand your content type"
    )
    
    # Map display names to API values
    input_type_map = {
        "Auto-detect": None,
        "Syllabus": "syllabus",
        "Question Bank": "question_bank",
        "Mixed": "mixed"
    }
    
    # Text area
    text_content = st.text_area(
        "Content:",
        height=300,
        placeholder="Paste your syllabus or question bank here...",
        help="Enter the educational content you want to learn"
    )
    
    # Character count
    if text_content:
        char_count = len(text_content.strip())
        st.caption(f"Characters: {char_count:,}")
    
    # Submit button
    if st.button("🚀 Submit and Process", type="primary", use_container_width=True):
        
        # Validate text
        is_valid, message = validate_text_input(text_content)
        
        if not is_valid:
            show_error("Invalid text input", message)
        else:
            def submit_text():
                """Submit text to backend."""
                input_type = input_type_map.get(input_type_hint)
                response = input_service.submit_text(text_content, input_type)
                return response
            
            # Execute with loading indicator
            try:
                result = with_loading(
                    submit_text,
                    loading_message="Processing text input...",
                    info_message="⏳ This may take up to 30 seconds. Please wait..."
                )
                
                if result:
                    # Update session state
                    st.session_state.current_input_id = result.get('input_id')
                    st.session_state.input_data = {
                        'input_id': result.get('input_id'),
                        'detected_type': result.get('detected_type'),
                        'extracted_text_length': result.get('extracted_text_length'),
                        'original_filename': None
                    }
                    
                    # Show success
                    show_success(f"✅ Text processed successfully!")
                    
                    # Display processing results
                    st.divider()
                    st.markdown("### Processing Results")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Detected Type", result.get('detected_type', 'Unknown').replace('_', ' ').title())
                    with col2:
                        st.metric("Text Length", f"{result.get('extracted_text_length', 0):,} chars")
                    
                    st.info("✅ Ready to continue! Go to the **Roadmap** page to generate your learning path.")
                    
            except Exception as e:
                handle_api_error(e, "Text submission")

# Display current input status
st.divider()

if st.session_state.get('current_input_id'):
    st.markdown("### Current Input Status")
    
    with st.expander("📋 View Input Details", expanded=False):
        input_data = st.session_state.get('input_data', {})
        
        st.write(f"**Input ID:** `{st.session_state.current_input_id}`")
        st.write(f"**Type:** {input_data.get('detected_type', 'Unknown').replace('_', ' ').title()}")
        st.write(f"**Text Length:** {input_data.get('extracted_text_length', 0):,} characters")
        
        if input_data.get('original_filename'):
            st.write(f"**Original File:** {input_data.get('original_filename')}")
        
        # Refresh button
        if st.button("🔄 Refresh Input Status"):
            try:
                with st.spinner("Fetching input status..."):
                    status = input_service.get_input_status(st.session_state.current_input_id)
                    
                    # Update session state
                    st.session_state.input_data = {
                        'input_id': status.get('input_id'),
                        'detected_type': status.get('detected_type'),
                        'extracted_text_length': len(status.get('extracted_text', '')),
                        'original_filename': status.get('original_filename')
                    }
                    
                    show_success("Input status refreshed")
                    st.rerun()
                    
            except Exception as e:
                handle_api_error(e, "Status refresh")
else:
    st.info("No input has been processed yet. Upload a file or enter text above to get started.")

# Help section
st.divider()

with st.expander("ℹ️ Help"):
    st.markdown("""
    ### How to use this page
    
    1. **Choose your input method:**
       - Upload a file (PDF, PPT, DOCX)
       - Or paste text directly
    
    2. **Provide your content:**
       - Syllabus: Course outline, topics, schedule
       - Question Bank: Practice questions, past papers
       - Mixed: Combination of both
    
    3. **Process your input:**
       - Click the upload/submit button
       - Wait for processing (may take up to 30 seconds)
       - View the detected type and extracted text length
    
    4. **Next steps:**
       - Go to the **Roadmap** page
       - Generate your personalized learning path
       - Start learning!
    
    ### Tips
    
    - Larger files may take longer to process
    - Text input is faster than file upload
    - The system auto-detects content type
    - You can provide a hint to improve detection
    """)
