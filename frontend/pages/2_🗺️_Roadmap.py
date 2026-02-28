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
from utils.state_manager import ensure_session_hydrated, reset_course_state
from utils.formatters import format_hours
from components.loading_spinner import with_loading
from components.error_display import (
    show_error, show_success, show_info, show_warning,
    handle_api_error, display_session_messages
)
from components.navigation import render_page_header, render_bottom_nav
import importlib
import ui.sidebar
importlib.reload(ui.sidebar)
from ui.sidebar import render_sidebar

# Page configuration
st.set_page_config(
    page_title="Roadmap",
    layout=config.LAYOUT
)

# Ensure session is hydrated on cold page reload
ensure_session_hydrated()

# Render sidebar
render_sidebar()

HELP_TEXT = """
### How to use this page

**Generating a new roadmap:**
1. Select your preferred pacing mode (**Timed** or **Untimed**).
2. Click the generate button to construct your structured curriculum.
3. Modules are ordered sequentially based on prerequisite dependencies.

**Working with an existing roadmap:**
1. Review the sequential module cards.
2. Click **Study** to view detailed notes and cheat sheets.
3. Click **Quiz** to attempt module assessments.
4. Click **Start Learning (Module 1)** below to begin step-by-step.

### Pacing Modes
- **Timed Mode:** Assigns estimated completion hours and structured timelines.
- **Untimed Mode:** Flexible, self-paced mastery with no time constraints.
"""

# Render clean modern page header with popover help and stage stepper
render_page_header(
    title="Learning Roadmap",
    subtitle="Structured learning curriculum generated from your course materials",
    current_stage=2,
    help_text=HELP_TEXT
)

# Display any session messages
display_session_messages()

# Check roadmap state
has_roadmap = st.session_state.get('roadmap') is not None
has_input = bool(st.session_state.get('current_input_id'))

# Guard: No input and no roadmap
if not has_roadmap and not has_input:
    show_warning("No syllabus input found. Please provide educational content on the Input page first.")
    render_bottom_nav(
        prev_label="Go to Input Page",
        prev_page="pages/1_📤_Input.py",
        next_label=None
    )
    st.stop()


# ========================================
# RESET CONFIRMATION MODAL / DIALOG
# ========================================
@st.dialog("Reset Learning Roadmap?")
def confirm_reset_dialog():
    st.write("This will permanently clear your current roadmap, module progress, and cached notes. Are you sure?")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Yes, Clear Roadmap", type="primary", use_container_width=True):
            try:
                roadmap_service.delete_roadmap()
            except Exception:
                pass
            reset_course_state()
            show_success("Roadmap and learning materials reset successfully.")
            st.rerun()
    with col_no:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ========================================
# SECTION A: GENERATION (ONLY IF NO ROADMAP)
# ========================================
if not has_roadmap:
    with st.container(border=True):
        st.markdown("### Generate Your Learning Path")
        st.caption("Select your preferred pacing mode to construct your curriculum modules.")
        
        input_id = st.session_state.get('current_input_id', 'unknown')
        st.info(f"Source Input Reference: `{input_id[:24]}...`")

        col1, col2 = st.columns(2, gap="large")

        with col1:
            with st.container(border=True):
                st.markdown("### Timed Mode")
                st.markdown("""
                - **Targeted pacing** with estimated hour budgets
                - Structured timelines and study intervals
                - Optimized for deadlines and exam schedules
                """)
                if st.button("Select Timed Mode", key="gen_timed", type="primary", use_container_width=True):
                    def generate_timed():
                        return roadmap_service.generate_roadmap(input_id, "timed")

                    try:
                        result = with_loading(
                            generate_timed,
                            loading_message="Generating timed roadmap...",
                            info_message="Structuring modules and prerequisite graph..."
                        )
                        if result:
                            st.session_state.roadmap = result
                            st.session_state.roadmap_mode = "timed"
                            modules = result.get('modules', [])
                            if modules:
                                st.session_state.current_module_id = modules[0].get('module_id')
                                st.session_state.current_module = modules[0]
                            show_success(f"Roadmap generated. {len(modules)} modules created.")
                            st.rerun()
                    except Exception as e:
                        handle_api_error(e, "Roadmap generation")

        with col2:
            with st.container(border=True):
                st.markdown("### Untimed Mode")
                st.markdown("""
                - **Self-paced mastery** with zero time constraints
                - Deep topic exploration and practice
                - Ideal for continuous comprehensive learning
                """)
                if st.button("Select Untimed Mode", key="gen_untimed", type="primary", use_container_width=True):
                    def generate_untimed():
                        return roadmap_service.generate_roadmap(input_id, "untimed")

                    try:
                        result = with_loading(
                            generate_untimed,
                            loading_message="Generating self-paced roadmap...",
                            info_message="Structuring modules and prerequisite graph..."
                        )
                        if result:
                            st.session_state.roadmap = result
                            st.session_state.roadmap_mode = "untimed"
                            modules = result.get('modules', [])
                            if modules:
                                st.session_state.current_module_id = modules[0].get('module_id')
                                st.session_state.current_module = modules[0]
                            show_success(f"Roadmap generated. {len(modules)} modules created.")
                            st.rerun()
                    except Exception as e:
                        handle_api_error(e, "Roadmap generation")

    render_bottom_nav(
        prev_label="Edit Input",
        prev_page="pages/1_📤_Input.py"
    )

