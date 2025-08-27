import re
import asyncio
import uuid
import streamlit as st
from core.schemas import Candidate, ConversationState, QASet, QAQuestion
from core.state import detect_exit, next_step
from core.qa_generator import generate_stack_questions
from core.answer_scorer import score_answer, calculate_overall_score, simple_score_answer
from core.storage import save_candidate
from core.security import mask_email, mask_phone
from ui.components import sidebar_settings, render_history, append_message

st.set_page_config(page_title="TalentScout Hiring Assistant", layout="centered")

INTAKE_STEPS = [
    "CONSENT",
    "INTAKE_NAME",
    "INTAKE_EMAIL",
    "INTAKE_PHONE",
    "INTAKE_YOE",
    "INTAKE_POSITION",
    "INTAKE_LOCATION",
    "INTAKE_TECH",
]

QUESTIONS = {
    "CONSENT": (
        "Before proceeding, please confirm consent to process your details strictly "
        "for screening purposes. Reply 'I agree' to continue."
    ),
    "INTAKE_NAME": "What's your full name?",
    "INTAKE_EMAIL": "What's your email address?",
    "INTAKE_PHONE": "What's your phone number?",
    "INTAKE_YOE": "How many years of professional experience do you have?",
    "INTAKE_POSITION": "What position(s) are you interested in? (comma-separated if multiple)",
    "INTAKE_LOCATION": "What's your current location?",
    "INTAKE_TECH": "What are your main technical skills/technologies? (comma-separated)",
}

EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RX = re.compile(r"^[+0-9][0-9\s\-().]{5,}$")

def get_next_question(step: str) -> str:
    return QUESTIONS.get(step, "")

def bot_say(text: str) -> None:
    append_message("assistant", text)

def user_say(text: str) -> None:
    append_message("user", text)

def apply_answer_to_step(step: str, text: str) -> bool:
    """
    Apply the user's message to the current intake step.
    Returns True if the answer is accepted and saved; False if validation fails.
    """
    c = st.session_state.candidate
    val = (text or "").strip()

    if step == "CONSENT":
        consent_words = ["agree", "yes", "ok", "proceed", "accept", "confirm"]
        if any(w in val.lower() for w in consent_words):
            c.consent_given = True
            return True
        bot_say("For compliance, please reply 'I agree', 'yes', or 'accept' to proceed, or 'exit' to stop.")
        return False

    if step == "INTAKE_NAME":
        if val and len(val.strip()) >= 2:
            c.full_name = val.strip()
            return True
        bot_say("Please provide your full name (at least 2 characters).")
        return False

    if step == "INTAKE_EMAIL":
        candidate_input = val.strip().strip(",. ").lower()
        if EMAIL_RX.match(candidate_input):
            c.email = candidate_input
            return True
        if ("@" in candidate_input and not EMAIL_RX.match(candidate_input)):
            bot_say(
                f"That looks almost like an email. Did you mean: "
                f"{candidate_input.rstrip('.')+'.com' if candidate_input.endswith('.') else candidate_input}? "
                "Please check for correct spelling and domain (e.g., name@example.com)."
            )
        else:
            bot_say(
                "That doesn't look like a valid email address. Please check punctuation and try again (e.g., name@example.com)."
            )
        return False

    if step == "INTAKE_PHONE":
        cleaned_phone = re.sub(r'[^\d+]', '', val)
        if len(cleaned_phone) >= 6 and (cleaned_phone.startswith('+') or cleaned_phone.isdigit()):
            c.phone = cleaned_phone
            return True
        bot_say("Please provide a valid phone number with country code if possible (e.g., +1234567890 or 1234567890).")
        return False

    if step == "INTAKE_YOE":
        try:
            years = float(val.replace(',', '.'))
            if 0 <= years <= 50:
                c.years_experience = years
                return True
            bot_say("Years of experience should be between 0 and 50 (e.g., 3.5).")
            return False
        except (ValueError, TypeError):
            bot_say("Please provide years of experience as a number (e.g., 3.5).")
            return False

    if step == "INTAKE_POSITION":
        if val and len(val.strip()) >= 2:
            positions = [s.strip() for s in val.split(",") if s.strip()]
            c.desired_positions = positions
            return True
        bot_say("Please provide the position(s) you're interested in.")
        return False

    if step == "INTAKE_LOCATION":
        if val and len(val.strip()) >= 2:
            c.current_location = val.strip()
            return True
        bot_say("Please provide your current location.")
        return False

    if step == "INTAKE_TECH":
        if val and len(val.strip()) >= 2:
            tech_list = [s.strip() for s in val.split(",") if s.strip()]
            c.tech_stack = tech_list
            return True
        bot_say("Please provide your technical skills/technologies (comma-separated).")
        return False

    return False

