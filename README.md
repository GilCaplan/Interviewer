# Interview Process Assistant

A full-stack application to help users prepare for interviews with practice problems, logical puzzles, interview questions, and more.

## Project Structure

```
Project_Interviewer/
├── .venv/                # Python virtual environment
├── Client/               # React frontend
├── server/               # Flask backend
├── .env                  # Environment variables
├── Docker                # Docker reference file
├── docker-compose.yml    # Docker Compose configuration
└── tests/                # Test files for both client and server
```

## Prerequisites

- Docker and Docker Compose
- Git

## Getting Started

1. Clone the repository:

```bash
git clone <repository-url>
cd Project_Interviewer
```

2. Start the application using Docker Compose:

```bash
docker-compose up --build
```

This will:
- Build and start the Flask server
- Build and start the React client
- Start a MongoDB database

3. Access the application:
   - Client: http://localhost:3000
   - Server API: http://localhost:5000/api/health

## Development

### Server (Flask)

The server is located in the `server/` directory and uses Flask with the following structure:
- `app/__init__.py`: Application factory
- `app/routes.py`: API routes
- `app/config.py`: Configuration settings

### Client (React)

The client is located in the `Client/` directory and uses React with the following structure:
- `src/App.js`: Main application component
- `src/components/`: React components
- `public/`: Static files

## Testing

You can run tests for both the server and client components:

### Server Tests

```bash
cd server
python -m unittest discover -s ../tests -p "test_server.py"
```

### Client Tests

```bash
cd Client
npm test
```

## Features (Planned)

1. Practice programming problems
2. Logical puzzles/riddles
3. Interview questions
4. Behavioral questions
5. Case studies
6. Mock interviews
7. Interview Dashboard
8. Resume help
9. Q/A with model & discussion forums
10. Gamification

## Tech Stack

- **Server**: Flask (Python)
- **Client**: React (JavaScript)
- **Database**: MongoDB
- **Containerization**: Docker