# ✅ Main Streamlit application

"""
app.py
Streamlit front-end for SkillBridge MVP.

- Runs entirely in a single process (Streamlit).
- Uses agent_core.Interviewer, Evaluator, Coach.
- Saves per-turn logs to logs/session_logs.json.
- Provides:
    - Start/Reset session controls
    - Chat-like interface for questions & answers
    - Clarification loop
    - Right column with realtime evaluation & coach feedback
    - Session Report tab with history & simple average score
    - Professional UI with custom theme and animations

How to run:
    streamlit run app.py
"""

import os
import json
import time
from typing import Dict, Any, List

import streamlit as st

# Load environment variables from .env file (for GEMINI_API_KEY)
from dotenv import load_dotenv
load_dotenv()

# Import agents from your agent_core.py
from agent_core import Interviewer, Evaluator, Coach

# ---------------------------
# MUST BE FIRST: Page Config
# ---------------------------
st.set_page_config(page_title="SkillBridge", layout="wide", initial_sidebar_state="expanded")

# Safe wrapper for streamlit.experimental_rerun() which may not exist in
# all streamlit versions or environments (avoid AttributeError during tests).
def _safe_rerun() -> None:
    try:
        rerun = getattr(st, "experimental_rerun", None)
        if callable(rerun):
            rerun()
    except Exception:
        # swallow to keep the app usable in environments without experimental API
        return

