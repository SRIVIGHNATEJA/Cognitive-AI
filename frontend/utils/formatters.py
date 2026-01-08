"""
Data formatting utilities.

Provides functions for formatting data for display.
"""

from typing import Optional


def format_time(seconds: int) -> str:
    """
    Format seconds into MM:SS format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string (e.g., "05:30")
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def format_hours(hours: float) -> str:
    """
    Format hours for display.
    
    Args:
        hours: Hours as float
        
    Returns:
        Formatted hours string (e.g., "5.5 hours")
    """
    if hours == 1.0:
        return "1 hour"
    return f"{hours:.1f} hours"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage for display.
    
    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string (e.g., "85.5%")
    """
    return f"{value:.{decimals}f}%"


def format_score(score: int, total: int = 10) -> str:
    """
    Format quiz score for display.
    
    Args:
        score: Score achieved
        total: Total possible score
        
    Returns:
        Formatted score string (e.g., "8/10")
    """
    return f"{score}/{total}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size for display.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string (e.g., "2.5 MB")
    """
    size_mb = size_bytes / (1024 * 1024)
    
    if size_mb < 0.1:
        size_kb = size_bytes / 1024
        return f"{size_kb:.1f} KB"
    
    return f"{size_mb:.1f} MB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_module_name(module_name: str, max_length: Optional[int] = None) -> str:
    """
    Format module name for display.
    
    Args:
        module_name: Module name
        max_length: Optional maximum length
        
    Returns:
        Formatted module name
    """
    if max_length:
        return truncate_text(module_name, max_length)
    return module_name