def handle_technical_answer(text: str) -> bool:
    """Handle answers to technical questions with AI scoring"""
    if not text or len(text.strip()) < 10:
        bot_say("Please provide a more detailed answer (at least 10 characters).")
        return False
    
    # Get current question info
    current_idx = st.session_state.state.current_question_index
    questions = st.session_state.get("generated_questions", [])
    
    if current_idx < len(questions):
        question = questions[current_idx]
        question_id = question.get("question_id", f"q_{current_idx}")
        
        # Save the answer
        st.session_state.candidate.technical_answers[question_id] = text.strip()
        
        # Score the answer using AI
        with st.spinner("🤖 AI is evaluating your answer..."):
            try:
                # Run async scoring
                score_result = asyncio.run(
                    score_answer(
                        question=question["question"],
                        answer=text.strip(),
                        topic=question["topic"],
                        difficulty=question["difficulty"],
                        experience_years=st.session_state.candidate.years_experience or 0
                    )
                )
                
                # Save the score
                st.session_state.candidate.answer_scores[question_id] = score_result
                
                # Show immediate feedback
                score_emoji = "🟢" if score_result.score >= 8 else "🟡" if score_result.score >= 6 else "🔴"
                bot_say(f"✅ **Answer Scored: {score_result.score}/10** {score_emoji}")
                bot_say(f"**Feedback:** {score_result.reasoning}")
                
                if score_result.strengths:
                    bot_say(f"**Strengths:** {', '.join(score_result.strengths)}")
                
                if score_result.improvements:
                    bot_say(f"**Areas for Improvement:** {', '.join(score_result.improvements)}")
                
            except Exception as e:
                # Fallback scoring
                score_result = simple_score_answer(text.strip(), question["topic"], question["difficulty"])
                st.session_state.candidate.answer_scores[question_id] = score_result
                
                score_emoji = "🟢" if score_result.score >= 8 else "🟡" if score_result.score >= 6 else "🔴"
                bot_say(f"✅ **Answer Scored: {score_result.score}/10** {score_emoji}")
                bot_say(f"**Feedback:** {score_result.reasoning}")
                bot_say("⚠️ AI scoring temporarily unavailable - using basic assessment.")
                print(f"Scoring error: {e}")
        
        # Move to next question or finish
        st.session_state.state.current_question_index += 1
        
        if st.session_state.state.current_question_index < len(questions):
            # Ask next question
            next_question = questions[st.session_state.state.current_question_index]
            difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
            emoji = difficulty_emoji.get(next_question["difficulty"], "🟡")
            bot_say(f"**Question {st.session_state.state.current_question_index + 1}. {emoji} [{next_question['difficulty'].upper()}]** {next_question['question']}")
        else:
            # All questions answered - calculate overall score
            try:
                overall_score = asyncio.run(
                    calculate_overall_score(st.session_state.candidate.answer_scores)
                )
                
                st.session_state.candidate.overall_score = overall_score
                
                # Show final results
                score_emoji = "🟢" if overall_score >= 8 else "🟡" if overall_score >= 6 else "🔴"
                bot_say(f"🎉 **Technical Assessment Complete!**")
                bot_say(f"**Overall Technical Score: {overall_score}/10** {score_emoji}")
                
                # Performance summary
                if overall_score >= 8:
                    bot_say("🌟 Excellent performance! Strong technical knowledge demonstrated.")
                elif overall_score >= 6:
                    bot_say("👍 Good performance! Solid understanding with some areas for growth.")
                else:
                    bot_say("📚 Developing skills! Consider strengthening technical fundamentals.")
                
            except Exception as e:
                print(f"Overall scoring error: {e}")
            
            st.session_state.state.step = "FOLLOWUP"
            bot_say("Feel free to add any additional comments about your experience, projects, or career goals, or type 'exit' to finish.")
        
        return True
    
    return False

