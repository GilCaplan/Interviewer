# Interview Process Assistant - Project Context

## Overview
A comprehensive full-stack application designed to help users prepare for interviews and exams through structured practice. The platform enables users to create tailored templates of questions and riddles, collaborate with others, and run realistic mock simulations. Users can publish their templates, explore community-shared content, and track their progress through detailed result analysis. This is a university project for Semester 6 FullStack course, focusing on creating a structured, effective preparation platform for interviews.

## Core Platform Features

### 1. Authentication System
- **Custom Login/Signup Pages**: Built with Flask backend
- **JWT-based Authentication**: Secure user sessions and API access
- **User Management**: Registration, login, password management

### 2. Template Building System
Create comprehensive question/riddle templates through multiple approaches:

#### 2.1 Collaborative Session Management
- **Password-Protected Sessions**: Users can create secure collaborative spaces
- **User Limit Controls**: Host can set maximum participants per session
- **Permission Management**: 
  - Contributors: Can add/suggest questions
  - Viewers: Read-only access to session
  - Host Override: Session creator has final approval authority

#### 2.2 Template Customization Options
- **Difficulty Levels**: NORMAL, MODERATE, HARD classifications
- **Subject Organization**: Primary subjects with sub-categories
- **Question Types**:
  - Open-ended questions
  - Multiple choice
  - Exact answer questions
- **Hint System**: Optional hints for each question
- **Question Limits**: Host-defined maximum questions per template

#### 2.3 LLM Integration API
- **AI-Assisted Generation**: Custom LLM API for automated question creation
- **Prompt-Based Interaction**: Text prompts to generate relevant content
- **Host Feedback Loop**: Session hosts can guide LLM responses
- **Quality Control**: LLM suggestions require host approval

#### 2.4 Question Queue System
- **Dual Queue Management**:
  - User-contributed questions queue
  - LLM-generated questions queue
- **Approval Workflow**: Host reviews and approves/disapproves suggestions
- **Dynamic Refilling**: Queues automatically replenish based on user/host requests
- **Example Workflow**: If template limit is 5 questions, system maintains 10+ suggestions in queues for host selection

### 3. Mock Interview Simulations
- **Template-Based Sessions**: Run realistic interviews using any created template
- **Real-time Execution**: WebSocket-powered live interview sessions
- **Multi-user Support**: Collaborative interview scenarios

### 4. Results & Progress Tracking
- **Session Review**: Detailed analysis of interview performance
- **Grading System**: Automated and manual scoring options
- **Progress Monitoring**: Track improvement over time
- **Result Sharing**: Share performance with mentors or peers

### 5. Community Features
- **Template Publishing**: Share created templates with community
- **Template Discovery**: Browse and use templates created by others
- **Collaborative Building**: Multi-user template creation sessions

## Architecture
- **Frontend**: React 18 (Client/)
- **Backend**: Flask 2.x (server/)
- **Database**: MongoDB
- **Containerization**: Docker & Docker Compose
- **Real-time**: WebSocket support for collaborative features
- **AI Integration**: Custom LLM API for question generation

## Key Technologies
- **Frontend**: React, React Router, Monaco Editor for code editing
- **Backend**: Flask, Flask-CORS, PyMongo, PyJWT for auth
- **AI/ML**: LLM API integration for content generation
- **Development**: Docker, Docker Compose for containerization
- **Testing**: Comprehensive test suites for both frontend and backend

## Project Structure
```
Project_Interviewer/
├── Client/                     # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── auth/         # Login/Signup components
│   │   │   ├── templates/    # Template building UI
│   │   │   ├── sessions/     # Collaborative session components
│   │   │   └── interviews/   # Mock interview interface
│   │   ├── context/          # React context (AuthContext)
│   │   └── utils/            # Utility functions
├── server/                    # Flask backend
│   ├── app/
│   │   ├── auth.py           # Authentication routes
│   │   ├── coding_challenges.py
│   │   ├── questions.py      # Question management
│   │   ├── templates.py      # Template CRUD operations
│   │   ├── llm_api.py       # LLM integration endpoints
│   │   ├── routes.py         # Main API routes
│   │   ├── sessions.py       # Session management
│   │   └── websocket_handlers.py
│   └── tests/               # Server tests
│       ├── test_auth.py     # Authentication tests
│       ├── test_templates.py # Template building tests
│       ├── test_sessions.py  # Session management tests
│       └── test_llm_api.py  # LLM integration tests
└── docker-compose.yml       # Multi-container setup
```

