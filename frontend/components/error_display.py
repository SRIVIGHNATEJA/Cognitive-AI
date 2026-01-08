"""
Error display component.

Provides consistent error message display across the app.
"""

import streamlit as st
from typing import Optional


def show_error(message: str, details: Optional[str] = None):
    """
    Display error message.
    
    Args:
        message: Error message
        details: Optional error details
    """
    st.error(f"❌ {message}")
    
    if details:
        with st.expander("Error Details"):
            st.code(details)


def show_warning(message: str):
    """
    Display warning message.
    
    Args:
        message: Warning message
    """
    st.warning(f"⚠️ {message}")


def show_success(message: str):
    """
    Display success message.
    
    Args:
        message: Success message
    """
    st.success(f"✅ {message}")


def show_info(message: str):
    """
    Display info message.
    
    Args:
        message: Info message
    """
    st.info(f"ℹ️ {message}")


def handle_api_error(error: Exception, context: str = "Operation"):
    """
    Handle and display API errors consistently.
    
    Args:
        error: Exception that occurred
        context: Context of the operation (e.g., "File upload")
    """
    error_msg = str(error)
    
    # Check for specific error types
    if "timeout" in error_msg.lower():
        show_error(
            f"{context} timed out",
            "The operation took too long. Please try again or check your connection."
        )
    elif "connection" in error_msg.lower():
        show_error(
            f"Cannot connect to backend",
            "Please ensure the backend server is running at the configured URL."
        )
    elif "404" in error_msg:
        show_error(
            f"{context} failed",
            "The requested resource was not found."
        )
    elif "500" in error_msg:
        show_error(
            f"{context} failed",
            "The server encountered an error. Please try again later."
        )
    else:
        show_error(f"{context} failed", error_msg)


def clear_messages():
    """Clear all message state."""
    st.session_state.error_message = None
    st.session_state.success_message = None


def display_session_messages():
    """Display messages stored in session state."""
    if st.session_state.get('error_message'):
        show_error(st.session_state.error_message)
        st.session_state.error_message = None
    
    if st.session_state.get('success_message'):
        show_success(st.session_state.success_message)
        st.session_state.success_message = None
