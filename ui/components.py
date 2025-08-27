import streamlit as st

def sidebar_settings() -> None:
    """Render sidebar with settings and information"""
    with st.sidebar:
        st.header("⚙️ Settings")
        st.caption("🤖 Powered by local Ollama models")
        st.caption("💾 Chat history persists during session")
        
        if st.button("🔄 Reset Session", help="Clear all data and start over"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        
        # Show current progress
        if "candidate" in st.session_state and "state" in st.session_state:
            show_progress()

def show_progress():
    """Show current progress through the intake process"""
    st.subheader("📊 Progress")
    
    candidate = st.session_state.candidate
    
    # Calculate progress
    fields = [
        ("Consent", candidate.consent_given),
        ("Name", bool(candidate.full_name)),
        ("Email", bool(candidate.email)),
        ("Phone", bool(candidate.phone)), 
        ("Experience", candidate.years_experience is not None),
        ("Position", bool(candidate.desired_positions)),
        ("Location", bool(candidate.current_location)),
        ("Tech Stack", bool(candidate.tech_stack)),
    ]
    
    completed = sum(1 for _, done in fields if done)
    total = len(fields)
    
    # Progress bar
    progress = completed / total if total > 0 else 0
    st.progress(progress, text=f"{completed}/{total} completed")
    
    # Show field status
    for field_name, is_done in fields:
        status = "✅" if is_done else "⏳"
        st.caption(f"{status} {field_name}")

def append_message(role: str, content: str) -> None:
    """Add a message to the chat history"""
    if "history" not in st.session_state:
        st.session_state.history = []
    
    # Avoid duplicate consecutive messages
    if (st.session_state.history and 
        st.session_state.history[-1]["role"] == role and 
        st.session_state.history[-1]["content"] == content):
        return
    
    st.session_state.history.append({"role": role, "content": content})

def render_history() -> None:
    """Render the chat history"""
    for msg in st.session_state.get("history", []):
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        
        with st.chat_message(msg["role"], avatar=avatar):
            # Handle markdown formatting
            content = msg["content"]
            if msg["role"] == "assistant":
                # Make bot messages more visually appealing
                st.markdown(content, unsafe_allow_html=False)
            else:
                # User messages in simpler format
                st.write(content)

def show_error(message: str):
    """Display an error message"""
    st.error(f"❌ {message}")

def show_success(message: str):
    """Display a success message""" 
    st.success(f"✅ {message}")

def show_info(message: str):
    """Display an info message"""
    st.info(f"ℹ️ {message}")
