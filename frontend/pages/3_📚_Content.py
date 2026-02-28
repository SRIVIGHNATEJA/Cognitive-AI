"""
Content page - View detailed notes and cheat sheets for modules.

Allows users to generate and view educational content for each module
in their learning roadmap.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from services.content_service import content_service
from utils.state_manager import ensure_session_hydrated
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
    page_title="Content",
    layout=config.LAYOUT
)

# Ensure session is hydrated on cold page reload
ensure_session_hydrated()

# Render sidebar
render_sidebar()

HELP_TEXT = """
### How to use this page

1. **Select a module:** Click any module chip in the top ribbon to load its study materials.
2. **Content views:**
   - **Detailed Notes:** Complete explanations, code snippets, and structured concepts.
   - **Cheat Sheet:** High-yield reference guide, syntax, and essential formulas.
3. **On-Demand Generation:** Content is synthesized once by AI and permanently cached for instant subsequent loads.
4. **Ask Doubts:** Enter questions below to receive focused, contextual clarifications.
5. **Next Step:** When ready, proceed to **Take Quiz** to validate your understanding.
"""

# Render clean modern page header with popover help and stage stepper
render_page_header(
    title="Module Study Materials",
    subtitle="Detailed lecture notes, cheat sheets, and targeted concept clarification",
    current_stage=3,
    help_text=HELP_TEXT
)

# Display any session messages
display_session_messages()

# Guard: Roadmap must exist
if not st.session_state.get('roadmap'):
    show_warning("No roadmap found. Please generate a learning roadmap first.")
    render_bottom_nav(
        prev_label="Go to Roadmap Page",
        prev_page="pages/2_🗺️_Roadmap.py"
    )
    st.stop()

# Get roadmap data
roadmap = st.session_state.roadmap
modules = roadmap.get('modules', [])
mode = roadmap.get('mode', 'untimed')

if not modules:
    show_error("No modules found in roadmap.")
    st.stop()

# Ensure active module is set
if not st.session_state.get('current_module_id'):
    st.session_state.current_module_id = modules[0].get('module_id')
    st.session_state.current_module = modules[0]

current_module_id = st.session_state.get('current_module_id')

# Injected Page CSS for Oval Pills & Theme Consistency
st.markdown(
    """
    <style>
    /* 1. Modern Module Oval Pills Styling (st.pills / stButtonGroup) */
    [data-testid="stButtonGroup"], [data-baseweb="button-group"] {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 0.45rem !important;
        border: none !important;
        background: transparent !important;
        margin-bottom: 0.25rem !important;
    }

    [data-testid="stButtonGroup"] button,
    [data-baseweb="button-group"] button {
        border-radius: 999px !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        padding: 0.35rem 0.95rem !important;
        min-height: 2.1rem !important;
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
    unsafe_allow_html=True
)

# ========================================
# MODULE RIBBON SELECTOR
# ========================================
st.markdown(
    "<div style='font-size: 0.68rem; font-weight: 700; color: #94a3b8; letter-spacing: 0.9px; text-transform: uppercase; margin-bottom: 0.35rem;'>Course Modules</div>",
    unsafe_allow_html=True
)

def _format_pill_label(mod):
    order = mod.get('order', 1)
    topic = mod.get('topic_name', f'Module {order}')
    short_names = {
        "Introduction to Artificial Intelligence": "Intro to AI",
        "History of AI Development": "AI History",
        "Types and Applications of AI": "Types & Apps",
        "Machine Learning Basics": "ML Basics",
        "Artificial Neural Networks": "Neural Networks",
        "Natural Language Processing (NLP)": "NLP",
        "Computer Vision": "Computer Vision",
    }
    short = short_names.get(topic, topic)
    if len(short) > 18:
        short = short[:17] + "…"
    return f"Mod {order}: {short}"

label_to_mod = {
    _format_pill_label(m): m
    for m in modules
}
options = list(label_to_mod.keys())

current_label = options[0]
for lbl, m in label_to_mod.items():
    if m.get('module_id') == current_module_id:
        current_label = lbl
        break

# Synchronize pill widget state whenever current_module_id changes externally
# (e.g. Next Module, Previous Module, Roadmap click, or Quiz completion)
if current_label and st.session_state.get("content_module_pills") != current_label:
    st.session_state["content_module_pills"] = current_label

