"""
Navigation components for Cognitive AI Learning Platform.

Provides a unified stage stepper and standardized bottom navigation deck
across all educational pipeline pages with solid interactive buttons.
"""

from typing import Optional, Callable
import streamlit as st


STAGES = [
    {"num": 1, "title": "Input", "page": "pages/1_📤_Input.py"},
    {"num": 2, "title": "Roadmap", "page": "pages/2_🗺️_Roadmap.py"},
    {"num": 3, "title": "Study", "page": "pages/3_📚_Content.py"},
    {"num": 4, "title": "Quiz", "page": "pages/4_🧪_Quiz.py"},
]


def render_page_header(title: str, subtitle: str, current_stage: int, help_text: Optional[str] = None):
    """
    Render a clean, modern page header with optional help popover and stage stepper.
    
    Args:
        title: Main title of the page
        subtitle: Subtitle/caption for context
        current_stage: Active stage number (1 to 4)
        help_text: Optional markdown string shown in a compact popover
    """
    col_title, col_help = st.columns([5, 1], vertical_alignment="center")
    
    with col_title:
        st.title(title)
        st.caption(subtitle)
        
    with col_help:
        if help_text:
            with st.popover("Page Help", use_container_width=True):
                st.markdown(help_text)

    render_stage_stepper(current_stage)
    st.divider()


def render_stage_stepper(current_stage: int):
    """
    Render a 4-stage visual progress stepper with solid interactive button controls.
    
    Stages:
    1: Input (Upload or text)
    2: Roadmap (Curriculum generated)
    3: Study (Notes & cheat sheets)
    4: Quiz (Assessment & mastery)
    """
    has_roadmap = bool(st.session_state.get("roadmap"))
    has_input = bool(st.session_state.get("current_input_id")) or has_roadmap
    has_module = bool(st.session_state.get("current_module_id"))
    
    is_accessible = {
        1: True,
        2: has_input or has_roadmap,
        3: has_roadmap,
        4: has_roadmap and has_module,
    }
    
    completed_count = 0
    if has_input:
        completed_count += 1
    if has_roadmap:
        completed_count += 1
    if st.session_state.get("content_cache"):
        completed_count += 1
    if st.session_state.get("quiz_cache"):
        completed_count += 1
    progress_val = min(1.0, max(0.05, completed_count / 4.0))

    cols = st.columns(4, gap="small")
    for idx, stage in enumerate(STAGES):
        s_num = stage["num"]
        with cols[idx]:
            if s_num == current_stage:
                st.button(
                    f"Step {s_num}: {stage['title']} (Active)",
                    type="primary",
                    disabled=True,
                    use_container_width=True,
                    key=f"stepper_btn_{s_num}"
                )
            else:
                accessible = is_accessible[s_num]
                done_suffix = " [Done]" if (s_num < current_stage or (s_num == 1 and has_input) or (s_num == 2 and has_roadmap)) else ""
                label = f"Step {s_num}: {stage['title']}{done_suffix}"
                if st.button(
                    label,
                    disabled=not accessible,
                    use_container_width=True,
                    key=f"stepper_btn_{s_num}"
                ):
                    st.switch_page(stage["page"])

    st.progress(progress_val, text=f"Pipeline Stage: Step {current_stage} of 4")


def render_bottom_nav(
    prev_label: Optional[str] = None,
    prev_page: Optional[str] = None,
    next_label: Optional[str] = None,
    next_page: Optional[str] = None,
    next_disabled: bool = False,
    extra_action_label: Optional[str] = None,
    extra_action_cb: Optional[Callable] = None,
    on_next_click: Optional[Callable] = None,
    on_prev_click: Optional[Callable] = None,
):
    """
    Standardized footer navigation deck using solid interactive buttons.
    
    Provides balanced button styling across Previous, Extra Actions, and Next.
    """
    st.divider()
    
    col_prev, col_mid, col_next = st.columns([1, 1, 1], gap="medium")
    
    with col_prev:
        if prev_page:
            if st.button(prev_label or "Previous Step", use_container_width=True, key=f"btn_nav_prev_{prev_page}"):
                st.switch_page(prev_page)
        elif prev_label and on_prev_click:
            if st.button(prev_label, use_container_width=True, key="bottom_prev_btn"):
                on_prev_click()
                
    with col_mid:
        if extra_action_label and extra_action_cb:
            if st.button(extra_action_label, use_container_width=True, key="bottom_extra_btn"):
                extra_action_cb()
                
    with col_next:
        if next_page:
            if st.button(next_label or "Proceed to Next", type="primary", disabled=next_disabled, use_container_width=True, key=f"btn_nav_next_{next_page}"):
                st.switch_page(next_page)
        elif next_label and on_next_click:
            if st.button(next_label, type="primary", disabled=next_disabled, use_container_width=True, key="bottom_next_btn"):
                on_next_click()
