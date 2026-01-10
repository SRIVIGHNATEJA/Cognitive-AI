"""
Quiz page - Take quizzes to test knowledge.

Allows users to generate and take quizzes for each module in their learning roadmap.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from services.quiz_service import quiz_service
from utils.formatters import format_hours
from components.loading_spinner import with_loading
from components.error_display import (
    show_error, show_success, show_info, show_warning,
    handle_api_error, display_session_messages
)

# Page configuration
st.set_page_config(
    page_title="Quiz",
    page_icon="🧪",
    layout=config.LAYOUT
)

st.title("🧪 Module Quiz")

st.markdown("""
Test your knowledge with quizzes for each module in your learning roadmap.
""")

# Display any session messages
display_session_messages()

# Check if roadmap exists
if not st.session_state.get('roadmap'):
    show_warning("No roadmap found. Please generate a roadmap first.")
    if st.button("Go to Roadmap Page", type="primary"):
        st.switch_page("pages/2_🗺️_Roadmap.py")
    st.stop()

# Check if module is selected
if not st.session_state.get('current_module_id'):
    show_warning("No module selected. Please select a module from Roadmap or Content page.")
    if st.button("Go to Roadmap Page", type="primary"):
        st.switch_page("pages/2_🗺️_Roadmap.py")
    st.stop()

# Get roadmap data
roadmap = st.session_state.roadmap
modules = roadmap.get('modules', [])
mode = roadmap.get('mode', 'unknown')

if not modules:
    show_error("No modules found in roadmap.")
    st.stop()

# Module selection
st.subheader("Select Module")

# Build module options for dropdown
module_options = {
    f"{m.get('order')}. {m.get('topic_name')}": m.get('module_id')
    for m in modules
}

# Pre-select current module if set
current_module_id = st.session_state.get('current_module_id')
default_index = 0

if current_module_id:
    # Find index of current module
    for idx, (label, mod_id) in enumerate(module_options.items()):
        if mod_id == current_module_id:
            default_index = idx
            break

# Module selector dropdown
selected_label = st.selectbox(
    "Choose a module:",
    options=list(module_options.keys()),
    index=default_index,
    help="Select a module to take a quiz"
)

selected_module_id = module_options[selected_label]

# Update session state if module changed
if selected_module_id != st.session_state.get('current_module_id'):
    st.session_state.current_module_id = selected_module_id
    # Find and store full module object
    for module in modules:
        if module.get('module_id') == selected_module_id:
            st.session_state.current_module = module
            break
    # Clear quiz state when module changes
    st.session_state.quiz_answers = {}
    st.session_state.quiz_start_time = None
    st.session_state.quiz_submitted = False
    st.session_state.quiz_evaluated = False

# Get current module details
current_module = st.session_state.get('current_module', {})
topic_name = current_module.get('topic_name', 'Unknown')
estimated_hours = current_module.get('estimated_hours', 0)
order = current_module.get('order', 0)
prerequisites = current_module.get('prerequisites', [])

# Display module info
st.divider()

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown(f"### {order}. {topic_name}")
    
    if prerequisites:
        # Build module_id -> topic_name mapping
        module_id_to_name = {
            m.get('module_id'): m.get('topic_name', 'Unknown')
            for m in modules
        }
        prereq_names = [module_id_to_name.get(p, p) for p in prerequisites]
        st.caption(f"**Prerequisites:** {', '.join(prereq_names)}")
    else:
        st.caption("**Prerequisites:** None")

with col2:
    # Only show time in timed mode
    if mode != 'untimed':
        st.metric("Time", format_hours(estimated_hours))

st.divider()

# Initialize quiz cache in session state
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

# Check if quiz exists for this module
cached_quiz = st.session_state.quiz_cache.get(selected_module_id)

# Check if quiz is already submitted
quiz_submitted = st.session_state.get('quiz_submitted', False)

# Check if quiz is already evaluated
quiz_evaluated = st.session_state.get('quiz_evaluated', False)

# If quiz is evaluated, show results
if quiz_evaluated and cached_quiz and cached_quiz.get('evaluation'):
    st.subheader("Quiz Results")
    
    evaluation = cached_quiz['evaluation']
    
    # Display score
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Score", f"{evaluation.get('score', 0)}/5")
    
    with col2:
        st.metric("Accuracy", f"{evaluation.get('accuracy', 0):.1f}%")
    
    with col3:
        time_taken = evaluation.get('time_taken_seconds', 0)
        minutes = time_taken // 60
        seconds = time_taken % 60
        st.metric("Time Taken", f"{minutes}m {seconds}s")
    
    with col4:
        correct = evaluation.get('correct_answers_count', 0)
        incorrect = evaluation.get('incorrect_answers_count', 0)
        st.metric("Correct/Incorrect", f"{correct}/{incorrect}")
    
    # Time limit exceeded warning
    if evaluation.get('time_limit_exceeded'):
        st.warning("⏰ Time limit exceeded! Your score may be affected.")
    
    # Show if evaluation was cached
    if evaluation.get('cached'):
        st.info("📋 Showing cached evaluation results")
    
    st.divider()
    
    # Display detailed results
    st.subheader("Detailed Results")
    
    question_results = evaluation.get('question_results', [])
    
    for result in question_results:
        question_num = result.get('question_number', 0)
        question_text = result.get('question_text', '')
        options = result.get('options', [])
        is_correct = result.get('is_correct', False)
        user_answer = result.get('user_answer', '')
        correct_answer = result.get('correct_answer', '')
        explanation = result.get('explanation', '')
        
        # Display question with result indicator
        if is_correct:
            st.success(f"**Question {question_num}:** {question_text} ✅")
        else:
            st.error(f"**Question {question_num}:** {question_text} ❌")
        
        # Display options
        for option in options:
            if option == correct_answer:
                st.markdown(f"- **{option}** ✓ (Correct answer)")
            elif option == user_answer and not is_correct:
                st.markdown(f"- **{option}** ✗ (Your answer)")
            else:
                st.markdown(f"- {option}")
        
        # Display explanation
        if explanation:
            st.caption(f"💡 {explanation}")
        
        st.divider()
    
    # Navigation buttons
    st.subheader("Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📚 Back to Content", use_container_width=True):
            st.switch_page("pages/3_📚_Content.py")
    
    with col2:
        # Next module button
        current_index = order - 1  # order is 1-based
        is_last = current_index == len(modules) - 1
        
        if st.button("Next Module →", disabled=is_last, use_container_width=True):
            if current_index < len(modules) - 1:
                next_module = modules[current_index + 1]
                st.session_state.current_module_id = next_module.get('module_id')
                st.session_state.current_module = next_module
                # Clear quiz state for new module
                st.session_state.quiz_answers = {}
                st.session_state.quiz_start_time = None
                st.session_state.quiz_submitted = False
                st.session_state.quiz_evaluated = False
                st.rerun()

# If quiz is submitted but not evaluated, show evaluate button
elif quiz_submitted and cached_quiz and not quiz_evaluated:
    st.subheader("Quiz Submitted")
    
    submission = cached_quiz.get('submission', {})
    quiz_data = cached_quiz.get('quiz', {})
    quiz_id = quiz_data.get('quiz_id', '')
    
    st.success("✅ Quiz submitted successfully!")
    
    st.info(f"""
    Your answers have been saved. Click the button below to evaluate your quiz and see your results.
    
    **Submission ID:** {submission.get('submission_id', 'N/A')}
    """)
    
    st.divider()
    
    # Evaluate button
    if st.button("🎯 Evaluate Quiz", type="primary", use_container_width=True):
        try:
            with st.spinner("Evaluating your answers... This may take a moment."):
                evaluation = quiz_service.evaluate_quiz(quiz_id=quiz_id)
            
            # Store evaluation in cache
            st.session_state.quiz_cache[selected_module_id]['evaluation'] = evaluation
            st.session_state.quiz_evaluated = True
            
            score = evaluation.get('score', 0)
            accuracy = evaluation.get('accuracy', 0)
            show_success(f"Quiz evaluated! Score: {score}/5 ({accuracy:.1f}%)")
            st.rerun()
            
        except Exception as e:
            handle_api_error(e, "Quiz evaluation")

# If quiz exists but not submitted, display quiz
elif cached_quiz and not quiz_submitted:
    st.subheader("Quiz")
    
    quiz_data = cached_quiz.get('quiz', {})
    quiz_id = quiz_data.get('quiz_id', '')
    questions = quiz_data.get('questions', [])
    quiz_mode = quiz_data.get('mode', 'untimed')
    time_limit = quiz_data.get('time_limit_seconds')
    
    # Start timer if not started
    if st.session_state.quiz_start_time is None:
        st.session_state.quiz_start_time = datetime.now()
    
    # Display timer for timed mode
    if quiz_mode == 'timed' and time_limit:
        elapsed = (datetime.now() - st.session_state.quiz_start_time).total_seconds()
        remaining = max(0, time_limit - int(elapsed))
        
        minutes = remaining // 60
        seconds = remaining % 60
        
        if remaining > 60:
            st.info(f"⏱️ Time remaining: {int(minutes)} minutes {int(seconds)} seconds")
        elif remaining > 0:
            st.warning(f"⏱️ Time remaining: {int(seconds)} seconds")
        else:
            st.error("⏰ Time's up!")
    
    st.info(f"📝 Answer all 5 questions and click Submit when ready.")
    
    st.divider()
    
    # Display questions
    for question in questions:
        question_num = question.get('question_number', 0)
        question_text = question.get('question_text', '')
        options = question.get('options', [])
        
        st.markdown(f"**Question {question_num}:** {question_text}")
        
        # Radio button for answer selection
        selected_option = st.radio(
            f"Select your answer for Question {question_num}:",
            options=options,
            key=f"q_{question_num}",
            index=None,
            label_visibility="collapsed"
        )
        
        # Store answer in session state
        if selected_option:
            st.session_state.quiz_answers[question_num] = selected_option
        
        st.divider()
    
    # Submit button
    all_answered = len(st.session_state.quiz_answers) == 5
    
    if not all_answered:
        st.warning(f"⚠️ Please answer all questions. ({len(st.session_state.quiz_answers)}/5 answered)")
    
    if st.button("✅ Submit Answers", type="primary", disabled=not all_answered, use_container_width=True):
        # Calculate time taken
        time_taken = int((datetime.now() - st.session_state.quiz_start_time).total_seconds())
        
        # Submit quiz (no evaluation yet)
        try:
            with st.spinner("Submitting your answers..."):
                submission = quiz_service.submit_quiz(
                    module_id=selected_module_id,
                    quiz_id=quiz_id,
                    answers=st.session_state.quiz_answers,
                    time_taken_seconds=time_taken
                )
            
            # Store submission in cache
            st.session_state.quiz_cache[selected_module_id]['submission'] = submission
            st.session_state.quiz_submitted = True
            
            show_success("Answers submitted successfully! Click 'Evaluate Quiz' to see your results.")
            st.rerun()
            
        except Exception as e:
            handle_api_error(e, "Quiz submission")

# If no quiz exists, show generate button
else:
    st.subheader("Generate Quiz")
    
    st.info("No quiz generated yet for this module.")
    
    # Determine quiz mode based on roadmap mode
    quiz_mode = mode
    time_limit = None
    
    if quiz_mode == 'timed':
        st.markdown("**Quiz Mode:** Timed")
        # Default time limit: 10 minutes (600 seconds)
        time_limit = 600
        st.caption(f"⏱️ Time limit: {time_limit // 60} minutes")
    else:
        st.markdown("**Quiz Mode:** Untimed")
        st.caption("⏱️ No time limit - take your time!")
    
    if st.button("🚀 Generate Quiz", type="primary", use_container_width=True):
        
        def generate():
            """Generate quiz from backend."""
            return quiz_service.generate_quiz(
                module_id=selected_module_id,
                mode=quiz_mode,
                time_limit_seconds=time_limit
            )
        
        # Execute with loading indicator
        try:
            result = with_loading(
                generate,
                loading_message="Generating quiz...",
                info_message="⏳ This may take up to 30 seconds. Please wait..."
            )
            
            if result:
                # Cache quiz in session
                st.session_state.quiz_cache[selected_module_id] = {
                    'quiz': result,
                    'results': None
                }
                
                # Reset quiz state
                st.session_state.quiz_answers = {}
                st.session_state.quiz_start_time = None
                st.session_state.quiz_submitted = False
                st.session_state.quiz_evaluated = False
                
                show_success("Quiz generated successfully! 5 questions ready.")
                st.rerun()
                
        except Exception as e:
            handle_api_error(e, "Quiz generation")

# Help section
st.divider()

with st.expander("ℹ️ Help"):
    st.markdown("""
    ### How to use this page
    
    **Taking a Quiz:**
    1. Select a module from the dropdown
    2. Click "Generate Quiz" if not yet created
    3. Wait for generation (up to 30 seconds)
    4. Answer all 5 multiple-choice questions
    5. Click "Submit Answers" when ready
    6. Click "Evaluate Quiz" to see your results
    7. View your score and detailed explanations
    
    **Quiz Format:**
    - 5 multiple-choice questions per module (optimized for performance)
    - 4 options per question
    - Single attempt per module
    - Deferred evaluation (submit first, evaluate when ready)
    
    **Quiz Modes:**
    
    **Timed Mode:**
    - Fixed time limit (10 minutes)
    - Timer displayed during quiz
    - Time limit enforced
    
    **Untimed Mode:**
    - No time limit
    - Take as long as you need
    - Focus on understanding
    
    ### Evaluation Process
    
    The quiz uses a two-step process:
    1. **Submit Answers** - Your answers are saved
    2. **Evaluate Quiz** - AI evaluates your answers and generates explanations
    
    This allows you to submit answers quickly and evaluate when ready.
    
    ### Results
    
    After evaluation, you'll see:
    - Overall score (out of 5)
    - Accuracy percentage
    - Time taken
    - Correct/incorrect count
    - Detailed per-question results
    - AI-generated explanations for each answer
    
    ### Navigation
    
    - Click "Back to Content" to review notes
    - Click "Next Module" to proceed to next module
    - Quiz results are saved permanently
    
    ### Tips
    
    - Review notes before taking quiz
    - Read questions carefully
    - All questions must be answered before submission
    - You cannot retake a quiz once submitted
    - Evaluation may take a few seconds (AI processing)
    - Use explanations to learn from mistakes
    """)
