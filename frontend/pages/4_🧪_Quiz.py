"""
Quiz page - Take quizzes to test knowledge.

Allows users to generate and take quizzes for each module in their learning roadmap.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from services.quiz_service import quiz_service
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
    page_title="Quiz",
    layout=config.LAYOUT
)

# Ensure session is hydrated on cold page reload
ensure_session_hydrated()

# Render sidebar
render_sidebar()

HELP_TEXT = """
### How to use this page

1. **Select a module:** Click any module chip in the top ribbon to load or generate its assessment.
2. **Quiz Format:**
   - 5 targeted multiple-choice questions per module.
   - Paced or self-paced based on your roadmap configuration.
3. **Submission & Evaluation:**
   - Click **Submit Answers** to record your responses.
   - Click **Evaluate Quiz** to receive automated scoring and rationale for each question.
4. **Retries:**
   - **Retry Quiz:** Re-attempt the same questions to improve your score (instant evaluation).
   - **New Quiz:** Generate 5 fresh questions covering the same module concepts.
"""

# Render clean modern page header with popover help and stage stepper
render_page_header(
    title="Module Assessment & Quiz",
    subtitle="Knowledge checks with automated scoring and detailed conceptual explanations",
    current_stage=4,
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

# ========================================
# MODULE RIBBON SELECTOR
# ========================================
st.markdown("#### Module Navigator")

label_to_mod = {
    f"Module {m.get('order')}: {m.get('topic_name')}": m
    for m in modules
}
options = list(label_to_mod.keys())

current_label = options[0]
for lbl, m in label_to_mod.items():
    if m.get('module_id') == current_module_id:
        current_label = lbl
        break

# Synchronize pill widget state whenever current_module_id changes externally
if current_label and st.session_state.get("quiz_module_pills") != current_label:
    st.session_state["quiz_module_pills"] = current_label

def on_quiz_module_pill_change():
    chosen_label = st.session_state.get("quiz_module_pills")
    if chosen_label and chosen_label in label_to_mod:
        chosen_mod = label_to_mod[chosen_label]
        st.session_state.current_module_id = chosen_mod.get('module_id')
        st.session_state.current_module = chosen_mod
        # Reset quiz state when module changes
        st.session_state.quiz_answers = {}
        st.session_state.quiz_start_time = None
        st.session_state.quiz_submitted = False
        st.session_state.quiz_evaluated = False
        st.session_state.quiz_attempt_number = 1

st.pills(
    "Modules:",
    options=options,
    label_visibility="collapsed",
    key="quiz_module_pills",
    on_change=on_quiz_module_pill_change
)

current_module = st.session_state.get('current_module', modules[0])
topic_name = current_module.get('topic_name', 'Unknown')
estimated_hours = current_module.get('estimated_hours', 0)
order = current_module.get('order', 1)

# Current Module Header Card
with st.container(border=True):
    col_q1, col_q2 = st.columns([3, 1], vertical_alignment="center")
    with col_q1:
        st.markdown(f"### Assessment: **Module {order} ({topic_name})**")
        st.caption("5 multiple-choice questions evaluating conceptual comprehension")
    with col_q2:
        if mode == 'timed':
            st.metric("Allocated Time", format_hours(estimated_hours))
        else:
            st.metric("Position", f"Module {order} of {len(modules)}")

# Initialize session caches
if 'quiz_cache' not in st.session_state:
    st.session_state.quiz_cache = {}
if 'quiz_answers' not in st.session_state:
    st.session_state.quiz_answers = {}
if 'quiz_start_time' not in st.session_state:
    st.session_state.quiz_start_time = None
if 'quiz_submitted' not in st.session_state:
    st.session_state.quiz_submitted = False
if 'quiz_evaluated' not in st.session_state:
    st.session_state.quiz_evaluated = False
if 'quiz_attempt_number' not in st.session_state:
    st.session_state.quiz_attempt_number = 1

cached_quiz = st.session_state.quiz_cache.get(current_module_id)
quiz_submitted = st.session_state.get('quiz_submitted', False)
quiz_evaluated = st.session_state.get('quiz_evaluated', False)

# =========================================================================
# STATE 1: EVALUATED RESULTS & DETAILED REVIEW
# =========================================================================
if quiz_evaluated and cached_quiz and cached_quiz.get('evaluation'):
    evaluation = cached_quiz['evaluation']
    attempt_num = evaluation.get('attempt_number', 1)
    quiz_id = cached_quiz['quiz']['quiz_id']
    score = evaluation.get('score', 0)
    accuracy = evaluation.get('accuracy', 0.0)
    time_taken = evaluation.get('time_taken_seconds', 0)
    correct = evaluation.get('correct_answers_count', 0)
    incorrect = evaluation.get('incorrect_answers_count', 0)

    with st.container(border=True):
        st.markdown(f"### Assessment Performance (Attempt #{attempt_num})")
        st.caption(f"Quiz Reference: `{quiz_id[:20]}...`")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            delta_score = score - 3
            st.metric("Final Score", f"{score}/5", delta=f"{delta_score:+d} vs pass mark" if delta_score != 0 else "Pass mark met")
        with c2:
            st.metric("Accuracy Rate", f"{accuracy:.1f}%")
        with c3:
            mins = time_taken // 60
            secs = time_taken % 60
            st.metric("Duration", f"{mins}m {secs}s")
        with c4:
            st.metric("Correct / Incorrect", f"{correct} / {incorrect}")

        if accuracy >= 80:
            st.success("Target reached: Proficient comprehension demonstrated.")
        elif accuracy >= 60:
            st.info("Passing score achieved: Review incorrect answers below for complete clarity.")
        else:
            st.warning("Review suggested: Re-read the module study notes and attempt a retry.")

    # Embedded Analytics
    try:
        import requests
        resp = requests.get(f"{config.BACKEND_URL}/api/analytics/quiz/{quiz_id}/attempts", timeout=4)
        if resp.status_code == 200:
            adata = resp.json()
            attempts = adata.get('attempts', [])
            if len(attempts) > 1:
                with st.container(border=True):
                    st.markdown("#### Attempt History & Progress")
                    imp = adata.get('improvement_rate')
                    if imp is not None:
                        st.caption(f"Score improvement from first attempt: **{imp:+.1f}%**")
                    table_rows = [
                        {"Attempt": a["attempt_number"], "Score": f"{a['score']}/5", "Accuracy": f"{a['accuracy']:.1f}%", "Duration": f"{a['time_taken_seconds']}s"}
                        for a in attempts
                    ]
                    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    except Exception:
        pass

    # Question Breakdown
    st.markdown("### Question Review & Explanations")
    question_results = evaluation.get('question_results', [])
    for qres in question_results:
        q_num = qres.get('question_number', 0)
        q_txt = qres.get('question_text', '')
        q_opts = qres.get('options', [])
        is_corr = qres.get('is_correct', False)
        usr_ans = qres.get('user_answer', '')
        corr_ans = qres.get('correct_answer', '')
        expl = qres.get('explanation', '')

        with st.container(border=True):
            status_text = "[Correct]" if is_corr else "[Incorrect]"
            st.markdown(f"**Question {q_num}:** {q_txt} — `{status_text}`")

            for opt in q_opts:
                if opt == corr_ans:
                    st.markdown(f"- **{opt}** *(Correct Answer)*")
                elif opt == usr_ans and not is_corr:
                    st.markdown(f"- **{opt}** *(Your Response)*")
                else:
                    st.markdown(f"- {opt}")

            if expl:
                st.caption(f"**Explanation:** {expl}")

    # Navigation Actions after Evaluation
    st.markdown("---")
    curr_idx = order - 1
    has_next = curr_idx < len(modules) - 1

    col_res1, col_res2, col_res3, col_res4 = st.columns([1, 1, 1, 1.4], gap="small")
    with col_res1:
        if st.button("Review Notes", use_container_width=True, key="btn_eval_review_notes"):
            st.switch_page("pages/3_📚_Content.py")
    with col_res2:
        if st.button("Retry Quiz", use_container_width=True, help="Re-attempt the same questions", key="btn_eval_retry"):
            try:
                with st.spinner("Preparing retry attempt..."):
                    ret_res = quiz_service.retry_quiz(quiz_id=cached_quiz['quiz']['quiz_id'])
                new_att = ret_res.get('attempt_number', attempt_num + 1)
                st.session_state.quiz_cache[current_module_id] = {
                    'quiz': ret_res,
                    'submission': None,
                    'evaluation': None
                }
                st.session_state.quiz_answers = {}
                st.session_state.quiz_start_time = None
                st.session_state.quiz_submitted = False
                st.session_state.quiz_evaluated = False
                st.session_state.quiz_attempt_number = new_att
                st.rerun()
            except Exception as e:
                handle_api_error(e, "Quiz retry")
    with col_res3:
        if st.button("New Quiz", use_container_width=True, help="Generate fresh questions", key="btn_eval_new"):
            try:
                with st.spinner("Generating fresh quiz questions..."):
                    q_mode = mode
                    t_limit = 600 if q_mode == 'timed' else None
                    new_q = quiz_service.generate_quiz(module_id=current_module_id, mode=q_mode, time_limit_seconds=t_limit)
                st.session_state.quiz_cache[current_module_id] = {
                    'quiz': new_q,
                    'submission': None,
                    'evaluation': None
                }
                st.session_state.quiz_answers = {}
                st.session_state.quiz_start_time = None
                st.session_state.quiz_submitted = False
                st.session_state.quiz_evaluated = False
                st.session_state.quiz_attempt_number = 1
                st.rerun()
            except Exception as e:
                handle_api_error(e, "New quiz generation")
    with col_res4:
        if has_next:
            if st.button("Next Module", type="primary", use_container_width=True, key="btn_eval_next_mod"):
                nxt = modules[curr_idx + 1]
                st.session_state.current_module_id = nxt.get('module_id')
                st.session_state.current_module = nxt
                st.session_state.quiz_answers = {}
                st.session_state.quiz_start_time = None
                st.session_state.quiz_submitted = False
                st.session_state.quiz_evaluated = False
                st.session_state.quiz_attempt_number = 1
                st.switch_page("pages/3_📚_Content.py")
        else:
            if st.button("Curriculum Overview", type="primary", use_container_width=True, key="btn_eval_roadmap"):
                st.switch_page("pages/2_🗺️_Roadmap.py")


# =========================================================================
# STATE 2: SUBMITTED (WAITING EVALUATION)
# =========================================================================
elif quiz_submitted and cached_quiz and not quiz_evaluated:
    with st.container(border=True):
        st.markdown("### Quiz Answers Saved")
        st.caption("Your responses have been recorded. Click below to begin automated evaluation.")
        
        quiz_data = cached_quiz.get('quiz', {})
        q_id = quiz_data.get('quiz_id', '')

        if st.button("Evaluate Quiz Now", type="primary", use_container_width=True, key=f"btn_eval_now_{current_module_id}_{q_id}"):
            try:
                att_num = st.session_state.get('quiz_attempt_number', 1)
                with st.spinner("Evaluating responses and generating explanations..."):
                    eval_res = quiz_service.evaluate_quiz(quiz_id=q_id, attempt_number=att_num)
                st.session_state.quiz_cache[current_module_id]['evaluation'] = eval_res
                st.session_state.quiz_evaluated = True
                show_success("Quiz evaluated successfully.")
                st.rerun()
            except Exception as e:
                handle_api_error(e, "Quiz evaluation")


# =========================================================================
# STATE 3: READY TO TAKE QUIZ (ACTIVE QUESTIONS)
# =========================================================================
elif cached_quiz and not quiz_submitted:
    quiz_data = cached_quiz.get('quiz', {})
    q_id = quiz_data.get('quiz_id', '')
    questions = quiz_data.get('questions', [])
    q_mode = quiz_data.get('mode', 'untimed')
    time_limit = quiz_data.get('time_limit_seconds')

    if st.session_state.quiz_start_time is None:
        st.session_state.quiz_start_time = datetime.now()

    if q_mode == 'timed' and time_limit:
        elapsed = (datetime.now() - st.session_state.quiz_start_time).total_seconds()
        remaining = max(0, time_limit - int(elapsed))
        st.info(f"Time Remaining: {int(remaining // 60)}m {int(remaining % 60)}s")

    st.markdown("### Answer All 5 Questions")

    for q in questions:
        q_num = q.get('question_number', 1)
        q_text = q.get('question_text', '')
        q_options = q.get('options', [])

        with st.container(border=True):
            st.markdown(f"**Question {q_num}:** {q_text}")
            sel = st.radio(
                f"Question {q_num} options:",
                options=q_options,
                key=f"q_{q_num}",
                index=None,
                label_visibility="collapsed"
            )
            if sel:
                st.session_state.quiz_answers[q_num] = sel

    all_done = len(st.session_state.quiz_answers) == len(questions)
    if not all_done:
        st.caption(f"Progress: {len(st.session_state.quiz_answers)} of {len(questions)} answered")

    col_sub_a, col_sub_b = st.columns([1, 2], gap="medium")
    with col_sub_a:
        if st.button("Back to Study Notes", use_container_width=True, key="btn_quiz_back_notes"):
            st.switch_page("pages/3_📚_Content.py")
    with col_sub_b:
        if st.button("Submit Answers", type="primary", disabled=not all_done, use_container_width=True, key=f"btn_submit_answers_{current_module_id}_{q_id}"):
            time_taken = int((datetime.now() - st.session_state.quiz_start_time).total_seconds())
            try:
                att_num = st.session_state.get('quiz_attempt_number', 1)
                with st.spinner("Submitting responses..."):
                    sub_res = quiz_service.submit_quiz(
                        module_id=current_module_id,
                        quiz_id=q_id,
                        answers=st.session_state.quiz_answers,
                        time_taken_seconds=time_taken,
                        attempt_number=att_num
                    )
                st.session_state.quiz_cache[current_module_id]['submission'] = sub_res
                st.session_state.quiz_submitted = True
                st.rerun()
            except Exception as e:
                handle_api_error(e, "Quiz submission")


# =========================================================================
# STATE 4: NO QUIZ YET (SHOW GENERATION CARD)
# =========================================================================
else:
    with st.container(border=True):
        st.markdown(f"### Knowledge Assessment for **{topic_name}**")
        st.caption("Generate a 5-question multiple choice assessment tailored to this module's topics.")

        col_g1, col_g2 = st.columns([1, 2], gap="medium", vertical_alignment="center")
        with col_g1:
            if st.button("Review Notes First", use_container_width=True, key="btn_gen_back_notes"):
                st.switch_page("pages/3_📚_Content.py")
        with col_g2:
            if st.button("Generate Module Quiz (5 Questions)", type="primary", use_container_width=True, key=f"btn_gen_quiz_{current_module_id}"):
                def gen_quiz_action():
                    q_mode = mode
                    t_limit = 600 if q_mode == 'timed' else None
                    return quiz_service.generate_quiz(
                        module_id=current_module_id,
                        mode=q_mode,
                        time_limit_seconds=t_limit
                    )

                try:
                    result = with_loading(
                        gen_quiz_action,
                        loading_message="Generating questions from module content...",
                        info_message="Structuring 5 multiple-choice questions..."
                    )
                    if result:
                        st.session_state.quiz_cache[current_module_id] = {
                            'quiz': result,
                            'submission': None,
                            'evaluation': None
                        }
                        st.session_state.quiz_answers = {}
                        st.session_state.quiz_start_time = None
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_evaluated = False
                        st.session_state.quiz_attempt_number = 1
                        st.rerun()
                except Exception as e:
                    handle_api_error(e, "Quiz generation")

    render_bottom_nav(
        prev_label="Study Materials",
        prev_page="pages/3_📚_Content.py"
    )
