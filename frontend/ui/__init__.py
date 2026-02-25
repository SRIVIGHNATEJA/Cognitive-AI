"""
UI components package for Cognitive AI Learning Platform.

This package contains reusable UI components that are used across
multiple pages in the application.
"""

import importlib
from . import sidebar
importlib.reload(sidebar)
from .sidebar import render_sidebar

__all__ = ['render_sidebar']