def on_content_module_pill_change():
    chosen_label = st.session_state.get("content_module_pills")
    if chosen_label and chosen_label in label_to_mod:
        chosen_mod = label_to_mod[chosen_label]
        st.session_state.current_module_id = chosen_mod.get('module_id')
        st.session_state.current_module = chosen_mod
        st.session_state.doubt_answer = None
        st.session_state.doubt_question = ""

st.pills(
    "Modules:",
    options=options,
    label_visibility="collapsed",
    key="content_module_pills",
    on_change=on_content_module_pill_change
)

current_module = st.session_state.get('current_module', modules[0])
topic_name = current_module.get('topic_name', 'Unknown')
estimated_hours = current_module.get('estimated_hours', 0)
order = current_module.get('order', 1)
total_mods = len(modules)
prerequisites = current_module.get('prerequisites', [])
progress_pct = int(min(100, max(5, (order / float(total_mods)) * 100)))

module_id_to_name = {m.get('module_id'): m.get('topic_name', 'Unknown') for m in modules}
prereq_names = [module_id_to_name.get(p, p) for p in prerequisites]
prereq_str = ", ".join(prereq_names) if prereq_names else "Core Foundation (No Prerequisites)"

# ========================================
# SLEEK MODULE HEADS-UP DISPLAY (HUD)
# ========================================
time_badge = f"⏱️ {format_hours(estimated_hours)}" if mode == 'timed' else f"📍 Step {order} of {total_mods}"

