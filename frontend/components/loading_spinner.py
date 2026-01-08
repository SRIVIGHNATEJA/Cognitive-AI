"""
Loading spinner component.

Provides consistent loading indicators across the app.
"""

import streamlit as st
from typing import Optional, Callable, Any


def show_loading(message: str = "Loading..."):
    """
    Display a loading spinner with message.
    
    Args:
        message: Loading message to display
    """
    st.spinner(message)


def with_loading(
    func: Callable,
    loading_message: str = "Processing...",
    info_message: Optional[str] = None
) -> Any:
    """
    Execute function with loading indicator.
    
    Args:
        func: Function to execute
        loading_message: Message to show in spinner
        info_message: Optional info message to show below spinner
        
    Returns:
        Function result
        
    Raises:
        Exception: If function raises an exception
    """
    # Prevent duplicate calls
    if st.session_state.get('loading', False):
        st.warning("⏳ Please wait, operation in progress...")
        return None
    
    # Set loading state
    st.session_state.loading = True
    
    try:
        with st.spinner(loading_message):
            if info_message:
                st.info(info_message)
            
            result = func()
            
            # Clear loading state
            st.session_state.loading = False
            
            return result
    
    except Exception as e:
        # Clear loading state on error
        st.session_state.loading = False
        raise e


def show_llm_loading(message: str = "Generating with AI..."):
    """
    Display loading indicator for LLM operations.
    
    Shows special message about potential delays.
    
    Args:
        message: Loading message
    """
    with st.spinner(message):
        st.info("⏳ This may take up to 30 seconds. Please wait...")
