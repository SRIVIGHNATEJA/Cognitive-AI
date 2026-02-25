"""
Shared sidebar component for Cognitive AI Learning Platform.

Provides a world-class, human-centric Learning Cockpit navigation ribbon:
- Natural asymmetric vertical pacing (eliminates both box clutter and awkward gaps)
- Custom CSS: Modern SaaS menu pill styling with glowing violet active theme (no red!)
- Tier 1: Course Workspace (Dashboard, Document Ingestion, Curriculum Roadmap)
- Tier 2: Current Mission Cockpit (Integrated Module HUD, Milestone Meter, Action Deck)
- Tier 3: AI Study Buddy Widget (Instant one-click access to AI Doubt Clarification)
- Tier 4: Collapsed Diagnostic Tools & Status Footer
"""

import inspect
from pathlib import Path
from typing import Optional
import streamlit as st


def _detect_current_page() -> str:
    """Detect current Streamlit page filename from the call stack."""
    valid_pages = {
        "app.py",
        "1_📤_Input.py",
        "2_🗺️_Roadmap.py",
        "3_📚_Content.py",
        "4_🧪_Quiz.py",
    }
    for frame in inspect.stack():
        filename = Path(frame.filename).name
        if filename in valid_pages:
            return filename
    return "app.py"


@st.dialog("Reset Platform to Initial State?")
def _confirm_reset_dialog():
    """Modal confirmation dialog before executing a complete platform state reset."""
    st.markdown(
        """
        <div style="font-size: 0.95rem; color: #1e293b; line-height: 1.5; margin-bottom: 0.65rem;">
            Are you sure you want to reset the platform back to its <strong>initial state</strong>?
        </div>
        <div style="font-size: 0.82rem; color: #475569; background: #f8fafc; border-radius: 9px; border: 1px solid #e2e8f0; padding: 0.85rem; margin-bottom: 1.15rem; line-height: 1.55;">
            <strong style="color: #0f172a;">This action will permanently clear:</strong>
            <ul style="margin: 0.4rem 0 0 0; padding-left: 1.25rem;">
                <li>Active syllabus text and uploaded documents</li>
                <li>Curriculum roadmap and module structures</li>
                <li>Generated study notes, cheat sheets, and practice quizzes</li>
                <li>Quiz assessment attempts and performance analytics</li>
                <li>Cached learning sessions and progress</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        if st.button("🚨 Yes, Reset Everything", type="primary", use_container_width=True, key="dlg_btn_confirm_reset"):
            from utils.state_manager import reset_entire_platform
            reset_entire_platform()
            try:
                st.switch_page("app.py")
            except Exception:
                st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True, key="dlg_btn_cancel_reset"):
            st.rerun()


def render_sidebar(current_page: Optional[str] = None):
    """
    Render the pinnacle Learning Cockpit sidebar ribbon.
    
    Args:
        current_page: Optional page filename override. If None, auto-detected.
    """
    if current_page is None:
        current_page = _detect_current_page()

    with st.sidebar:
        # =====================================================================
        # CUSTOM CSS: Modern SaaS Menu Styling & Cohesive Palette
        # =====================================================================
        st.markdown(
            """
            <style>
            /* 1. Hide default Streamlit multi-page nav links */
            [data-testid="stSidebarNav"] {
                display: none !important;
            }

            /* 2. Natural sidebar container padding */
            [data-testid="stSidebar"] > div:first-child {
                padding: 0.65rem 0.85rem 1.25rem 0.85rem !important;
            }

            /* 3. Controlled natural rhythm between vertical elements */
            [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
                gap: 0.55rem !important;
            }

            [data-testid="stSidebar"] [data-testid="stElementContainer"] {
                margin-bottom: 0rem !important;
            }

            /* 4. Elegant menu button pill styling (Linear/Notion SaaS style) */
            [data-testid="stSidebar"] button {
                border-radius: 9px !important;
                font-size: 0.85rem !important;
                font-weight: 500 !important;
                padding: 0.45rem 0.85rem !important;
                min-height: 2.25rem !important;
                transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
                text-align: left !important;
                display: flex !important;
                justify-content: flex-start !important;
                align-items: center !important;
                letter-spacing: -0.1px !important;
            }

            /* 5. Inactive navigation pill: subtle, soft white surface */
            [data-testid="stSidebar"] button[kind="secondary"] {
                background: #ffffff !important;
                border: 1px solid rgba(226, 232, 240, 0.85) !important;
                color: #334155 !important;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
            }

            [data-testid="stSidebar"] button[kind="secondary"]:hover {
                background: rgba(99, 102, 241, 0.07) !important;
                border-color: rgba(99, 102, 241, 0.35) !important;
                color: #4f46e5 !important;
                transform: translateX(3px) !important;
            }

            /* 6. Active navigation pill: rich glowing violet gradient */
            [data-testid="stSidebar"] button[kind="primary"] {
                background: linear-gradient(135deg, #6366f1 0%, #7c3aed 60%, #8b5cf6 100%) !important;
                border: none !important;
                color: #ffffff !important;
                box-shadow: 0 3px 10px rgba(99, 102, 241, 0.35) !important;
                font-weight: 600 !important;
            }

            [data-testid="stSidebar"] button[kind="primary"]:hover {
                background: linear-gradient(135deg, #5558e6 0%, #6d28d9 60%, #7c3aed 100%) !important;
                box-shadow: 0 4px 14px rgba(99, 102, 241, 0.45) !important;
            }

            /* 7. Disabled navigation pill */
            [data-testid="stSidebar"] button:disabled {
                opacity: 0.42 !important;
                background: #f8fafc !important;
                border: 1px dashed #cbd5e1 !important;
                color: #94a3b8 !important;
                cursor: not-allowed !important;
                transform: none !important;
            }

            /* 8. Collapsed expander styling */
            [data-testid="stSidebar"] [data-testid="stExpander"] {
                border-radius: 9px !important;
                border: 1px solid rgba(226, 232, 240, 0.8) !important;
                background: #ffffff !important;
                margin-top: 0.35rem !important;
            }
            [data-testid="stSidebar"] [data-testid="stExpander"] summary {
                padding: 0.45rem 0.75rem !important;
                font-size: 0.8rem !important;
                color: #475569 !important;
            }

            /* 9. Global Primary & Form Submit Button Polish (Eliminates harsh coral-red everywhere!) */
            button[kind="primary"],
            button[kind="primaryFormSubmit"],
            [data-testid="stBaseButton-primary"],
            [data-testid="stBaseButton-primaryFormSubmit"],
            [data-testid="baseButton-primary"],
            [data-testid="baseButton-primaryFormSubmit"],
            .stButton > button[kind="primary"],
            .stButton > button[data-testid="stBaseButton-primary"],
            .stFormSubmitButton > button,
            .stFormSubmitButton > button[kind="primaryFormSubmit"] {
                background: linear-gradient(135deg, #6366f1 0%, #7c3aed 60%, #8b5cf6 100%) !important;
                background-color: #7c3aed !important;
                border: none !important;
                color: #ffffff !important;
                box-shadow: 0 3px 10px rgba(99, 102, 241, 0.3) !important;
            }
            button[kind="primary"]:hover,
            button[kind="primaryFormSubmit"]:hover,
            [data-testid="stBaseButton-primary"]:hover,
            [data-testid="stBaseButton-primaryFormSubmit"]:hover,
            [data-testid="baseButton-primary"]:hover,
            [data-testid="baseButton-primaryFormSubmit"]:hover,
            .stButton > button[kind="primary"]:hover,
            .stButton > button[data-testid="stBaseButton-primary"]:hover,
            .stFormSubmitButton > button:hover,
            .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {
                background: linear-gradient(135deg, #5558e6 0%, #6d28d9 60%, #7c3aed 100%) !important;
                background-color: #6d28d9 !important;
                box-shadow: 0 4px 14px rgba(99, 102, 241, 0.45) !important;
            }

            /* 10. Modern Segmented Capsule Tabs (Pinnacle SaaS styling) */
            [data-testid="stTabs"] [role="tablist"] {
                background: #f1f5f9 !important;
                border: 1px solid rgba(226, 232, 240, 0.95) !important;
                border-radius: 12px !important;
                padding: 4px !important;
                gap: 6px !important;
                margin-bottom: 1.25rem !important;
                border-bottom: none !important;
            }

            [data-testid="stTabs"] button[role="tab"] {
                border-radius: 9px !important;
                font-size: 0.9rem !important;
                font-weight: 500 !important;
                color: #64748b !important;
                padding: 0.55rem 1.15rem !important;
                border: none !important;
                background: transparent !important;
                transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
                border-bottom: none !important;
            }

            [data-testid="stTabs"] button[role="tab"]:hover {
                color: #1e293b !important;
                background: rgba(255, 255, 255, 0.65) !important;
                border-bottom: none !important;
            }

            /* Active Tab: Elevated crisp white capsule with violet typography & subtle glow */
            [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
                background: #ffffff !important;
                color: #4f46e5 !important;
                font-weight: 700 !important;
                border: 1px solid rgba(99, 102, 241, 0.25) !important;
                box-shadow: 0 3px 10px rgba(99, 102, 241, 0.12), 0 1px 3px rgba(0, 0, 0, 0.05) !important;
                border-bottom: none !important;
            }

            /* Eliminate Streamlit's default red bottom border indicator line completely */
            [data-testid="stTabs"] [role="tablist"] > div,
            [data-testid="stTabs"] button[role="tab"] div[data-testid="stMarkdownContainer"] {
                border-bottom: none !important;
            }

            /* 11. Modern Module Oval Pills Styling (st.pills / stButtonGroup) */
            [data-testid="stButtonGroup"],
            [data-baseweb="button-group"] {
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 0.45rem !important;
                border: none !important;
                background: transparent !important;
            }

            [data-testid="stButtonGroup"] button,
            [data-baseweb="button-group"] button {
                border-radius: 999px !important;
                font-size: 0.8rem !important;
                font-weight: 500 !important;
                padding: 0.35rem 0.95rem !important;
                min-height: 2rem !important;
                border: 1px solid rgba(226, 232, 240, 0.95) !important;
                background: #ffffff !important;
                color: #475569 !important;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
                transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
                margin: 0 !important;
            }

            [data-testid="stButtonGroup"] button:hover,
            [data-baseweb="button-group"] button:hover {
                border-color: rgba(99, 102, 241, 0.45) !important;
                color: #4338ca !important;
                background: rgba(99, 102, 241, 0.05) !important;
                transform: translateY(-1px) !important;
            }

            /* Active Selected Pill: Rich Violet-Indigo Gradient (NO RED!) */
            [data-testid="stButtonGroup"] button[aria-checked="true"],
            [data-baseweb="button-group"] button[aria-checked="true"] {
                background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%) !important;
                background-color: #7c3aed !important;
                color: #ffffff !important;
                border: 1px solid transparent !important;
                box-shadow: 0 3px 10px rgba(99, 102, 241, 0.35) !important;
                font-weight: 600 !important;
            }

            [data-testid="stButtonGroup"] button[aria-checked="true"] * {
                color: #ffffff !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # =====================================================================
        # ZONE 1: BRAND IDENTITY (Glassmorphic Violet Header)
        # =====================================================================
        st.markdown(
            """
            <div style="padding: 1.1rem 1rem; text-align: center; background: linear-gradient(135deg, #6366f1 0%, #7c3aed 50%, #9333ea 100%); border-radius: 12px; margin-bottom: 0.5rem; box-shadow: 0 4px 16px rgba(99, 102, 241, 0.28); border: 1px solid rgba(255, 255, 255, 0.18);">
                <div style="font-size: 2.1rem; line-height: 1; margin-bottom: 0.35rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.15));">🧠</div>
                <div style="color: #ffffff; font-size: 1.25rem; font-weight: 700; letter-spacing: -0.3px; line-height: 1.2;">Cognitive AI</div>
                <div style="font-size: 0.78rem; color: rgba(255, 255, 255, 0.92); font-weight: 300; margin-top: 0.25rem; letter-spacing: 0.2px;">Adaptive Learning Platform</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # State resolution with auto-hydration from backend cache
        roadmap = st.session_state.get("roadmap")
        if not roadmap:
            try:
                from services.roadmap_service import roadmap_service
                cached_rm = roadmap_service.get_roadmap()
                if cached_rm and cached_rm.get("modules"):
                    st.session_state.roadmap = cached_rm
                    roadmap = cached_rm
            except Exception:
                pass

        current_module = st.session_state.get("current_module")
        current_module_id = st.session_state.get("current_module_id")

        # Auto-hydrate current_module if roadmap exists
        if not current_module and roadmap and roadmap.get("modules"):
            if current_module_id:
                for mod in roadmap["modules"]:
                    if mod.get("module_id") == current_module_id:
                        current_module = mod
                        break
            if not current_module:
                current_module = roadmap["modules"][0]
                current_module_id = current_module.get("module_id")
                st.session_state.current_module = current_module
                st.session_state.current_module_id = current_module_id

        current_input_id = st.session_state.get("current_input_id")

        has_input = bool(current_input_id) or bool(roadmap)
        has_roadmap = bool(roadmap)
        has_module = bool(current_module)

        # =====================================================================
        # ZONE 2: WORKSPACE (Tier 1 Global Navigation)
        # =====================================================================
        st.markdown(
            "<div style='font-size: 0.65rem; font-weight: 700; color: #94a3b8; letter-spacing: 0.9px; text-transform: uppercase; margin: 0.35rem 0 0.25rem 0.2rem;'>Workspace</div>",
            unsafe_allow_html=True,
        )

        is_dash_active = current_page == "app.py"
        if st.button(
            "🏠  Overview & Home",
            type="primary" if is_dash_active else "secondary",
            use_container_width=True,
            key="sb_nav_dash",
        ):
            if not is_dash_active:
                st.switch_page("app.py")

        is_input_active = current_page == "1_📤_Input.py"
        input_label = "📤  Document Ingestion  ✓" if has_input else "📤  Document Ingestion"
        if st.button(
            input_label,
            type="primary" if is_input_active else "secondary",
            use_container_width=True,
            key="sb_nav_input",
        ):
            if not is_input_active:
                st.switch_page("pages/1_📤_Input.py")

        is_roadmap_active = current_page == "2_🗺️_Roadmap.py"
        total_mods = roadmap.get("total_modules", len(roadmap.get("modules", []))) if roadmap else 0
        roadmap_label = f"🗺️  Roadmap ({total_mods} Modules)" if has_roadmap else "🗺️  Curriculum Roadmap"
        
        if st.button(
            roadmap_label,
            type="primary" if is_roadmap_active else "secondary",
            disabled=not (has_input or has_roadmap),
            use_container_width=True,
            key="sb_nav_roadmap",
        ):
            if not is_roadmap_active:
                st.switch_page("pages/2_🗺️_Roadmap.py")

        # =====================================================================
        # ZONE 3: CURRENT MISSION (Tier 2 Integrated Module Cockpit)
        # =====================================================================
        st.markdown(
            "<div style='border-top: 1px solid rgba(226, 232, 240, 0.7); margin: 0.65rem 0 0.5rem 0;'></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='font-size: 0.65rem; font-weight: 700; color: #94a3b8; letter-spacing: 0.9px; text-transform: uppercase; margin: 0 0 0.35rem 0.2rem;'>Current Mission</div>",
            unsafe_allow_html=True,
        )

        if has_roadmap and has_module:
            topic_name = current_module.get("topic_name", "Unknown Topic")
            order = current_module.get("order", 1)
            total = roadmap.get("total_modules", len(roadmap.get("modules", [])))
            mode = roadmap.get("mode", "untimed").title()
            progress_pct = int(min(100, max(5, (order / float(total)) * 100)))

            # Integrated Mission Cockpit Card
            st.markdown(
                f"""
                <div style="background: #ffffff; border-radius: 12px; border: 1px solid rgba(99, 102, 241, 0.22); border-left: 4px solid #6366f1; padding: 0.85rem 0.95rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03); margin-bottom: 0.45rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                        <span style="font-size: 0.65rem; font-weight: 700; color: #6366f1; letter-spacing: 0.6px; text-transform: uppercase;">MODULE {order} OF {total}</span>
                        <span style="font-size: 0.72rem; font-weight: 600; color: #475569; background: #f1f5f9; padding: 0.12rem 0.45rem; border-radius: 6px;">⏱️ {mode}</span>
                    </div>
                    <div style="font-weight: 700; color: #0f172a; font-size: 0.92rem; line-height: 1.35; margin-bottom: 0.45rem;">{topic_name}</div>
                    <div style="background: #f1f5f9; border-radius: 999px; height: 5px; width: 100%; overflow: hidden; margin-bottom: 0.35rem; border: 1px solid rgba(226, 232, 240, 0.6);">
                        <div style="background: linear-gradient(90deg, #6366f1, #8b5cf6, #d946ef); height: 100%; width: {progress_pct}%; border-radius: 999px;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748b; font-weight: 500;">
                        <span>Course Milestone</span>
                        <span style="color: #6366f1; font-weight: 600;">{progress_pct}%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Integrated Action Deck
            is_content_active = current_page == "3_📚_Content.py"
            if st.button(
                "📖  Study Notes & Cheat Sheet",
                type="primary" if is_content_active else "secondary",
                use_container_width=True,
                key="sb_nav_content",
            ):
                st.session_state.active_content_tab = "📖 Detailed Study Notes"
                if not is_content_active:
                    st.switch_page("pages/3_📚_Content.py")
                else:
                    st.rerun()

            is_quiz_active = current_page == "4_🧪_Quiz.py"
            if st.button(
                "🧪  Practice Assessment Quiz",
                type="primary" if is_quiz_active else "secondary",
                use_container_width=True,
                key="sb_nav_quiz",
            ):
                if not is_quiz_active:
                    st.switch_page("pages/4_🧪_Quiz.py")

            # =================================================================
            # ZONE 4: AI STUDY BUDDY WIDGET (Human Connection)
            # =================================================================
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%); border-radius: 10px; border: 1px dashed rgba(99, 102, 241, 0.32); padding: 0.65rem 0.8rem; margin-top: 0.35rem; margin-bottom: 0.15rem;">
                    <div style="display: flex; align-items: center; gap: 0.35rem; margin-bottom: 0.15rem;">
                        <span style="font-size: 0.95rem;">💡</span>
                        <span style="font-size: 0.76rem; font-weight: 700; color: #4f46e5;">AI Tutor Ready</span>
                    </div>
                    <div style="font-size: 0.71rem; color: #64748b; line-height: 1.35;">
                        Have a concept question? Ask your verified AI tutor.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("💬  Ask a Doubt →", use_container_width=True, key="sb_nav_ask_doubt"):
                st.session_state.active_content_tab = "💡 AI Doubt Assistant"
                if not is_content_active:
                    st.switch_page("pages/3_📚_Content.py")
                else:
                    st.rerun()

        elif has_roadmap:
            # Roadmap ready, guide user to pick a module
            st.markdown(
                """
                <div style="background: #ffffff; border-radius: 12px; border: 1px dashed #cbd5e1; padding: 0.95rem 0.85rem; text-align: center; margin-bottom: 0.35rem;">
                    <div style="font-size: 1.4rem; margin-bottom: 0.25rem;">🗺️</div>
                    <div style="font-weight: 700; font-size: 0.86rem; color: #1e293b; margin-bottom: 0.2rem;">Choose a Module</div>
                    <div style="font-size: 0.73rem; color: #64748b; line-height: 1.35; margin-bottom: 0.5rem;">
                        Select a module in your Roadmap to unlock study materials, cheat sheets, and quizzes.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🗺️  Open Roadmap", use_container_width=True, key="sb_nav_goto_rm"):
                st.switch_page("pages/2_🗺️_Roadmap.py")

        elif has_input:
            # Input uploaded, ready to generate roadmap
            st.markdown(
                """
                <div style="background: #ffffff; border-radius: 12px; border-left: 4px solid #10b981; border: 1px solid rgba(16, 185, 129, 0.25); padding: 0.85rem 0.95rem; margin-bottom: 0.35rem;">
                    <div style="font-weight: 700; font-size: 0.85rem; color: #065f46; margin-bottom: 0.2rem;">✅ Material Ready</div>
                    <div style="font-size: 0.73rem; color: #64748b; line-height: 1.35; margin-bottom: 0.5rem;">
                        Course text extracted. Generate your curriculum roadmap to begin.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("⚡  Generate Roadmap", use_container_width=True, key="sb_nav_gen_rm"):
                st.switch_page("pages/2_🗺️_Roadmap.py")

        else:
            # Cold start onboarding state
            st.markdown(
                """
                <div style="background: #ffffff; border-radius: 12px; border: 1px dashed #cbd5e1; padding: 1rem 0.85rem; text-align: center; margin-bottom: 0.35rem;">
                    <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">📄</div>
                    <div style="font-weight: 700; font-size: 0.88rem; color: #1e293b; margin-bottom: 0.2rem;">Welcome!</div>
                    <div style="font-size: 0.74rem; color: #64748b; line-height: 1.35; margin-bottom: 0.5rem;">
                        Upload a syllabus, lecture notes, or textbook text to construct your personalized path.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("📤  Upload Material", use_container_width=True, key="sb_nav_goto_input"):
                st.switch_page("pages/1_📤_Input.py")

        # =====================================================================
        # ZONE 5: PLATFORM CONTROLS & DIAGNOSTICS FOOTER
        # =====================================================================
        st.markdown(
            "<div style='border-top: 1px solid rgba(226, 232, 240, 0.7); margin: 0.65rem 0 0.35rem 0;'></div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "🔄  Reset to Initial State",
            type="secondary",
            use_container_width=True,
            key="sb_btn_reset_platform",
            help="Completely reset the course, roadmap, notes, and quiz data back to the clean initial state.",
        ):
            _confirm_reset_dialog()

        with st.expander("⚙️ System Status", expanded=False):
            from config import config
            from services.api_client import api_client
            from components.error_display import show_error, show_success

            def check_backend_health_inline():
                try:
                    return api_client.health_check()
                except Exception:
                    return False

            def sync_backend_session_inline():
                try:
                    session_data = api_client.get("/api/session")
                    st.session_state.backend_session_id = session_data.get("session_id")
                    st.session_state.backend_session_data = session_data
                    st.session_state.current_input_id = session_data.get("current_input_id")
                    if session_data.get("roadmap_generated", False):
                        st.session_state.roadmap_mode = session_data.get("roadmap_mode")
                    if session_data.get("current_module_id"):
                        st.session_state.current_module_id = session_data.get("current_module_id")
                    return True
                except Exception as e:
                    show_error("Failed to sync with backend", str(e))
                    return False

            if st.session_state.get("backend_session_id"):
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

        # Grounding status footer
        st.markdown(
            """
            <div style="text-align: center; margin-top: 0.5rem; font-size: 0.66rem; color: #94a3b8; letter-spacing: 0.3px;">
                ⚡ Local Qwen 1.5B • CPU Accelerated • Online
            </div>
            """,
            unsafe_allow_html=True,
        )
