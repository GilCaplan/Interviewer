# Interview Process Assistant

A collaborative platform for creating and practicing interview questions. Teams can build question templates together with AI assistance, then use them for mock interviews with automated evaluation.

**What it does:**
- **Template Building:** Collaboratively create interview question sets with real-time editing
- **AI-Powered:** Get question suggestions from Google Gemini AI
- **Mock Interviews:** Practice with any template and receive detailed feedback
- **Performance Tracking:** Track progress with automated scoring and analytics

**Tech Stack:** Flask backend, React frontend, MongoDB database, Docker containerized.

## Quick Start

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) + Git

```bash
# 1. Clone repository
git clone https://github.com/GilCaplan/Interviewer.git
cd Project_Interviewer

# 2. Set up environment
create a .env file and add the following with a gemini api key:

"""
# Flask Backend Configuration
FLASK_APP=app
FLASK_ENV=development
SERVER_PORT=5001
SECRET_KEY=interview-assistant-secret-key-change-in-production

# Database Configuration
MONGO_URI=mongodb://db:27017/interview-assistant

# React Frontend Configuration  
REACT_APP_API_URL=http://localhost:5001
REACT_APP_WS_URL=ws://localhost:5001

# LLM Configuration
GEMINI_API_KEY=
LLM_MODEL=gemini-1.5-flash

# HuggingFace Configuration (Optional)
HUGGINGFACE_TOKEN=

# Application Limits
MAX_SESSION_PARTICIPANTS=10
MAX_QUESTIONS_PER_TEMPLATE=20
SESSION_TIMEOUT_HOURS=24

# Rate Limiting (requests per minute/day)
LLM_REQUESTS_PER_MINUTE=15
LLM_REQUESTS_PER_DAY=1500
"""
# Optional: Edit .env and add your Gemini API key from https://makersuite.google.com/app/apikey

# 3. Start application
docker-compose up --build

# 4. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:5000
```

## Testing

```bash
# All tests
cd server/tests && python run_all_tests.py

# Individual tests
python individual_tests/test_basic_functionality.py
python individual_tests/test_template_building.py
python individual_tests/test_security_authentication_consolidated.py

# List all tests
ls individual_tests/test_*.py
```

**Expected:** 100% pass rate (168+ tests)

## Key Features

- **Collaborative Template Builder** - Real-time multi-user question creation
- **AI Assistance** - Google Gemini integration for question suggestions  
- **Mock Interviews** - Practice with any template
- **Performance Analytics** - Detailed feedback and scoring
- **WebSocket Real-time** - Live collaboration
- **JWT Authentication** - Secure user sessions
- **Docker Containerized** - Consistent deployment

## Architecture

- **Frontend:** React + Socket.IO
- **Backend:** Flask + Flask-SocketIO  
- **Database:** MongoDB
- **AI:** Google Gemini 1.5 Flash
- **Security:** PBKDF2-SHA256 password hashing, rate limiting
- **Testing:** 5 test categories (Unit, Integration, System, Stress, Security)

## Troubleshooting

**Port conflicts:** Change `SERVER_PORT` in `.env`  
**Docker issues:** `docker-compose down && docker-compose up --build`  
**Test failures:** `curl http://localhost:5000/api/health`

## System Requirements

**Minimum:** 4GB RAM, 2 cores, 2GB disk  
**Tested:** 100+ concurrent users, 200+ sessions, 30K+ msg/min

---

Production-ready full-stack application demonstrating Docker containerization, real-time collaboration, AI integration, and comprehensive testing.
