# Interview Process Assistant - Project Context

## Overview
A comprehensive full-stack application designed to help users prepare for interviews through collaborative template building and real-time practice sessions. The platform features a 3-screen interface for template building with AI assistance, multi-user collaboration, and comprehensive testing capabilities. This is a university project for Semester 6 FullStack course, focusing on practical interview preparation with modern web technologies.

## Core Platform Features

### 1. Authentication System
- **JWT-based Authentication**: Secure user sessions and API access
- **Auto-registration**: Users are automatically registered on first login
- **Token-based Authorization**: Protected routes and API endpoints

### 2. Template Building System ✅ **FULLY IMPLEMENTED**

#### 2.1 Three-Screen Interface
The template building system features a comprehensive 3-screen interface:

1. **Template Editor Screen**:
   - Numbered question building (1, 2, 3...)
   - Multiple question types with dynamic forms
   - Host controls for starting, editing, and finalizing questions
   - Real-time collaboration with live updates
   - Question type selection with validation

2. **LLM Chat Screen**:
   - Real Google Gemini AI integration (free tier)
   - General chat for broad assistance
   - Question-specific suggestions with context
   - Rate limiting for free usage (10/min, 1000/day)
   - Automatic fallback to mock responses when rate limited

3. **Participants List Screen**:
   - Live participant management
   - Session statistics and activity tracking
   - Host settings for viewing modes and permissions
   - Session sharing with codes and links
   - User activity monitoring

#### 2.2 Question Types (Fully Supported)
- **Open Ended**: Text questions with grading criteria and hints
- **Multiple Choice**: Options with correct answers and explanations  
- **True/False**: Boolean questions with explanations
- **Coding**: Programming challenges with starter code and test cases
- **Short Answer**: Keyword-based validation with word limits

#### 2.3 Real LLM Integration ✅ **PRODUCTION READY**
- **Google Gemini 1.5 Flash**: Free tier model for cost-effective usage
- **Smart Rate Limiting**: Conservative limits to stay within free quotas
- **Context-Aware Generation**: AI understands session context and question types
- **Secure API Key Management**: Environment variables, not committed to GitHub
- **Graceful Degradation**: Falls back to mock responses when rate limited

#### 2.4 Collaborative Features
- **Multi-User Sessions**: Support for up to 10 concurrent users
- **Real-Time Updates**: WebSocket-powered live collaboration
- **Host Controls**: Session creators have final authority over content
- **Permission Management**: Configurable viewing modes (edit/view/suggestions)
- **Session Codes**: Easy sharing with generated access codes

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
- **Run comprehensive tests**: `cd server/tests/gil_tests && python run_all_tests.py`
- **Individual test suites**: 
  - Basic functionality: `python test_basic_functionality.py`
  - Template building: `python test_template_building.py`
  - Session collaboration: `python test_session_collaboration.py`
  - LLM integration: `python test_llm_mock_integration.py`

## How to Create Templates (Frontend Guide)

### Method 1: Collaborative Session Builder (Recommended)
This is the main way to create templates using the 3-screen interface:

1. **Access the Application**: Visit `http://localhost:3000`
2. **Login**: Use any username (auto-registration)
3. **Create a Session**: 
   - Navigate to session creation (you can manually go to `/session/[any-code]`)
   - Or join an existing session with a session code
4. **Use the 3-Screen Interface**:
   - **Template Editor**: Build questions with the host controls
   - **LLM Chat**: Get AI assistance for question generation
   - **Participants**: Manage session settings and collaborators
5. **Build Questions**: 
   - Choose question type (open ended, multiple choice, etc.)
   - Fill in required fields for each type
   - Use AI suggestions or write manually
   - Finalize each question when complete
6. **Convert to Template**: 
   - When done, use "Convert to Template" in the Template Editor
   - This saves your collaborative work as a reusable template

### Method 2: Direct API Template Creation
For programmatic template creation:

```javascript
// Example: Create a template directly via API
const templateData = {
  template_name: "Algorithm Interview Questions",
  description: "Common algorithm questions for technical interviews",
  subject: "algorithms",
  difficulty: "medium",
  is_public: false
};

fetch('/api/templates', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${userToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(templateData)
});
```

### Question Type Examples

Each question type has specific required fields:

#### Multiple Choice
```json
{
  "type": "multiple_choice",
  "question_text": "What is the time complexity of quicksort?",
  "options": ["O(n)", "O(n log n)", "O(n²)", "O(log n)"],
  "correct_answer": "O(n log n)",
  "explanation": "Quicksort has O(n log n) average case complexity"
}
```

#### Coding Challenge
```json
{
  "type": "coding",
  "question_text": "Implement a function to reverse a linked list",
  "language": "python",
  "starter_code": "def reverse_list(head):\n    # Your code here\n    pass",
  "solution": "def reverse_list(head):\n    prev = None\n    while head:\n        next_temp = head.next\n        head.next = prev\n        prev = head\n        head = next_temp\n    return prev",
  "test_cases": [
    {"input": "[1,2,3]", "expected": "[3,2,1]"}
  ]
}
```

## Implementation Status

### ✅ Completed Features (Production Ready)
1. **Complete Authentication System**: JWT-based with auto-registration
2. **3-Screen Template Builder**: Template Editor, LLM Chat, Participants List
3. **Real LLM Integration**: Google Gemini 1.5 Flash with rate limiting
4. **Multi-User Collaboration**: WebSocket real-time with up to 10 users
5. **5 Question Types**: Open ended, multiple choice, true/false, coding, short answer
6. **Session Management**: Creation, joining, settings, participant management
7. **Docker Containerization**: Complete development environment
8. **Comprehensive Testing**: 98.2% pass rate across 57 test cases
9. **Template Conversion**: Session-to-template functionality
10. **Secure API Key Management**: Environment variables, GitHub-safe

### 🔄 Available But Needs UI Enhancement
1. **Template Gallery**: Backend complete, frontend needs better UX
2. **Direct Template Creation**: API exists, needs dedicated frontend form
3. **Mock Interview Engine**: Backend ready, needs interview runner UI
4. **Advanced Question Management**: Update/delete endpoints available

### 📋 Future Enhancements
1. Mobile-responsive design improvements
2. Advanced analytics dashboard
3. Community features and template sharing
4. Gamification and progress tracking
5. Advanced LLM features (when budget allows)

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

### Collaborative Template Building (✅ Implemented)
- Start question building: `POST /api/sessions/<session_id>/questions/<question_number>/start`
- Update question content: `PUT /api/sessions/<session_id>/questions/<question_id>/update`
- Add collaboration note: `POST /api/sessions/<session_id>/questions/<question_id>/note`
- Finalize question: `POST /api/sessions/<session_id>/questions/<question_id>/finalize`
- Convert session to template: `POST /api/sessions/<session_id>/convert-to-template`
- Update session settings: `PUT /api/sessions/<session_id>/settings`
- Get participants: `GET /api/sessions/<session_id>/participants`

### LLM Integration (✅ Production Ready with Gemini)
- Generate LLM suggestion: `POST /api/sessions/<session_id>/questions/<question_id>/llm-suggest`
- General LLM chat: `POST /api/sessions/<session_id>/llm-chat`
- Get chat history: `GET /api/sessions/<session_id>/chat-history`

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