def generate_questions_sync(stack: list[str], k: int = 5) -> QASet:
    """
    Synchronous wrapper for async QA generation to keep Streamlit logic simple.
    Always returns a QASet; degrades gracefully on errors.
    """
    try:
        return asyncio.run(generate_stack_questions(stack, k=k))
    except Exception as e:
        st.error(f"AI Question Generation unavailable: {str(e)}")
        # Enhanced fallback questions
        base = stack or ["general software engineering"]
        
        questions_map = {
            "python": "Explain the difference between lists and tuples in Python and when to use each.",
            "django": "How does Django's ORM work and what are its main advantages?",
            "javascript": "What is the difference between == and === in JavaScript?",
            "react": "Explain the component lifecycle in React.",
            "sql": "What's the difference between INNER JOIN and LEFT JOIN?",
            "machine learning": "Explain the bias-variance tradeoff in machine learning.",
            "data science": "How do you handle missing data in a dataset?",
            "aws": "What are the key differences between EC2 and Lambda?",
            "docker": "Explain the difference between Docker images and containers.",
            "git": "What's the difference between merge and rebase in Git?",
            "nodejs": "Explain the event loop in Node.js.",
            "java": "What's the difference between abstract classes and interfaces in Java?",
            "c++": "Explain the concept of RAII in C++.",
            "kubernetes": "What's the difference between Deployment and StatefulSet?",
            "mongodb": "Explain the difference between SQL and NoSQL databases."
        }
        
        items = []
        used_questions = set()
        
        for tech in base[:k]:
            tech_lower = tech.lower().strip()
            question_text = None
            
            for key, question in questions_map.items():
                if key in tech_lower or tech_lower in key:
                    if question not in used_questions:
                        question_text = question
                        used_questions.add(question)
                        break
            
            if not question_text:
                question_text = f"Describe a challenging project you worked on using {tech} and how you solved key problems."
            
            items.append(
                QAQuestion(
                    topic=tech,
                    question=question_text,
                    difficulty="medium",
                    question_id=str(uuid.uuid4())[:8]
                )
            )
        
        while len(items) < k:
            items.append(
                QAQuestion(
                    topic="general",
                    question="Describe your approach to debugging complex technical issues.",
                    difficulty="medium",
                    question_id=str(uuid.uuid4())[:8]
                )
            )
        
        return QASet(items=items[:k])

# Initialize session state
def initialize_session():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "candidate" not in st.session_state:
        st.session_state.candidate = Candidate()
    if "state" not in st.session_state:
        st.session_state.state = ConversationState(step="GREETING")
    if "questions_generated" not in st.session_state:
        st.session_state.questions_generated = False
    if "generated_questions" not in st.session_state:
        st.session_state.generated_questions = []
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        greeting = (
            "Hello! 👋 This assistant will collect essential details for initial screening "
            "and then ask a few role-relevant technical questions with **AI-powered scoring**. Type 'exit' anytime to finish.\n\n"
            "Before proceeding, please confirm consent to process your details strictly for screening purposes. Reply **'I agree'** to continue."
        )
        bot_say(greeting)
        st.session_state.state.step = "CONSENT"

# Initialize session
initialize_session()

# UI Layout
sidebar_settings()
st.title("🎯 TalentScout – AI Hiring Assistant")
render_history()

# Input handling with improved flow
prompt = st.chat_input("Type your message here...")

if prompt:
    user_say(prompt)
    
    # Handle exit detection
    if detect_exit(prompt):
        st.session_state.state.exit_detected = True
        st.session_state.state.step = "END"
        st.rerun()
    else:
        try:
            current_step = st.session_state.state.step
            
            # Handle intake steps
            if current_step in INTAKE_STEPS:
                if apply_answer_to_step(current_step, prompt):
                    st.session_state.state.step = next_step(
                        st.session_state.candidate, 
                        st.session_state.state
                    )
                    
                    next_step_val = st.session_state.state.step
                    if next_step_val in INTAKE_STEPS:
                        q = get_next_question(next_step_val)
                        if q:
                            bot_say(q)
                    elif next_step_val == "GENERATE_QA":
                        bot_say("Perfect! Let me prepare some tailored technical questions with AI scoring for you...")
                    
                    st.rerun()
            
            # Handle technical Q&A phase
            elif current_step == "TECHNICAL_QA":
                if handle_technical_answer(prompt):
                    st.rerun()
            
            elif current_step == "FOLLOWUP":
                # Save additional comments
                st.session_state.candidate.additional_comments = prompt.strip()
                bot_say("Thank you for the additional information! Feel free to add more comments or type 'exit' when ready to finish.")
                st.rerun()
                
        except Exception as e:
            st.error(f"Sorry, something went wrong: {str(e)}")
            bot_say("Sorry, something went wrong while processing that. Please try again.")
            st.rerun()

# Generate technical questions when intake is complete
if st.session_state.state.step == "GENERATE_QA" and not st.session_state.questions_generated:
    try:
        with st.spinner("🤔 Preparing tailored technical questions with AI scoring based on your skills..."):
            qa = generate_questions_sync(st.session_state.candidate.tech_stack, k=5)
            
        # Store questions for reference
        questions_data = []
        for q in qa.items:
            questions_data.append({
                "topic": q.topic,
                "question": q.question,
                "difficulty": q.difficulty,
                "question_id": q.question_id or str(uuid.uuid4())[:8]
            })
        
        st.session_state.generated_questions = questions_data
        st.session_state.candidate.technical_questions = questions_data
        
        bot_say("Great! Here are your personalized technical questions. Each answer will be scored by AI from 0-10:")
        
        # Display all questions first
        for i, q in enumerate(questions_data, 1):
            difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
            emoji = difficulty_emoji.get(q["difficulty"], "🟡")
            bot_say(f"**{i}. {emoji} [{q['difficulty'].upper()}] {q['topic']}** - {q['question']}")
        
        # Ask first question
        bot_say("\n🚀 **Let's begin!** Please answer each question thoroughly. The AI will provide immediate feedback and scoring.")
        first_question = questions_data[0]
        difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
        emoji = difficulty_emoji.get(first_question["difficulty"], "🟡")
        bot_say(f"**Question 1. {emoji} [{first_question['difficulty'].upper()}]** {first_question['question']}")
        
        st.session_state.questions_generated = True
        st.session_state.state.step = "TECHNICAL_QA"
        st.session_state.state.current_question_index = 0
        
        st.rerun()
        
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        bot_say("Having trouble generating custom questions. Let's proceed with the standard process.")
        st.session_state.state.step = "FOLLOWUP"
        st.rerun()