## Development Commands
- **Start application**: `docker-compose up --build`
- **Client dev**: `cd Client && npm start`
- **Server tests**: `cd server && python -m unittest discover -s ../tests -p "test_*.py"`
- **Client tests**: `cd Client && npm test` (Frontend tests need path fixes - focus on backend testing)
- **Run specific test suite**: `cd server && python -m unittest tests.test_templates`

## Implementation Status

### ✅ Completed Features
1. Authentication system with JWT
2. Basic coding challenges with Monaco editor
3. Multi-room collaborative template building foundation
4. WebSocket real-time communication
5. Basic interview questions management
6. Docker containerization setup

### 🔄 In Development
1. **Template Building System**:
   - Advanced collaborative sessions
   - LLM API integration
   - Question queue management
   - Template customization options
2. **Mock Interview Engine**:
   - Template-based simulations
   - Real-time interview sessions
3. **Results & Analytics**:
   - Performance tracking
   - Progress monitoring
   - Result sharing capabilities

### 📋 Planned Features
1. Advanced logical puzzles/riddles
2. Community template marketplace
3. Gamification and achievement system
4. Advanced analytics dashboard
5. Mobile-responsive design enhancements

## API Endpoints

### Core Endpoints
- Health check: `GET /api/health`
- API info: `GET /api/info`
- Authentication: `POST /api/auth/login`, `GET /api/auth/verify`

### Template Management (Complete CRUD)
- Create template: `POST /api/templates`
- Get templates: `GET /api/templates` (with filters: subject, difficulty, created_by)
- Get specific template: `GET /api/templates/<template_id>`
- Update template: `PUT /api/templates/<template_id>`
- Delete template: `DELETE /api/templates/<template_id>`
- Get question types: `GET /api/templates/question-types`

### Template Question Management
- Add question to template: `POST /api/templates/<template_id>/questions`
- Update question: `PUT /api/templates/<template_id>/questions/<question_id>`
- Delete question: `DELETE /api/templates/<template_id>/questions/<question_id>`

### Session Management (Enhanced for Template Building)
- Create session: `POST /api/sessions/create` (supports template_mode)
- Join session: `POST /api/sessions/join/<session_code>`
- Get session data: `GET /api/sessions/<session_id>`
- List user sessions: `GET /api/sessions/list`
- Chat messaging: `POST /api/sessions/<session_id>/chat`

### Collaborative Template Building
- Start question building: `POST /api/sessions/<session_id>/questions/<question_number>/start`
- Update question content: `PUT /api/sessions/<session_id>/questions/<question_id>/update`
- Add collaboration note: `POST /api/sessions/<session_id>/questions/<question_id>/note`
- Finalize question: `POST /api/sessions/<session_id>/questions/<question_id>/finalize`
- Convert session to template: `POST /api/sessions/<session_id>/convert-to-template`

### LLM Integration (Enhanced)
- Generate LLM suggestion: `POST /api/sessions/<session_id>/questions/<question_id>/llm-suggest`
- Legacy LLM endpoint: `POST /api/sessions/<session_id>/llm-question`

### Question Types Supported
- **Multiple Choice**: `options`, `correct_answer`, `explanation`
- **Open Ended**: `question_text`, `sample_answer`, `grading_criteria`
- **True/False**: `question_text`, `correct_answer`, `explanation`  
- **Coding**: `question_text`, `language`, `starter_code`, `solution`, `test_cases`
- **Short Answer**: `question_text`, `expected_keywords`, `max_words`

## Testing Strategy

### Backend Tests
- **Authentication Tests**: User registration, login, JWT validation
- **Template Tests**: CRUD operations, validation, permissions
- **Session Tests**: Creation, joining, collaboration features
- **LLM API Tests**: Question generation, approval workflows
- **WebSocket Tests**: Real-time communication, session management

### Frontend Tests
- **Component Tests**: Template builder, session interface
- **Integration Tests**: Authentication flow, template creation
- **E2E Tests**: Complete user workflows

## Development Notes
- Uses JWT for secure authentication
- MongoDB for flexible document storage
- WebSocket for real-time collaborative features
- Docker containerization for consistent development environment
- LLM API integration for AI-assisted content generation
- Comprehensive testing setup covering all major features
- Modular architecture supporting future feature expansion

## Recent Changes
- Enhanced API endpoints for multi-room template building
- Added comprehensive feature specifications for template system
- Implemented dual endpoints for session management
- Updated test configuration for Docker environment
- Planned LLM integration architecture
- Expanded testing strategy to cover new features