# Interview Process Assistant

A full-stack application to help users prepare for interviews with practice problems, logical puzzles, interview questions, and more. This is a university project (Semester 6 FullStack course).

## Project Structure

```
Project_Interviewer/
├── Client/                     # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── context/          # React context (AuthContext)
│   │   └── utils/            # Utility functions
├── server/                    # Flask backend
│   ├── app/
│   │   ├── auth.py           # Authentication routes
│   │   ├── coding_challenges.py
│   │   ├── questions.py      # Question management
│   │   ├── routes.py         # Main API routes
│   │   ├── sessions.py       # Session management
│   │   └── websocket_handlers.py
│   └── tests/               # Server tests
├── .env                     # Environment variables
├── docker-compose.yml       # Docker Compose configuration
└── CLAUDE.md               # Project documentation
```

## Prerequisites

- Docker and Docker Compose
- Git

## Getting Started

1. Clone the repository:

```bash
git clone https://github.com/GilCaplan/Interviewer.git
cd Project_Interviewer
```

2. Start the application using Docker Compose:

```bash
docker-compose up --build
```

This will:
- Build and start the Flask server on port 5001
- Build and start the React client on port 3000
- Start a MongoDB database

3. Access the application:
   - **Client**: http://localhost:3000
   - **Server API**: http://localhost:5001/api/health

## Key Features (Implemented)

✅ **Authentication system** with JWT  
✅ **Coding challenges** with Monaco editor  
✅ **Multi-room collaborative** template building  
✅ **WebSocket real-time** communication  
✅ **Interview questions** management  

🔄 **In Progress**: Practice programming problems, logical puzzles, mock interviews

## Testing

### Server Tests

Run server tests using Docker (recommended):

```bash
# Start the containers
docker-compose up --build

# Run tests inside the server container
docker exec -it project_interviewer-server-1 python -m unittest discover -s tests -p "test_server.py"
```

Or run locally:

```bash
cd server
python -m unittest discover -s ../tests -p "test_server.py"
```

### WebSocket Tests

Run WebSocket tests (requires python-socketio):

```bash
# Inside Docker container
docker exec -it project_interviewer-server-1 python tests/template_websocket_tests.py

# Or locally (after installing dependencies)
cd server/tests
python3 template_websocket_tests.py
```

### Client Tests

```bash
cd Client
npm test
```

## Development Commands

- **Start application**: `docker-compose up --build`
- **Client dev mode**: `cd Client && npm start`
- **Server tests**: `cd server && python -m unittest discover -s ../tests -p "test_server.py"`
- **Client tests**: `cd Client && npm test`

## API Endpoints

- Health check: `http://localhost:5001/api/health`
- Authentication endpoints in `server/app/auth.py`
- Session management with dual endpoints for multi-room support
- Question management endpoints in `server/app/questions.py`

## Tech Stack

- **Frontend**: React 18, React Router, Monaco Editor
- **Backend**: Flask 2.x, Flask-CORS, PyMongo, PyJWT
- **Database**: MongoDB
- **Real-time**: WebSocket support with Flask-SocketIO
- **Containerization**: Docker & Docker Compose

## Environment Configuration

The application uses environment variables defined in `.env`:
- `SERVER_PORT=5001`
- `MONGO_URI=mongodb://mongo:27017/interviewer_db`
- `JWT_SECRET_KEY=your-secret-key`
- `REACT_APP_API_URL=http://localhost:5001`

## Troubleshooting

1. **Port conflicts**: Ensure ports 3000, 5001, and 27017 are available
2. **Docker issues**: Try `docker-compose down` then `docker-compose up --build`
3. **Database connection**: MongoDB runs in a separate container, accessible at `mongo:27017`
4. **WebSocket tests**: Ensure `python-socketio` is installed (included in requirements.txt)