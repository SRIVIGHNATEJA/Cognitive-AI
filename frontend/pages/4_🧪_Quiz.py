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
    st.session_state.quiz_attempt_number = 1

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

if 'quiz_attempt_number' not in st.session_state:
    st.session_state.quiz_attempt_number = 1

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
    attempt_num = evaluation.get('attempt_number', 1)
    quiz_id = cached_quiz['quiz']['quiz_id']
    
    # Display quiz info and attempt number
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.caption(f"**Quiz ID:** `{quiz_id}`")
    with col_info2:
        if attempt_num > 1:
            st.caption(f"**Attempt:** {attempt_num}")
        else:
            st.caption(f"**Attempt:** {attempt_num} (First attempt)")
    
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
    
    # === EMBEDDED ANALYTICS SECTION ===
    # Fetch and display attempt analytics if multiple attempts exist
    try:
        import requests
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        
        analytics_response = requests.get(f"{config.BACKEND_URL}/api/analytics/quiz/{quiz_id}/attempts", timeout=5)
        
        if analytics_response.status_code == 200:
            analytics_data = analytics_response.json()
            attempts = analytics_data.get('attempts', [])
            
            # Only show analytics if there are multiple attempts
            if len(attempts) > 1:
                st.subheader("📊 Progress Across Attempts")
                
                # Display improvement rate
                improvement_rate = analytics_data.get('improvement_rate')
                if improvement_rate is not None:
                    if improvement_rate > 0:
                        st.success(f"🎉 Great progress! You improved by **{improvement_rate:.1f}%** from your first attempt!")
                    elif improvement_rate < 0:
                        st.info(f"📚 Your accuracy decreased by {abs(improvement_rate):.1f}%. Review the material and try again!")
                    else:
                        st.info("Your accuracy remained the same. Keep practicing!")
                
                # Attempt history table
                with st.expander("📋 View Attempt History", expanded=False):
                    table_data = []
                    for attempt in attempts:
                        table_data.append({
                            "Attempt": attempt["attempt_number"],
                            "Score": f"{attempt['score']}/5",
                            "Accuracy": f"{attempt['accuracy']:.1f}%",
                            "Time": f"{attempt['time_taken_seconds']}s"
                        })
                    st.dataframe(table_data, use_container_width=True, hide_index=True)
                
                # Score progression graph
                with st.expander("📈 Score Progression", expanded=True):
                    attempt_numbers = [a["attempt_number"] for a in attempts]
                    scores = [a["score"] for a in attempts]
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(attempt_numbers, scores, marker='o', linewidth=2, markersize=8, color='#1f77b4')
                    ax.axhline(y=3, color='green', linestyle='--', alpha=0.5, label='Passing (3/5)')
                    ax.set_xlabel('Attempt Number', fontsize=11)
                    ax.set_ylabel('Score (out of 5)', fontsize=11)
                    ax.set_title('Score Progression', fontsize=12, fontweight='bold')
                    ax.grid(True, alpha=0.3)
                    ax.legend()
                    ax.set_ylim(0, 5.5)
                    ax.set_xticks(attempt_numbers)
                    st.pyplot(fig)
                    plt.close(fig)
                
                # Time progression graph (only if 2+ attempts)
                if len(attempts) >= 2:
                    with st.expander("⏱️ Time Progression", expanded=False):
                        times = [a["time_taken_seconds"] for a in attempts]
                        
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.plot(attempt_numbers, times, marker='s', linewidth=2, markersize=8, color='#ff7f0e')
                        ax.set_xlabel('Attempt Number', fontsize=11)
                        ax.set_ylabel('Time Taken (seconds)', fontsize=11)
                        ax.set_title('Time Progression', fontsize=12, fontweight='bold')
                        ax.grid(True, alpha=0.3)
                        ax.set_xticks(attempt_numbers)
                        st.pyplot(fig)
                        plt.close(fig)
                        
                        # Time improvement message
                        first_time = attempts[0]["time_taken_seconds"]
                        latest_time = attempts[-1]["time_taken_seconds"]
                        time_diff = first_time - latest_time
                        
                        if time_diff > 0:
                            st.success(f"⚡ You're getting faster! Saved {time_diff} seconds from first to latest attempt.")
                        elif time_diff < 0:
                            st.info(f"⏱️ You took {abs(time_diff)} more seconds on the latest attempt (taking time to think is good!).")
                
                st.divider()
    
    except Exception as e:
        # Silently fail - analytics is optional enhancement
        pass
    
    # === END ANALYTICS SECTION ===
    
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
    
    # Ask a Doubt section
    st.subheader("💬 Ask a Doubt")
    
    st.markdown("""
    Have a question about this quiz or module? Ask here for a quick clarification.
    """)
    
    # Initialize doubt state in session for quiz page
    if 'quiz_doubt_answer' not in st.session_state:
        st.session_state.quiz_doubt_answer = None
    if 'quiz_doubt_question' not in st.session_state:
        st.session_state.quiz_doubt_question = ""
    
    # Doubt input form
    with st.form(key=f"quiz_doubt_form_{selected_module_id}", clear_on_submit=False):
        quiz_doubt_question = st.text_area(
            "Your question:",
            value=st.session_state.quiz_doubt_question,
            placeholder="e.g., Why did I get question 3 wrong? Can you explain the concept?",
            help="Ask a specific question about this module's content or quiz",
            max_chars=500,
            height=100
        )
        
        col_submit, col_clear = st.columns([1, 1])
        
        with col_submit:
            submit_quiz_doubt = st.form_submit_button("Submit Question", type="primary", use_container_width=True)
        
        with col_clear:
            clear_quiz_doubt = st.form_submit_button("Clear", use_container_width=True)
    
    # Handle clear button
    if clear_quiz_doubt:
        st.session_state.quiz_doubt_answer = None
        st.session_state.quiz_doubt_question = ""
        st.rerun()
    
    # Handle submit button
    if submit_quiz_doubt:
        if not quiz_doubt_question or len(quiz_doubt_question.strip()) < 5:
            show_warning("Please enter a question (at least 5 characters)")
        else:
            try:
                # Import doubt service
                from services.doubt_service import doubt_service
                
                with st.spinner("Thinking..."):
                    result = doubt_service.ask_doubt(
                        module_id=selected_module_id,
                        question=quiz_doubt_question
                    )
                
                # Store answer in session
                st.session_state.quiz_doubt_answer = result
                st.session_state.quiz_doubt_question = quiz_doubt_question
                
            except Exception as e:
                handle_api_error(e, "Doubt submission")
    
    # Display answer if available
    if st.session_state.quiz_doubt_answer:
        answer_data = st.session_state.quiz_doubt_answer
        in_scope = answer_data.get('in_scope', False)
        answer = answer_data.get('answer', '')
        
        if in_scope:
            st.success("✅ Answer:")
            st.markdown(answer)
        else:
            st.info("ℹ️ Out of Scope:")
            st.markdown(answer)
        
        st.caption("💡 This is a one-time answer. For follow-up questions, please submit a new question.")
    
    st.divider()
    
    # Navigation buttons
    st.subheader("Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📚 Back to Content", use_container_width=True):
            st.switch_page("pages/3_📚_Content.py")
    
    with col2:
        # Retry button - same quiz, new attempt
        if st.button("🔄 Retry Quiz", type="secondary", use_container_width=True, help="Retry with same questions (new attempt)"):
            try:
                with st.spinner("Preparing quiz retry..."):
                    retry_result = quiz_service.retry_quiz(quiz_id=cached_quiz['quiz']['quiz_id'])
                
                # Update cache with new attempt number
                new_attempt = retry_result.get('attempt_number', 1)
                st.session_state.quiz_cache[selected_module_id] = {
                    'quiz': retry_result,
                    'submission': None,
                    'evaluation': None
                }
                
                # Reset quiz state for new attempt
                st.session_state.quiz_answers = {}
                st.session_state.quiz_start_time = None
                st.session_state.quiz_submitted = False
                st.session_state.quiz_evaluated = False
                st.session_state.quiz_attempt_number = new_attempt
                
                show_success(f"Quiz retry initialized! Starting attempt {new_attempt} with same questions.")
                st.rerun()
                
            except Exception as e:
                handle_api_error(e, "Quiz retry")
    
    with col3:
        # New Quiz button - fresh quiz with new questions
        if st.button("✨ New Quiz", type="primary", use_container_width=True, help="Generate new quiz with different questions"):
            try:
                # Determine quiz mode based on roadmap mode
                quiz_mode = mode
                time_limit = None
                
                if quiz_mode == 'timed':
                    time_limit = 600  # 10 minutes
                
                with st.spinner("Generating new quiz..."):
                    result = quiz_service.generate_quiz(
                        module_id=selected_module_id,
                        mode=quiz_mode,
                        time_limit_seconds=time_limit
                    )
                
                # Cache new quiz in session
                st.session_state.quiz_cache[selected_module_id] = {
                    'quiz': result,
                    'submission': None,
                    'evaluation': None
                }
                
                # Reset quiz state for new quiz
                st.session_state.quiz_answers = {}
                st.session_state.quiz_start_time = None
                st.session_state.quiz_submitted = False
                st.session_state.quiz_evaluated = False
                st.session_state.quiz_attempt_number = 1
                
                show_success("New quiz generated successfully! 5 fresh questions ready.")
                st.rerun()
                
            except Exception as e:
                handle_api_error(e, "New quiz generation")
    
    with col4:
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
                st.session_state.quiz_attempt_number = 1
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
            attempt_num = st.session_state.get('quiz_attempt_number', 1)
            with st.spinner("Evaluating your answers... This may take a moment."):
                evaluation = quiz_service.evaluate_quiz(
                    quiz_id=quiz_id,
                    attempt_number=attempt_num
                )
            
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
    attempt_num = st.session_state.get('quiz_attempt_number', 1)
    
    # Display quiz info
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.caption(f"**Quiz ID:** `{quiz_id}`")
    with col_info2:
        if attempt_num > 1:
            st.caption(f"**Attempt:** {attempt_num} (Retry)")
        else:
            st.caption(f"**Attempt:** {attempt_num} (First attempt)")
    
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
            attempt_num = st.session_state.get('quiz_attempt_number', 1)
            with st.spinner("Submitting your answers..."):
                submission = quiz_service.submit_quiz(
                    module_id=selected_module_id,
                    quiz_id=quiz_id,
                    answers=st.session_state.quiz_answers,
                    time_taken_seconds=time_taken,
                    attempt_number=attempt_num
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
                st.session_state.quiz_attempt_number = 1
                
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
    - Multiple attempts supported (retry with same questions)
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
    - Click "Retry Quiz" to retake with **same questions** (new attempt, instant evaluation)
    - Click "New Quiz" to generate **different questions** (fresh quiz, new quiz_id)
    - Click "Next Module" to proceed to next module
    - Quiz results are saved permanently
    - Each retry is tracked as a separate attempt
    
    ### Retry vs New Quiz
    
    **Retry Quiz (🔄):**
    - Same quiz_id, same questions
    - New attempt_number (2, 3, 4...)
    - Instant evaluation (uses cached answers from first attempt)
    - Good for: Improving your score on the same questions
    
    **New Quiz (✨):**
    - New quiz_id, different questions
    - Resets to attempt_number 1
    - First evaluation takes ~45s (generates new answers)
    - Good for: Testing knowledge with fresh questions
    
    ### Tips
    
    - Review notes before taking quiz
    - Read questions carefully
    - All questions must be answered before submission
    - You can retry a quiz multiple times (same questions)
    - Evaluation may take a few seconds (AI processing)
    - Use explanations to learn from mistakes
    - Each retry is a new attempt with fresh answers
    """)