st.markdown(
    f"""
    <div style="background: #ffffff; border-radius: 12px; border: 1px solid rgba(99, 102, 241, 0.22); border-left: 4px solid #6366f1; padding: 0.95rem 1.25rem; margin: 0.5rem 0 1rem 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; flex-wrap: wrap; gap: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; font-size: 0.68rem; font-weight: 700; padding: 0.18rem 0.55rem; border-radius: 999px; letter-spacing: 0.4px;">MODULE {order} OF {total_mods}</span>
                <span style="font-size: 0.74rem; color: #64748b; font-weight: 500;">🔗 {prereq_str}</span>
            </div>
            <span style="font-size: 0.76rem; font-weight: 600; color: #4338ca; background: #eef2ff; padding: 0.15rem 0.6rem; border-radius: 6px; border: 1px solid rgba(99, 102, 241, 0.15);">{time_badge}</span>
        </div>
        <div style="font-size: 1.3rem; font-weight: 700; color: #0f172a; line-height: 1.3; margin: 0.3rem 0 0.5rem 0;">{topic_name}</div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="flex-grow: 1; background: #f1f5f9; border-radius: 999px; height: 5px; overflow: hidden; border: 1px solid rgba(226, 232, 240, 0.8);">
                <div style="background: linear-gradient(90deg, #6366f1 0%, #7c3aed 50%, #8b5cf6 100%); height: 100%; width: {progress_pct}%; border-radius: 999px;"></div>
            </div>
            <span style="font-size: 0.72rem; color: #64748b; font-weight: 600;">{progress_pct}% Milestone</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if 'content_cache' not in st.session_state:
    st.session_state.content_cache = {}

if current_module_id not in st.session_state.content_cache:
    st.session_state.content_cache[current_module_id] = {
        'notes': None,
        'cheatsheet': None
    }

# ========================================
# STUDY CONTENT TABS
# ========================================
content_tabs = [
    "📖 Detailed Study Notes",
    "⚡ High-Yield Cheat Sheet",
    "💡 AI Doubt Assistant"
]

target_tab = st.session_state.pop("active_content_tab", None)
if target_tab not in content_tabs:
    target_tab = None

tab_notes, tab_cheatsheet, tab_doubts = st.tabs(
    content_tabs,
    default=target_tab
)

# -------- TAB 1: DETAILED NOTES --------
with tab_notes:
    cached_notes = st.session_state.content_cache[current_module_id].get('notes')

    if cached_notes:
        if cached_notes.get('cached'):
            st.caption("Loaded from local session cache")
        else:
            st.caption("Freshly generated notes")

        content_text = cached_notes.get('notes', '')
        if content_text:
            st.markdown(content_text)
        else:
            st.warning("Generated content was empty.")
    else:
        try:
            with st.spinner("Checking cache for existing notes..."):
                backend_notes = content_service.get_notes(current_module_id)

            if backend_notes:
                st.session_state.content_cache[current_module_id]['notes'] = backend_notes
                st.caption("Retrieved from server cache")
                st.markdown(backend_notes.get('notes', ''))
            else:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="text-align: center; padding: 1.25rem 1rem 0.5rem 1rem;">
                            <div style="font-size: 2.2rem; margin-bottom: 0.35rem; line-height: 1;">📖</div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">Detailed Study Notes Ready to Synthesize</div>
                            <div style="font-size: 0.82rem; color: #64748b; max-width: 500px; margin: 0 auto 1.1rem auto; line-height: 1.45;">
                                AI will generate in-depth conceptual notes, step-by-step principles, and practical examples specifically tailored for <strong>{topic_name}</strong>.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button("✨ Synthesize In-Depth Study Notes", type="primary", use_container_width=True, key=f"gen_notes_{current_module_id}"):
                        def generate_notes_action():
                            return content_service.generate_notes(current_module_id)

                        try:
                            result = with_loading(
                                generate_notes_action,
                                loading_message="Generating in-depth study notes...",
                                info_message="Synthesizing course materials and structure..."
                            )
                            if result:
                                st.session_state.content_cache[current_module_id]['notes'] = result
                                show_success("Notes generated successfully.")
                                st.rerun()
                        except Exception as e:
                            handle_api_error(e, "Notes generation")
        except Exception as e:
            handle_api_error(e, "Notes retrieval")

# -------- TAB 2: CHEAT SHEET --------
with tab_cheatsheet:
    cached_cs = st.session_state.content_cache[current_module_id].get('cheatsheet')

    if cached_cs:
        if cached_cs.get('cached'):
            st.caption("Loaded from local session cache")
        else:
            st.caption("Freshly generated cheat sheet")

        content_text = cached_cs.get('cheat_sheet', '')
        if content_text:
            st.markdown(content_text)
        else:
            st.warning("Generated cheat sheet was empty.")
    else:
        try:
            with st.spinner("Checking cache for cheat sheet..."):
                backend_cs = content_service.get_cheatsheet(current_module_id)

            if backend_cs:
                st.session_state.content_cache[current_module_id]['cheatsheet'] = backend_cs
                st.caption("Retrieved from server cache")
                st.markdown(backend_cs.get('cheat_sheet', ''))
            else:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="text-align: center; padding: 1.25rem 1rem 0.5rem 1rem;">
                            <div style="font-size: 2.2rem; margin-bottom: 0.35rem; line-height: 1;">⚡</div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">High-Yield Cheat Sheet Ready to Synthesize</div>
                            <div style="font-size: 0.82rem; color: #64748b; max-width: 500px; margin: 0 auto 1.1rem auto; line-height: 1.45;">
                                AI will extract formulas, core definitions, syntax summaries, and high-yield exam takeaways for <strong>{topic_name}</strong>.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button("⚡ Generate High-Yield Cheat Sheet", type="primary", use_container_width=True, key=f"gen_cs_{current_module_id}"):
                        def generate_cs_action():
                            return content_service.generate_cheatsheet(current_module_id)

                        try:
                            result = with_loading(
                                generate_cs_action,
                                loading_message="Generating high-yield cheat sheet...",
                                info_message="Compiling formulas, syntax, and key principles..."
                            )
                            if result:
                                st.session_state.content_cache[current_module_id]['cheatsheet'] = result
                                show_success("Cheat sheet generated successfully.")
                                st.rerun()
                        except Exception as e:
                            handle_api_error(e, "Cheat sheet generation")
        except Exception as e:
            handle_api_error(e, "Cheat sheet retrieval")

# -------- TAB 3: AI DOUBT ASSISTANT --------
with tab_doubts:
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%); border-radius: 10px; border-left: 4px solid #6366f1; padding: 0.75rem 1rem; margin-bottom: 0.85rem;">
            <div style="font-weight: 700; color: #4338ca; font-size: 0.95rem;">💡 AI Tutor Active: {topic_name}</div>
            <div style="font-size: 0.8rem; color: #475569; margin-top: 0.15rem;">Ask any conceptual question or clarification grounded strictly in Module {order}'s verified curriculum.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.caption("Ask questions strictly based on this module. Our verification guard provides focused, grounded answers.")

    if 'doubt_answer' not in st.session_state:
        st.session_state.doubt_answer = None
    if 'doubt_question' not in st.session_state:
        st.session_state.doubt_question = ""

    # Quick prompt suggestion chips
    st.markdown("<div style='font-size: 0.78rem; font-weight: 600; color: #64748b; margin-bottom: 0.35rem;'>Suggested Inquiries:</div>", unsafe_allow_html=True)
    chip_col1, chip_col2, chip_col3 = st.columns(3, gap="small")
    with chip_col1:
        if st.button("📌 Core Concepts Summary", use_container_width=True, key=f"chip_1_{current_module_id}"):
            st.session_state.doubt_question = f"What are the core concepts and fundamental rules of {topic_name}?"
            st.rerun()
    with chip_col2:
        if st.button("🔍 Real-World Example", use_container_width=True, key=f"chip_2_{current_module_id}"):
            st.session_state.doubt_question = f"Can you give an intuitive real-world practical example of {topic_name}?"
            st.rerun()
    with chip_col3:
        if st.button("⚡ Key Exam Pitfalls", use_container_width=True, key=f"chip_3_{current_module_id}"):
            st.session_state.doubt_question = f"What are the most common misconceptions or exam pitfalls regarding {topic_name}?"
            st.rerun()

    with st.form(key=f"doubt_form_{current_module_id}", clear_on_submit=False):
        doubt_question = st.text_area(
            "Your question:",
            value=st.session_state.doubt_question,
            placeholder="e.g., Can you clarify the difference between mutable and immutable data structures in this context?",
            max_chars=500,
            height=95,
            label_visibility="collapsed"
        )
        col_sub, col_clr = st.columns([2, 1])
        with col_sub:
            submit_doubt = st.form_submit_button("Ask Doubt", type="primary", use_container_width=True)
        with col_clr:
            clear_doubt = st.form_submit_button("Clear", use_container_width=True)

    if clear_doubt:
        st.session_state.doubt_answer = None
        st.session_state.doubt_question = ""
        st.rerun()

    if submit_doubt:
        if not doubt_question or len(doubt_question.strip()) < 5:
            show_warning("Please enter a question with at least 5 characters.")
        else:
            try:
                from services.doubt_service import doubt_service
                with st.spinner("Analyzing question within module context..."):
                    ans_result = doubt_service.ask_doubt(
                        module_id=current_module_id,
                        question=doubt_question
                    )
                st.session_state.doubt_answer = ans_result
                st.session_state.doubt_question = doubt_question
            except Exception as e:
                handle_api_error(e, "Doubt submission")

    if st.session_state.doubt_answer:
        answer_data = st.session_state.doubt_answer
        in_scope = answer_data.get('in_scope', False)
        answer = answer_data.get('answer', '')
        with st.container(border=True):
            if in_scope:
                st.markdown("##### ✅ In-Scope Clarification")
                st.markdown(answer)
            else:
                st.markdown("##### ⚠️ Out of Scope Boundary")
                st.markdown(answer)


# ========================================
# STANDARDIZED BOTTOM NAVIGATION DECK
# ========================================
curr_idx = order - 1
has_prev = curr_idx > 0
has_next = curr_idx < len(modules) - 1

col_nav_a, col_nav_b, col_nav_c, col_nav_d = st.columns([1.2, 1, 1, 1.5], gap="small")

with col_nav_a:
    if st.button("Roadmap Overview", use_container_width=True, key="btn_back_to_roadmap"):
        st.switch_page("pages/2_🗺️_Roadmap.py")

with col_nav_b:
    if st.button("Previous Module", disabled=not has_prev, use_container_width=True, key="btn_prev_mod"):
        if has_prev:
            prev_mod = modules[curr_idx - 1]
            st.session_state.current_module_id = prev_mod.get('module_id')
            st.session_state.current_module = prev_mod
            st.session_state.doubt_answer = None
            st.session_state.doubt_question = ""
            st.rerun()

with col_nav_c:
    if st.button("Next Module", disabled=not has_next, use_container_width=True, key="btn_next_mod"):
        if has_next:
            next_mod = modules[curr_idx + 1]
            st.session_state.current_module_id = next_mod.get('module_id')
            st.session_state.current_module = next_mod
            st.session_state.doubt_answer = None
            st.session_state.doubt_question = ""
            st.rerun()

with col_nav_d:
    if st.button("Take Module Quiz", type="primary", use_container_width=True, key="btn_to_quiz"):
        st.switch_page("pages/4_🧪_Quiz.py")
