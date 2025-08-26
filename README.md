# Interview Process Assistant

A comprehensive full-stack application for collaborative interview preparation with AI assistance. Built with Flask backend, React frontend, and MongoDB database in Docker containers.

## 🚀 Quick Start (First-Time Setup)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed
- Git installed

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/GilCaplan/Interviewer.git
   cd Project_Interviewer
   ```

2. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   ```

3. **Get Google Gemini API key (optional but recommended)**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in and create a new API key
   - Edit `.env` file and replace `your_gemini_api_key_here` with your actual key
   - **Without API key**: App works fully but uses mock AI responses

4. **Start the application**
   ```bash
   # This will build and start all containers
   docker-compose up --build
   ```

5. **Access the application**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:5001
   - **Database**: MongoDB running internally

**That's it!** The application should be running on your first try.

## 🧪 Testing

### Run All Tests
```bash
# From project root directory
cd server/tests
python run_all_tests.py
```

### Run Individual Tests
```bash
# Basic functionality
python individual_tests/test_basic_functionality.py

# Template building
python individual_tests/test_template_building.py

# Security testing
python individual_tests/test_security_authentication_consolidated.py

# All available test files:
ls individual_tests/test_*.py
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: API and database integration  
- **System Tests**: End-to-end workflows
- **Stress Tests**: Concurrent users and load testing
- **Security Tests**: Authentication and input validation

**Expected Result**: 100% pass rate (168+ tests)

## 🎯 Key Features

### For Interviewers
- **Template Builder**: Create interview question templates collaboratively
- **AI Assistance**: Get question suggestions from Google Gemini
- **Real-time Collaboration**: Multiple users can build templates together
- **Question Types**: Multiple choice, coding, open-ended, true/false, short answer

### For Interviewees
- **Practice Interviews**: Take mock interviews using any template
- **Performance Tracking**: Get detailed feedback and scoring
- **Progress Analytics**: Track improvement over time

### Technical Features
- **Docker Containerized**: Runs consistently across all environments
- **JWT Authentication**: Secure user sessions
- **WebSocket Real-time**: Live collaboration features
- **MongoDB Database**: Persistent data storage
- **Comprehensive Testing**: 100% test coverage with automated testing

## 📁 Project Structure
```
Project_Interviewer/
├── Client/                 # React frontend
├── server/                 # Flask backend
│   ├── app/               # Application code
│   ├── tests/             # Test suite
│   └── requirements.txt   # Python dependencies
├── docker-compose.yml     # Docker orchestration
├── .env.example          # Environment template
└── README.md            # This file
```

## 🔧 Development

### Local Development (without Docker)
```bash
# Backend
cd server
pip install -r requirements.txt
python app.py

# Frontend
cd Client
npm install
npm start
```

### Adding New Dependencies
```bash
# Backend
cd server
pip install package-name
pip freeze > requirements.txt

# Frontend
cd Client
npm install package-name
```

## 🐛 Troubleshooting

### Port Conflicts
- **macOS users**: Disable AirPlay Receiver if port 5000 conflicts
- **Alternative**: Change `SERVER_PORT` in `.env` file

### Docker Issues
```bash
# Clean restart
docker-compose down
docker-compose up --build

# View logs
docker-compose logs server
docker-compose logs client
```

### Test Failures
```bash
# Check server is running
curl http://localhost:5001/api/health

# Run tests individually to isolate issues
python individual_tests/test_basic_functionality.py
```

## 🏗️ Architecture

- **Frontend**: React with Socket.IO for real-time features
- **Backend**: Flask with Flask-SocketIO for WebSocket support
- **Database**: MongoDB with connection pooling
- **AI Integration**: Google Gemini 1.5 Flash API
- **Authentication**: JWT tokens with secure password hashing
- **Rate Limiting**: API protection and cost control
- **Testing**: Comprehensive test suite with 168+ individual tests

## 🔒 Security Features

- **Password Security**: PBKDF2-SHA256 hashing with salt
- **API Protection**: Rate limiting and input validation
- **Container Security**: Non-root users, minimal attack surface
- **Environment Variables**: API keys protected with .gitignore

## 📊 System Requirements

**Minimum:**
- 4GB RAM
- 2 CPU cores
- 2GB disk space

**Recommended:**
- 8GB RAM
- 4 CPU cores  
- 5GB disk space

**Tested Performance:**
- ✅ 100+ concurrent WebSocket users
- ✅ 200+ simultaneous sessions
- ✅ 30,000+ messages per minute

---

This project demonstrates production-ready full-stack development with modern technologies including Docker containerization, real-time collaboration, AI integration, and comprehensive testing strategies.