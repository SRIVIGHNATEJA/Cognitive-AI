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

# Card-based input method selection
st.markdown("### Choose Input Method")
st.caption("Select how you want to provide your educational content")

# Initialize input method in session state if not exists
if 'input_method' not in st.session_state:
    st.session_state.input_method = None

col1, col2 = st.columns(2, gap="large")

with col1:
    with st.container():
        st.markdown("#### 📁 Upload File")
        st.caption("PDF, PPT, DOCX supported")
        st.markdown("""
        **Best for:**
        - Existing documents
        - Formatted content
        - Large syllabi
        """)
        if st.button("Choose File Upload", key="select_file", use_container_width=True, type="primary" if st.session_state.input_method == "file" else "secondary"):
            st.session_state.input_method = "file"
            st.rerun()

with col2:
    with st.container():
        st.markdown("#### 📝 Enter Text")
        st.caption("Paste content directly")
        st.markdown("""
        **Best for:**
        - Quick input
        - Copy-paste content
        - Short syllabi
        """)
        if st.button("Choose Text Input", key="select_text", use_container_width=True, type="primary" if st.session_state.input_method == "text" else "secondary"):
            st.session_state.input_method = "text"
            st.rerun()

st.divider()

# Determine which method to show
if st.session_state.input_method == "file":
    input_method = "📁 Upload File"
elif st.session_state.input_method == "text":
    input_method = "📝 Enter Text"
else:
    # No method selected yet
    st.info("👆 Please select an input method above to get started")
    st.stop()

# File Upload Section
if input_method == "📁 Upload File":
    with st.container():
        st.markdown("### 📁 Upload Your File")
        st.caption(f"Supported: {', '.join(config.SUPPORTED_FORMATS)} • Max size: {config.MAX_FILE_SIZE_MB}MB")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=config.SUPPORTED_FORMATS,
            help="Upload your syllabus or question bank"
        )
        
        if uploaded_file is not None:
            # Display file info in a contained card
            with st.container():
                col_file1, col_file2 = st.columns(2)
                with col_file1:
                    st.metric("File Name", uploaded_file.name)
                with col_file2:
                    file_size = format_file_size(uploaded_file.size)
                    st.metric("File Size", file_size)
            
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
                            
                            # Display processing results in a card
                            st.divider()
                            with st.container():
                                st.markdown("### ✅ Processing Complete")
                                st.caption("Your content has been analyzed and is ready for learning")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Detected Type", result.get('detected_type', 'Unknown').replace('_', ' ').title())
                                with col2:
                                    st.metric("Text Length", f"{result.get('extracted_text_length', 0):,} chars")
                                
                                st.success("🎯 **Next Step:** Go to the **Roadmap** page to generate your personalized learning path")
                            
                    except Exception as e:
                        handle_api_error(e, "File upload")

# Text Input Section
else:
    with st.container():
        st.markdown("### 📝 Enter Your Text")
        st.caption("Paste your syllabus or question bank content directly")
        
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
            placeholder="Paste your syllabus or question bank here...\n\nMinimum: 10 characters\nMaximum: 10,000 characters",
            help="Enter the educational content you want to learn"
        )
        
        # Character count
        if text_content:
            char_count = len(text_content.strip())
            col_char1, col_char2 = st.columns([3, 1])
            with col_char2:
                st.caption(f"**{char_count:,}** characters")
        
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
                        
                        # Display processing results in a card
                        st.divider()
                        with st.container():
                            st.markdown("### ✅ Processing Complete")
                            st.caption("Your content has been analyzed and is ready for learning")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Detected Type", result.get('detected_type', 'Unknown').replace('_', ' ').title())
                            with col2:
                                st.metric("Text Length", f"{result.get('extracted_text_length', 0):,} chars")
                            
                            st.success("🎯 **Next Step:** Go to the **Roadmap** page to generate your personalized learning path")
                        
                except Exception as e:
                    handle_api_error(e, "Text submission")

# Display current input status
st.divider()

with st.container():
    st.markdown("### 📊 Current Input Status")
    
    if st.session_state.get('current_input_id'):
        input_data = st.session_state.get('input_data', {})
        
        col_status1, col_status2, col_status3 = st.columns(3)
        with col_status1:
            st.metric("Type", input_data.get('detected_type', 'Unknown').replace('_', ' ').title())
        with col_status2:
            st.metric("Text Length", f"{input_data.get('extracted_text_length', 0):,}")
        with col_status3:
            if input_data.get('original_filename'):
                st.metric("Source", "File")
            else:
                st.metric("Source", "Text")
        
        with st.expander("📋 View Full Details", expanded=False):
            st.write(f"**Input ID:** `{st.session_state.current_input_id}`")
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
        st.info("No input has been processed yet. Select an input method above to get started.")

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
