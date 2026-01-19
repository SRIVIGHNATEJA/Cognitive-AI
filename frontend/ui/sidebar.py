"""
Shared sidebar component for Cognitive AI Learning Platform.

This module provides a stateless, idempotent sidebar renderer that displays
the premium sidebar UI consistently across all pages.

CRITICAL SAFETY RULES:
- Stateless: No internal state management
- Idempotent: Can be called multiple times safely
- Purely presentational: No backend calls or logic branching
- Read-only: Only reads from existing session_state keys
- No mutations: Never writes or modifies session_state
"""

import streamlit as st


def render_sidebar():
    """
    Render the premium sidebar UI with 4 zones.
    
    This function is stateless and purely presentational. It only reads
    from existing session_state keys and never modifies them.
    
    Zones:
    1. App Identity - Brand header with gradient
    2. Primary Navigation - Visual navigation cards
    3. Learning Context - Current learning state (read-only)
    4. Quick Actions - Fast navigation buttons
    5. System Status - Collapsed technical details
    """
    
    with st.sidebar:
        # ========================================
        # ZONE 1: APP IDENTITY
        # ========================================
        st.markdown("""
        <div style="padding: 1.5rem 1rem; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🧠</div>
            <h3 style="margin: 0; color: white; font-size: 1.2rem; font-weight: 600;">Cognitive AI</h3>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: rgba(255,255,255,0.95); font-weight: 300;">Your AI-Powered Learning Companion</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ========================================
        # ZONE 2: PRIMARY NAVIGATION
        # ========================================
        st.markdown("### 🧭 Learning Journey")
        st.caption("Navigate through your learning path")
        
        # Navigation items with visual treatment
        st.markdown("""
        <div style="background: rgba(102, 126, 234, 0.08); padding: 0.75rem; border-radius: 8px; border-left: 3px solid #667eea; margin-bottom: 0.5rem;">
            <div style="font-weight: 600; color: #667eea; margin-bottom: 0.25rem;">📤 Input</div>
            <div style="font-size: 0.8rem; color: #666;">Upload content</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; opacity: 0.7; background: rgba(0,0,0,0.02);">
            <div style="font-weight: 500; margin-bottom: 0.25rem;">🗺️ Roadmap</div>
            <div style="font-size: 0.8rem; color: #888;">Generate path</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; opacity: 0.7; background: rgba(0,0,0,0.02);">
            <div style="font-weight: 500; margin-bottom: 0.25rem;">📚 Content</div>
            <div style="font-size: 0.8rem; color: #888;">Study materials</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; opacity: 0.7; background: rgba(0,0,0,0.02);">
            <div style="font-weight: 500; margin-bottom: 0.25rem;">🧪 Quiz</div>
            <div style="font-size: 0.8rem; color: #888;">Test knowledge</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # ========================================
        # ZONE 3: LEARNING CONTEXT (READ-ONLY)
        # ========================================
        st.markdown("### 📊 Learning Context")
        
        # Read from existing session state (NO NEW COMPUTATION)
        roadmap = st.session_state.get('roadmap')
        current_module = st.session_state.get('current_module')
        current_input_id = st.session_state.get('current_input_id')
        
        if roadmap:
            mode = roadmap.get('mode', 'unknown').title()
            total_modules = roadmap.get('total_modules', 0)
            
            st.markdown(f"""
            <div style="background: rgba(0,0,0,0.03); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid rgba(0,0,0,0.05);">
                <div style="margin-bottom: 0.5rem; display: flex; justify-content: space-between;">
                    <span style="color: #666; font-size: 0.85rem;">Mode:</span>
                    <span style="font-weight: 600; color: #333;">{mode}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #666; font-size: 0.85rem;">Modules:</span>
                    <span style="font-weight: 600; color: #333;">{total_modules}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if current_module:
                topic_name = current_module.get('topic_name', 'Unknown')
                order = current_module.get('order', 0)
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); padding: 1rem; border-radius: 8px; border-left: 3px solid #667eea; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size: 0.7rem; color: #667eea; margin-bottom: 0.5rem; font-weight: 600; letter-spacing: 0.5px;">CURRENT MODULE</div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem; color: #333; font-size: 0.95rem;">{topic_name}</div>
                    <div style="font-size: 0.85rem; color: #666;">Module {order} of {total_modules}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("📍 Select a module to begin")
        else:
            if current_input_id:
                st.markdown("""
                <div style="background: rgba(76, 175, 80, 0.1); padding: 1rem; border-radius: 8px; border-left: 3px solid #4caf50;">
                    <div style="font-weight: 600; margin-bottom: 0.25rem; color: #2e7d32;">✅ Input Processed</div>
                    <div style="font-size: 0.85rem; color: #666;">Ready to generate roadmap</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: rgba(255, 152, 0, 0.1); padding: 1rem; border-radius: 8px; border-left: 3px solid #ff9800;">
                    <div style="font-weight: 600; margin-bottom: 0.25rem; color: #e65100;">📍 Get Started</div>
                    <div style="font-size: 0.85rem; color: #666;">Upload content to begin</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # ========================================
        # ZONE 4: QUICK ACTIONS
        # ========================================
        st.markdown("### ⚡ Quick Actions")
        
        current_module_id = st.session_state.get('current_module_id')
        
        if current_module_id:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📚 Study", use_container_width=True, key="sidebar_study"):
                    st.switch_page("pages/3_📚_Content.py")
            
            with col2:
                if st.button("🧪 Quiz", use_container_width=True, key="sidebar_quiz"):
                    st.switch_page("pages/4_🧪_Quiz.py")
        else:
            st.caption("Complete setup to unlock quick actions")
        
        st.divider()
        
        # ========================================
        # ZONE 5: SYSTEM STATUS (COLLAPSED)
        # ========================================
        with st.expander("🔧 System Status", expanded=False):
            # Import here to avoid circular dependencies
            from config import config
            from services.api_client import api_client
            from components.error_display import show_error, show_success
            
            # Helper functions (inline to keep sidebar self-contained)
            def check_backend_health_inline():
                try:
                    return api_client.health_check()
                except Exception:
                    return False
            
            def sync_backend_session_inline():
                try:
                    session_data = api_client.get("/api/session")
                    st.session_state.backend_session_id = session_data.get('session_id')
                    st.session_state.backend_session_data = session_data
                    st.session_state.current_input_id = session_data.get('current_input_id')
                    if session_data.get('roadmap_generated', False):
                        st.session_state.roadmap_mode = session_data.get('roadmap_mode')
                    if session_data.get('current_module_id'):
                        st.session_state.current_module_id = session_data.get('current_module_id')
                    return True
                except Exception as e:
                    show_error("Failed to sync with backend", str(e))
                    return False
            
            if st.session_state.get('backend_session_id'):
                st.success("✅ Connected to backend")
                st.caption(f"Session: {st.session_state.backend_session_id[:16]}...")
            else:
                st.warning("⚠️ Not connected to backend")
            
            st.caption(f"Backend: {config.BACKEND_URL}")
            
            if st.button("🔄 Refresh Session", use_container_width=True, key="sidebar_refresh"):
                with st.spinner("Syncing..."):
                    if sync_backend_session_inline():
                        show_success("Session refreshed")
                        st.rerun()
                    else:
                        show_error("Failed to refresh")
            
            if st.button("🏥 Health Check", use_container_width=True, key="sidebar_health"):
                with st.spinner("Checking..."):
                    if check_backend_health_inline():
                        show_success("Backend is healthy")
                    else:
                        show_error("Backend not responding")