# ========================================
# SECTION B: DISPLAY ROADMAP MODULES
# ========================================
else:
    roadmap = st.session_state.roadmap
    mode = roadmap.get('mode', 'untimed')
    modules = roadmap.get('modules', [])
    total_modules = roadmap.get('total_modules', len(modules))

    # Top summary metrics card
    with st.container(border=True):
        st.markdown("### Curriculum Overview")
        st.caption(f"Curriculum path: {total_modules} structured modules")

        if mode == 'timed':
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Mode", "Timed")
            with c2:
                st.metric("Total Modules", total_modules)
            with c3:
                total_hours = roadmap.get('total_estimated_hours', 0)
                st.metric("Total Duration", format_hours(total_hours))
            with c4:
                st.metric("Status", "Cached" if roadmap.get('cached') else "Generated")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Mode", "Untimed")
            with c2:
                st.metric("Total Modules", total_modules)
            with c3:
                st.metric("Status", "Cached" if roadmap.get('cached') else "Generated")

        # Visual curriculum pacing progress meter
        curr_mod_order = 1
        if st.session_state.get('current_module'):
            curr_mod_order = st.session_state.current_module.get('order', 1)
        cur_pct = int(min(100, max(5, (curr_mod_order / float(total_modules)) * 100)))

        st.markdown(
            f"""
            <div style="margin-top: 0.65rem; padding-top: 0.65rem; border-top: 1px solid rgba(226, 232, 240, 0.7);">
                <div style="display: flex; justify-content: space-between; font-size: 0.74rem; color: #64748b; font-weight: 600; margin-bottom: 0.35rem;">
                    <span>Curriculum Pathway Progress</span>
                    <span style="color: #6366f1;">Active: Module {curr_mod_order} of {total_modules} ({cur_pct}%)</span>
                </div>
                <div style="background: #f1f5f9; border-radius: 999px; height: 6px; width: 100%; overflow: hidden; border: 1px solid rgba(226, 232, 240, 0.8);">
                    <div style="background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%); height: 100%; width: {cur_pct}%; border-radius: 999px;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("")

    # Build mapping for prerequisites
    module_id_to_name = {
        m.get('module_id'): m.get('topic_name', 'Unknown')
        for m in modules
    }

    # ========================================
    # SEQUENTIAL LEARNING JOURNEY (UNIFIED EMBEDDED MATRIX)
    # ========================================
    st.markdown("### Sequential Learning Journey")
    st.caption("Each module builds upon foundational concepts. Review module prerequisites, study hours, and launch activities.")

    total_hrs = roadmap.get('total_estimated_hours', max(1.0, sum(m.get('estimated_hours', 1) for m in modules)))
    cumulative_hours = 0.0

    for module in modules:
        m_id = module.get('module_id')
        m_order = module.get('order', 1)
        m_topic = module.get('topic_name', 'Untitled Topic')
        m_hours = module.get('estimated_hours', 0)
        m_prereqs = module.get('prerequisites', [])

        cumulative_hours += m_hours
        pct_curriculum = int(round((m_hours / total_hrs) * 100)) if total_hrs > 0 else 0

        is_current = st.session_state.get('current_module_id') == m_id

        prereq_labels = [module_id_to_name.get(p, p) for p in m_prereqs]
        prereq_badge = f"Requires: {', '.join(prereq_labels)}" if prereq_labels else "Core Foundation"

        with st.container(border=True):
            col_info, col_actions = st.columns([3, 2], vertical_alignment="center")

            with col_info:
                if is_current:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem;">
                            <span style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 999px; letter-spacing: 0.3px;">CURRENT MILESTONE</span>
                            <span style="font-size: 0.74rem; color: #6366f1; font-weight: 600;">Step {m_order} of {total_modules}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.2rem;">
                            Step {m_order:02d}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                st.markdown(f"#### {m_topic}")

                if mode == 'timed':
                    st.caption(f"⏱️ **{format_hours(m_hours)}** ({pct_curriculum}% of path) &nbsp;|&nbsp; 🔗 *{prereq_badge}* &nbsp;|&nbsp; 📈 Cumul: {format_hours(cumulative_hours)}")
                else:
                    st.caption(f"🔗 *{prereq_badge}* &nbsp;|&nbsp; 📈 Weight: {pct_curriculum}%")

            with col_actions:
                col_btn_study, col_btn_quiz = st.columns(2)
                with col_btn_study:
                    if st.button("Study Notes", key=f"btn_study_{m_id}", use_container_width=True, type="primary" if is_current else "secondary"):
                        st.session_state.current_module_id = m_id
                        st.session_state.current_module = module
                        st.session_state.active_content_tab = "📖 Detailed Study Notes"
                        st.switch_page("pages/3_📚_Content.py")
                with col_btn_quiz:
                    if st.button("Module Quiz", key=f"btn_quiz_{m_id}", use_container_width=True):
                        st.session_state.current_module_id = m_id
                        st.session_state.current_module = module
                        st.switch_page("pages/4_🧪_Quiz.py")

    # ========================================
    # STAGE BOTTOM NAVIGATION DECK
    # ========================================
    first_module = modules[0] if modules else None
    first_title = first_module.get('topic_name', 'Module 1') if first_module else "Module 1"
    
    def on_start_learning():
        if first_module:
            st.session_state.current_module_id = first_module.get('module_id')
            st.session_state.current_module = first_module
        st.switch_page("pages/3_📚_Content.py")

    render_bottom_nav(
        prev_label="Edit Syllabus / Input",
        prev_page="pages/1_📤_Input.py",
        extra_action_label="Reset Roadmap",
        extra_action_cb=confirm_reset_dialog,
        next_label=f"Start Learning ({first_title[:24]})",
        on_next_click=on_start_learning
    )