# Handle end state
if st.session_state.state.step == "END" or st.session_state.state.exit_detected:
    already_thanked = any(
        (m["role"] == "assistant" and "Thank you for your time!" in m["content"])
        for m in st.session_state.history
    )
    
    if not already_thanked:
        c = st.session_state.candidate.model_dump()
        display = c.copy()
        
        # Mask sensitive data
        if display.get("email"):
            display["email"] = mask_email(display["email"])
        if display.get("phone"):
            display["phone"] = mask_phone(display["phone"])
        
        bot_say("Thank you for completing the TalentScout assessment! 🙏 Your information and technical responses have been recorded.")
        bot_say("**Next steps:** Your profile will be reviewed and you'll be contacted if there's a good fit.")
        
        # Show detailed scoring summary
        if st.session_state.candidate.answer_scores:
            bot_say("## 📊 **Technical Assessment Results**")
            
            # Overall score
            overall_score = st.session_state.candidate.overall_score or 0
            score_emoji = "🟢" if overall_score >= 8 else "🟡" if overall_score >= 6 else "🔴"
            bot_say(f"**Overall Technical Score: {overall_score}/10** {score_emoji}")
            
            # Performance interpretation
            if overall_score >= 8:
                performance_msg = "🌟 **Outstanding** - Demonstrates strong technical expertise"
            elif overall_score >= 6:
                performance_msg = "👍 **Good** - Solid technical foundation with growth potential"
            elif overall_score >= 4:
                performance_msg = "📚 **Developing** - Basic understanding, room for improvement"
            else:
                performance_msg = "🔄 **Entry Level** - Consider additional training or study"
            
            bot_say(performance_msg)
            
            # Individual question breakdown
            bot_say("**Question-by-Question Breakdown:**")
            for i, (q_id, score) in enumerate(st.session_state.candidate.answer_scores.items(), 1):
                q_emoji = "🟢" if score.score >= 8 else "🟡" if score.score >= 6 else "🔴"
                bot_say(f"**Q{i}:** {score.score}/10 {q_emoji} - {score.reasoning[:80]}...")
        
        # Show basic summary
        summary_lines = []
        if display.get("full_name"):
            summary_lines.append(f"**Name:** {display['full_name']}")
        if display.get("email"):
            summary_lines.append(f"**Email:** {display['email']}")
        if display.get("years_experience") is not None:
            summary_lines.append(f"**Experience:** {display['years_experience']} years")
        if display.get("desired_positions"):
            summary_lines.append(f"**Positions:** {', '.join(display['desired_positions'])}")
        if display.get("tech_stack"):
            summary_lines.append(f"**Tech Stack:** {', '.join(display['tech_stack'])}")
        
        # Add scoring summary
        answers_count = len(display.get("technical_answers", {}))
        questions_count = len(display.get("technical_questions", []))
        summary_lines.append(f"**Technical Assessment:** {answers_count}/{questions_count} questions completed")
        
        if display.get("overall_score"):
            summary_lines.append(f"**AI Technical Score:** {display['overall_score']}/10")
        
        if display.get("additional_comments"):
            summary_lines.append(f"**Additional Comments:** {display['additional_comments'][:100]}...")
        
        if summary_lines:
            bot_say("**Summary (sensitive data masked):**\n" + "\n".join(summary_lines))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Save Complete Assessment", type="primary", key="save_btn"):
            try:
                candidate_data = st.session_state.candidate.model_dump()
                save_candidate(candidate_data)
                st.success("✅ Complete assessment saved successfully!")
                bot_say("✅ Your complete assessment including AI scores and feedback has been saved!")
                
                import os
                data_file = os.getenv("DATA_FILE", "data/candidates.jsonl")
                current_dir = os.getcwd()
                full_path = os.path.join(current_dir, data_file)
                st.info(f"📁 Saved to: {full_path}")
                
            except Exception as e:
                st.error(f"❌ Error saving assessment: {str(e)}")
                bot_say("❌ Error saving assessment. Please try again.")
    
    with col2:
        if st.button("🔄 Start New Assessment", key="reset_btn"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