# ---------------------------
# Inject Custom CSS & Styling
# ---------------------------
def inject_custom_css():
    """Inject professional custom CSS for enhanced UI."""
    st.markdown("""
    <style>
        /* Main header with gradient */
        .main-header {
            background: linear-gradient(135deg, #2E5BFF 0%, #8B5CF6 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(46, 91, 255, 0.3);
            animation: fadeIn 0.8s ease-in;
        }
        
        .main-header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
        }
        
        .main-header .tagline {
            font-size: 1.2rem;
            margin-top: 0.5rem;
            opacity: 0.95;
            font-weight: 500;
        }
        
        .main-header .subtext {
            font-size: 0.95rem;
            opacity: 0.85;
            margin-top: 0.5rem;
        }
        
        /* Feedback cards */
        .feedback-card {
            background: linear-gradient(135deg, rgba(46, 91, 255, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%);
            border-left: 4px solid #2E5BFF;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(46, 91, 255, 0.1);
            transition: all 0.3s ease;
            animation: slideIn 0.5s ease-out;
        }
        
        .feedback-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(46, 91, 255, 0.2);
        }
        
        .feedback-card.success {
            border-left-color: #00D084;
            background: linear-gradient(135deg, rgba(0, 208, 132, 0.1) 0%, rgba(0, 208, 132, 0.05) 100%);
        }
        
        .feedback-card.warning {
            border-left-color: #FF9F1C;
            background: linear-gradient(135deg, rgba(255, 159, 28, 0.1) 0%, rgba(255, 159, 28, 0.05) 100%);
        }
        
        /* Score badges */
        .score-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: 600;
            font-size: 0.9rem;
            animation: fadeIn 0.5s ease-in;
        }
        
        .score-excellent {
            background: linear-gradient(135deg, #00D084 0%, #00B570 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(0, 208, 132, 0.3);
        }
        
        .score-good {
            background: linear-gradient(135deg, #2E5BFF 0%, #1e40af 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(46, 91, 255, 0.3);
        }
        
        .score-needs-work {
            background: linear-gradient(135deg, #FF9F1C 0%, #f97316 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(255, 159, 28, 0.3);
        }
        
        /* Progress bars */
        .skill-progress {
            background: rgba(0, 0, 0, 0.1);
            border-radius: 10px;
            height: 12px;
            overflow: hidden;
            margin: 0.5rem 0;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .skill-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #2E5BFF 0%, #8B5CF6 100%);
            border-radius: 10px;
            transition: width 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        
        /* Welcome card */
        .welcome-card {
            background: linear-gradient(135deg, rgba(46, 91, 255, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
            border: 2px solid rgba(46, 91, 255, 0.2);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
        }
        
        .welcome-card h2 {
            color: #2E5BFF;
            margin-top: 0;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-top: 1.5rem;
        }
        
        .stat-item {
            background: rgba(46, 91, 255, 0.08);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(46, 91, 255, 0.15);
            transition: all 0.3s ease;
        }
        
        .stat-item:hover {
            background: rgba(46, 91, 255, 0.12);
            transform: translateY(-3px);
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: #2E5BFF;
            margin: 0.5rem 0;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.7);
        }
        
        /* Performance metrics */
        .performance-metric {
            margin: 1rem 0;
            padding: 0.75rem;
            background: rgba(46, 91, 255, 0.05);
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        
        .performance-metric:hover {
            background: rgba(46, 91, 255, 0.1);
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            font-weight: 600;
            flex: 1;
        }
        
        /* Animations */
        @keyframes fadeIn {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        /* Chat history styling */
        .chat-message {
            padding: 1rem;
            margin: 0.75rem 0;
            border-radius: 10px;
            background: rgba(46, 91, 255, 0.05);
            border-left: 3px solid #2E5BFF;
            animation: slideInLeft 0.4s ease-out;
        }
        
        .chat-message.question {
            border-left-color: #2E5BFF;
        }
        
        .chat-message.answer {
            border-left-color: #8B5CF6;
            margin-left: 1rem;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #2E5BFF 0%, #8B5CF6 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.75rem 2rem !important;
            border-radius: 25px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(46, 91, 255, 0.3) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(46, 91, 255, 0.4) !important;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background: rgba(46, 91, 255, 0.05) !important;
            border-radius: 10px !important;
            padding: 1rem !important;
        }
        
        /* Info/Warning/Success boxes */
        .stAlert {
            border-radius: 12px !important;
            padding: 1rem !important;
        }
        
        /* Welcome card styling */
        .welcome-card {
            background: rgba(46, 91, 255, 0.08);
            border: 2px solid rgba(46, 91, 255, 0.2);
            border-radius: 15px;
            padding: 2rem;
            margin: 1rem 0;
            animation: fadeIn 0.6s ease-in;
        }
        
        .welcome-card h2 {
            color: #2E5BFF;
            margin-top: 0;
            font-size: 1.8rem;
        }
        
        .welcome-card h3 {
            color: #2E5BFF;
            margin-top: 1.5rem;
            font-size: 1.3rem;
        }
        
        .welcome-card p {
            color: #FAFAFA;
            line-height: 1.6;
        }
        
        .welcome-card ol {
            color: #FAFAFA;
        }
        
        .welcome-card li {
            margin: 0.8rem 0;
            color: #FAFAFA;
        }
        
        /* Stats grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin: 1.5rem 0;
        }
        
        .stat-item {
            padding: 1.5rem;
            background: rgba(46, 91, 255, 0.15);
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(46, 91, 255, 0.2);
            transition: all 0.3s ease;
        }
        
        .stat-item:hover {
            background: rgba(46, 91, 255, 0.25);
            transform: translateY(-3px);
        }
        
        .stat-item div:first-child {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: #2E5BFF;
            margin: 0.5rem 0;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #FAFAFA;
            opacity: 0.85;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ---------------------------
# Helper Functions for UI
# ---------------------------
def display_score_visual(score_name: str, score_value: float, max_score: float = 100.0) -> None:
    """Display score as a visual progress bar with color coding."""
    percentage = min((score_value / max_score) * 100, 100)
    
    # Determine badge style based on score
    if percentage >= 75:
        badge_class = "score-excellent"
        emoji = "🌟"
    elif percentage >= 50:
        badge_class = "score-good"
        emoji = "👍"
    else:
        badge_class = "score-needs-work"
        emoji = "💪"
    
    st.markdown(f"""
    <div class="performance-metric">
        <div class="metric-row">
            <span class="metric-label">{emoji} {score_name}</span>
            <span class="score-badge {badge_class}">{score_value:.0f}/{max_score:.0f}</span>
        </div>
        <div class="skill-progress">
            <div class="skill-progress-fill" style="width: {percentage}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def display_welcome_screen() -> None:
    """Display professional welcome screen for new sessions."""
    html_content = """
    <div class="welcome-card">
        <h2>👋 Welcome to SkillsBridge!</h2>
        <p>Your AI-powered interview coach is ready to help you master behavioral and technical interviews with personalized feedback.</p>
        <h3>🚀 How It Works:</h3>
        <ol>
            <li><strong>Answer Questions:</strong> Practice with 150+ carefully curated interview questions</li>
            <li><strong>Get AI Feedback:</strong> Receive instant personalized coaching powered by Gemini AI</li>
            <li><strong>Learn STAR Method:</strong> See ideal answer examples based on your context</li>
            <li><strong>Track Progress:</strong> Monitor your improvement over multiple practice sessions</li>
        </ol>
    </div>
    <div class="welcome-card" style="text-align: center; margin-top: 2rem;">
        <h3>📊 Platform Stats</h3>
        <div class="stats-grid">
            <div class="stat-item">
                <div>❓</div>
                <div class="stat-number">150</div>
                <div class="stat-label">Questions</div>
            </div>
            <div class="stat-item">
                <div>🤖</div>
                <div class="stat-number">3</div>
                <div class="stat-label">AI Agents</div>
            </div>
            <div class="stat-item">
                <div>⚡</div>
                <div class="stat-number">∞</div>
                <div class="stat-label">Attempts</div>
            </div>
        </div>
    </div>
    <div style="margin-top: 2rem; padding: 1.5rem; background: rgba(46, 91, 255, 0.15); border-radius: 8px; border-left: 4px solid #2E5BFF;">
        <strong style="color: #2E5BFF; font-size: 1.05rem;">💡 Pro Tip:</strong> 
        <span style="color: #FAFAFA; margin-left: 0.5rem;">Start with easy questions to warm up, then progress to harder scenarios. The system intelligently adapts to your performance!</span>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# ---------------------------
# Setup paths & ensure folders
# ---------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(ROOT, "logs")
DEMO_DIR = os.path.join(ROOT, "demo_cases")

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DEMO_DIR, exist_ok=True)

SESSION_LOG_FILE = os.path.join(LOGS_DIR, "session_logs.json")

# ---------------------------
# Utilities
# ---------------------------
def load_session_logs() -> List[Dict[str, Any]]:
    if not os.path.exists(SESSION_LOG_FILE):
        return []
    try:
        with open(SESSION_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def append_session_log(entry: Dict[str, Any]):
    logs = load_session_logs()
    logs.append(entry)
    with open(SESSION_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

def reset_app_state():
    # Resets Streamlit session_state keys we use
    keys = [
        "session_active", "user_name", "interviewer", "evaluator", "coach",
        "current_question", "current_question_id", "input_answer",
        "waiting_for_clarification", "clarification_prompt", "last_eval",
        "last_feedback", "history", "last_overall_score"
    ]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]

# ---------------------------
# Initialize UI / Session
# ---------------------------

# Professional header with branding
st.markdown("""
<div class="main-header">
    <h1>🎯 SkillsBridge</h1>
    <div class="tagline">AI-Powered Interview Coaching</div>
    <div class="subtext">💼 Practice • 📊 Analyze • 🚀 Succeed</div>
</div>
""", unsafe_allow_html=True)

# Sidebar controls
with st.sidebar:
    st.header("Session Controls")
    if "session_active" not in st.session_state:
        st.session_state.session_active = False

    if not st.session_state.session_active:
        st.session_state.user_name = st.text_input("Your name (for session):", value="", key="user_name_input")
        start_btn = st.button("Start Session", key="start_btn")
        if start_btn:
            if not st.session_state.user_name.strip():
                st.warning("Please enter a name to start.")
            else:
                # Initialize agents and session_state
                st.session_state.interviewer = Interviewer()
                st.session_state.evaluator = Evaluator()
                st.session_state.coach = Coach()
                st.session_state.current_question = None
                st.session_state.current_question_id = None
                st.session_state.input_answer = ""
                st.session_state.waiting_for_clarification = False
                st.session_state.clarification_prompt = ""
                st.session_state.last_eval = None
                st.session_state.last_feedback = None
                st.session_state.history = []
                st.session_state.session_active = True
                _safe_rerun()
    else:
        st.write(f"**Active session:** {st.session_state.get('user_name', '')}")
        if st.button("Reset Session", key="reset_btn"):
            reset_app_state()
            _safe_rerun()

    st.markdown("---")
    st.checkbox("Debug: show raw diagnostics", key="debug_toggle")
    st.markdown("**Files**")
    st.write("data/questions.json")
    st.write("data/rubric.json")
    st.write("data/coach_templates.json")

# Layout columns: main (chat) and right (feedback + report)
col1, col2 = st.columns([1.8, 1.2], gap="large")

# ---------------------------
# Main column: Chat UI & Flow
# ---------------------------
with col1:
    st.subheader("Interview Chat")
    if not st.session_state.get("session_active"):
        display_welcome_screen()
    else:
        # Show last few turns in chat-like format
        history = st.session_state.get("history", [])
        if history:
            for turn in history[-6:]:
                st.markdown(f"**Q — {turn['question_id']}**: {turn['question_text']}")
                st.markdown(f"> **Your answer:** {turn['answer']}")
                s_val = turn['eval'].get('star_structure', turn['eval'].get('structure'))
                st.markdown(f"> **Score:** {turn['eval']['total']} (C:{turn['eval']['clarity']}, S:{s_val}, R:{turn['eval']['relevance']})")
                st.markdown("---")

        # Button to fetch next question if none active
        if st.session_state.get("current_question") is None:
            if st.button("Get Next Question", key="get_q_btn"):
                interviewer: Interviewer = st.session_state["interviewer"]
                q = interviewer.pick_question(st.session_state)
                st.session_state.current_question = q
                st.session_state.current_question_id = q["id"]
                st.session_state.input_answer = ""
                _safe_rerun()
            else:
                st.info("Click 'Get Next Question' to begin this turn.")
        else:
            q = st.session_state.current_question
            st.markdown(f"### Question ({q['id']}) — {q.get('difficulty', '')}")
            st.write(q["text"])
            with st.form(key="answer_form", clear_on_submit=False):
                ans = st.text_area("Your answer (type and submit):", value=st.session_state.get("input_answer", ""), height=160, key="answer_box")
                submitted = st.form_submit_button("Submit Answer")
                if submitted:
                    st.session_state.input_answer = ans.strip()
                    if not st.session_state.input_answer:
                        st.warning("Please type an answer before submitting.")
                    else:
                        # Evaluate
                        evaluator: Evaluator = st.session_state["evaluator"]
                        eval_result = evaluator.score(q["text"], st.session_state.input_answer)
                        st.session_state.last_eval = eval_result
                        st.session_state.last_feedback = None

                        # If clarification needed -> set flag and show prompt
                        if eval_result.get("clarification_needed"):
                            interviewer: Interviewer = st.session_state["interviewer"]
                            clar = interviewer.ask_clarification(q, st.session_state)
                            st.session_state.waiting_for_clarification = True
                            st.session_state.clarification_prompt = clar
                            # Save minimal turn while waiting? We'll save after final feedback.
                            _safe_rerun()
                        else:
                            # Generate coach feedback and finalize turn
                            coach: Coach = st.session_state["coach"]
                            # Prefer new signature: (question_text, user_answer, evaluation_result, model_answer)
                            try:
                                feedback = coach.generate_feedback(q.get("text") if isinstance(q, dict) else q,
                                                                   st.session_state.input_answer,
                                                                   eval_result,
                                                                   q.get("model_answer", "") if isinstance(q, dict) else "")
                            except TypeError:
                                # Fallback to old signature if coach expects (q, answer, eval)
                                feedback = coach.generate_feedback(q, st.session_state.input_answer, eval_result)
                            st.session_state.last_feedback = feedback

                            # Build turn and append to history & logs
                            turn = {
                                "timestamp": int(time.time()),
                                "user": st.session_state["user_name"],
                                "question_id": q["id"],
                                "question_text": q["text"],
                                "answer": st.session_state["input_answer"],
                                "eval": eval_result,
                                "coach": feedback
                            }
                            st.session_state.history.append(turn)
                            append_session_log(turn)
                            # Update last overall score for adaptive difficulty
                            st.session_state["last_overall_score"] = eval_result.get("total", 0)

                            # Clear current question to allow next
                            st.session_state.current_question = None
                            st.session_state.current_question_id = None
                            st.session_state.input_answer = ""
                            st.session_state.waiting_for_clarification = False
                            st.session_state.clarification_prompt = ""
                            _safe_rerun()

            # Clarification flow UI
            if st.session_state.get("waiting_for_clarification"):
                st.warning("Evaluator requests clarification:")
                st.info(st.session_state.get("clarification_prompt"))
                with st.form(key="clarify_form", clear_on_submit=False):
                    clar_ans = st.text_area("Add your clarification (append to your previous answer):", value="", height=120, key="clar_box")
                    clar_sub = st.form_submit_button("Submit Clarification")
                    if clar_sub:
                        if not clar_ans.strip():
                            st.warning("Please provide a clarification or additional detail.")
                        else:
                            # Append clarification and re-evaluate
                            q = st.session_state.current_question
                            combined = (st.session_state.get("input_answer", "") + " " + clar_ans.strip()).strip()
                            evaluator: Evaluator = st.session_state["evaluator"]
                            eval_result = evaluator.score(q["text"], combined)
                            st.session_state.last_eval = eval_result

                            # Generate coach feedback
                            coach: Coach = st.session_state["coach"]
                            # Prefer new signature but fallback if needed
                            try:
                                feedback = coach.generate_feedback(q.get("text") if isinstance(q, dict) else q,
                                                                   combined,
                                                                   eval_result,
                                                                   q.get("model_answer", "") if isinstance(q, dict) else "")
                            except TypeError:
                                feedback = coach.generate_feedback(q, combined, eval_result)
                            st.session_state.last_feedback = feedback

                            # Build turn and append to history & logs
                            turn = {
                                "timestamp": int(time.time()),
                                "user": st.session_state["user_name"],
                                "question_id": q["id"],
                                "question_text": q["text"],
                                "answer": combined,
                                "eval": eval_result,
                                "coach": feedback
                            }
                            st.session_state.history.append(turn)
                            append_session_log(turn)
                            # Update last overall score for adaptive difficulty
                            st.session_state["last_overall_score"] = eval_result.get("total", 0)

                            # Reset question state
                            st.session_state.current_question = None
                            st.session_state.current_question_id = None
                            st.session_state.input_answer = ""
                            st.session_state.waiting_for_clarification = False
                            st.session_state.clarification_prompt = ""
                            _safe_rerun()

# ---------------------------
# Right column: Feedback & Reports
# ---------------------------
with col2:
    st.subheader("📊 Instant Feedback")
    
    # Add spacing
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    if st.session_state.get("last_eval") is None:
        st.info("💡 Submit an answer to see your personalized feedback and coaching.")
    else:
        eval_result = st.session_state["last_eval"]
        
        # Total score with emoji indicator
        total_score = eval_result.get("total", 0)
        if total_score >= 75:
            emoji = "🌟"
            color = "#00D084"
        elif total_score >= 50:
            emoji = "👍"
            color = "#2E5BFF"
        else:
            emoji = "💪"
            color = "#FF9F1C"
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, {color}20 0%, {color}10 100%); 
                    border-radius: 12px; border: 2px solid {color}40; margin-bottom: 1.5rem; margin-top: 1rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">{emoji}</div>
            <div style="font-size: 2.8rem; font-weight: 700; color: {color}; line-height: 1;">{total_score:.1f}<span style="font-size: 1.5rem; opacity: 0.7;">/100</span></div>
            <div style="font-size: 0.95rem; opacity: 0.75; margin-top: 0.8rem; color: #FAFAFA;">Overall Score</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Visual breakdown of scores
        st.markdown("**📈 Performance Breakdown**")
        st.markdown('<div style="height: 0.3rem;"></div>', unsafe_allow_html=True)
        
        clarity_val = eval_result.get('clarity')
        star_val = eval_result.get('star_structure', eval_result.get('structure'))
        relevance_val = eval_result.get('relevance')
        
        display_score_visual("Clarity", clarity_val)
        display_score_visual("STAR Structure", star_val)
        display_score_visual("Relevance", relevance_val)
        
        # Diagnostics
        if eval_result.get("diagnostics"):
            with st.expander("📋 Detailed Feedback", expanded=True):
                for k, v in eval_result.get("diagnostics", {}).items():
                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

    if st.session_state.get("last_feedback"):
        st.markdown("---")
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        fb = st.session_state["last_feedback"]
        
        st.markdown("**🎓 Coaching & Guidance**")
        
        # Improvement bullet
        st.markdown(f"""
        <div class="feedback-card warning">
            <strong>⚡ Key Improvement Area:</strong><br>{fb.get("improvement_bullet")}
        </div>
        """, unsafe_allow_html=True)
        
        # Practice prompt
        st.markdown(f"""
        <div class="feedback-card">
            <strong>📝 Practice Prompt:</strong><br>{fb.get("practice_prompt")}
        </div>
        """, unsafe_allow_html=True)
        
        # Model answer in code block
        with st.expander("📚 Model Answer Template", expanded=False):
            st.code(fb.get("model_answer"), language="markdown")
        
        # Display personalized coaching if available
        if fb.get("personalized_coaching"):
            # Check if this is a template fallback (starts with standard phrases)
            is_template = fb.get("personalized_coaching", "").startswith("Your answer") or fb.get("personalized_coaching", "").startswith("You provided") or fb.get("personalized_coaching", "").startswith("You covered")
            
            with st.expander("💡 AI-Powered Personalized Coaching", expanded=True):
                if is_template:
                    st.info("ℹ️ Using template feedback (Gemini quota may be exhausted). AI-generated feedback resumes when quota resets.")
                st.markdown(f"""
                <div class="feedback-card success">
                    {fb.get("personalized_coaching")}
                </div>
                """, unsafe_allow_html=True)
        
        # Display ideal answer example
        if fb.get("ideal_answer"):
            # Check if this is a template fallback
            is_template = fb.get("ideal_answer", "").startswith("**Ideal STAR Answer Example:**")
            
            with st.expander("🎯 Ideal Answer Example (Based on Your Context)", expanded=True):
                if is_template:
                    st.info("ℹ️ Showing template answer (Gemini quota exhausted). Personalized examples resume when quota resets.")
                st.markdown(f"""
                <div class="feedback-card success">
                    {fb.get("ideal_answer")}
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="height: 0.8rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header" style="background: linear-gradient(135deg, #2E5BFF 0%, #8B5CF6 100%); padding: 1.2rem; margin: 0;"><h3 style="margin: 0; font-size: 1.2rem;">📊 Session Report</h3></div>', unsafe_allow_html=True)
    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    hist = st.session_state.get("history", [])
    if not hist:
        st.info("📈 No questions answered yet. Start practicing to see your performance!")
    else:
        # Calculate metrics
        avg = sum(t["eval"]["total"] for t in hist) / len(hist)
        excellent_count = sum(1 for t in hist if t["eval"]["total"] >= 75)
        improvement = hist[-1]["eval"]["total"] - hist[0]["eval"]["total"] if len(hist) > 1 else 0
        
        # Display metrics in columns
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        with m_col1:
            st.metric("Average Score", f"{avg:.1f}/100", delta=f"+{improvement:.1f}" if improvement > 0 else f"{improvement:.1f}")
        
        with m_col2:
            st.metric("Questions Attempted", len(hist))
        
        with m_col3:
            st.metric("Excellent Answers", f"{excellent_count} ⭐")
        
        with m_col4:
            latest_score = hist[-1]["eval"]["total"]
            score_status = "🌟" if latest_score >= 75 else ("👍" if latest_score >= 50 else "💪")
            st.metric("Latest Score", f"{latest_score:.1f}/100", label_visibility="collapsed")
            st.markdown(f"<div style='text-align: center;'>{score_status}</div>", unsafe_allow_html=True)
        
        # Show detailed history
        if st.checkbox("📋 Show Full History", key="show_full_turns", value=False):
            st.markdown("<div class='feedback-card'>", unsafe_allow_html=True)
            for idx, t in enumerate(hist, 1):
                score = t["eval"]["total"]
                status_emoji = "🌟" if score >= 75 else ("👍" if score >= 50 else "📝")
                st.markdown(f"""
                **{idx}. {t['question_id']}** {status_emoji}
                - Score: {score:.1f}/100
                - Answer length: {len(t['answer'])} chars
                """)
            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("debug_toggle"):
        st.markdown("---")
        st.subheader("DEBUG: Raw session_state")
        st.write(st.session_state.to_dict())

# ---------------------------
# Footer
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; padding: 1rem; color: #FAFAFA; opacity: 0.8;">
    <strong>🎯 SkillsBridge</strong><br>
    <small>AI-Powered Interview Coach</small><br>
    <small style="font-size: 0.8rem; opacity: 0.7;">Team 12 • CS(AI&DS)</small>
</div>
""", unsafe_allow_html=True)
