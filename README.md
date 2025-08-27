# 🎯 TalentScout - AI-Powered Hiring Assistant

An intelligent conversational hiring assistant built with Streamlit and powered by local Ollama models. TalentScout streamlines the candidate screening process by collecting essential information and generating personalized technical questions based on candidates' skill sets.

## ✨ Features

### 🤖 **Intelligent Conversation Flow**
- **Consent Management**: GDPR-compliant consent collection
- **Progressive Data Collection**: Step-by-step candidate information gathering
- **Smart Validation**: Real-time input validation with helpful feedback
- **Exit Detection**: Natural conversation termination

### 🧠 **AI-Powered Question Generation**
- **Dynamic Technical Questions**: Auto-generated questions based on candidate's tech stack
- **Difficulty Levels**: Easy, Medium, and Hard questions with visual indicators
- **Comprehensive Coverage**: Questions tailored to specific technologies (Python, Django, React, etc.)
- **Fallback System**: Graceful degradation when AI service is unavailable

### 💾 **Data Management**
- **Secure Storage**: Local JSONL file storage with encryption capabilities
- **Complete Profiles**: Stores both basic info and technical question answers
- **Privacy Protection**: Sensitive data masking in UI display
- **Timestamped Records**: Automatic submission timestamps

### 🎨 **User Experience**
- **Progress Tracking**: Real-time progress visualization in sidebar
- **Responsive Design**: Clean, professional interface
- **Error Handling**: Graceful error recovery with user-friendly messages
- **Session Management**: Persistent chat history during session

## 🏗️ Architecture

talentscout/
├── app.py # Main Streamlit application
├── requirements.txt # Python dependencies
├── README.md # Project documentation
├── .env.example # Environment variables template
├── .gitignore # Git ignore rules
│
├── core/ # Core business logic
│ ├── init.py
│ ├── schemas.py # Pydantic data models
│ ├── state.py # Conversation state management
│ ├── qa_generator.py # AI question generation
│ ├── nlp.py # LLM client wrapper
│ ├── storage.py # Data persistence
│ └── security.py # Security utilities
│
├── ui/ # User interface components
│ ├── components.py # Reusable UI components
│ └── theming.py # CSS styling (optional)
│
├── data/ # Data storage
│ └── candidates.jsonl # Candidate submissions
│
├── prompts/ # AI prompt templates
│ └── dynamic_templates.py
│
├── policies/ # Compliance documents
│ └── gdpr_policy.md


## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Ollama** (for AI-powered question generation)

### 1. Clone Repository
git clone https://github.com/yourusername/talentscout.git
cd talentscout


### 2. Install Dependencies
pip install -r requirements.txt


### 3. Set Up Ollama
Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

Pull the required model
ollama pull llama3.1:8b

Verify installation
ollama list


### Ollama Configuration

The application uses Ollama for AI-powered question generation:

- **Default Model**: `llama3.1:8b`
- **API Endpoint**: `http://localhost:11434`
- **Fallback**: Built-in question templates when AI is unavailable



