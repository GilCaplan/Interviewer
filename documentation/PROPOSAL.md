# Project Proposal: Interview Preparation Platform

## Project Overview

Create tailored templates of questions and riddles to prepare for interviews or exams. Publish your templates or explore those shared by others. Run realistic mock simulations based on any template. After each session, review, grade, and share results to monitor progress and refine your skills. A focused platform for structured, effective preparation for interviews.

**Technology Stack**: Flask Backend with custom authentication system

---

## Core Features

### 1. Authentication System
- Build our own custom login/signup page
- Built using Flask framework

### 2. Template Building System

**Core Idea**: Build templates manually/with friends/LLM of questions/riddles (control number of questions, subject through LLM API that we build)

#### 2.1 Collaborative Session Management
- User can open a session with configurable settings:
  - Set password protection
  - LLM integration in chat
  - User limit (who can join the session)
  - User permissions (contribute or view-only)
  - Host override capabilities for template building decisions

#### 2.2 Template Building Objective
- Primary goal: Building comprehensive templates for questions/riddles

#### 2.3 Template Configuration Options
- **Difficulty Levels**: Normal/Moderate/Hard
- **Subject and Sub-subject** categorization
- **Hints system** for questions
- **Question Types**:
  - Open-ended questions
  - Multiple choice
  - Exact answer format

#### 2.4 LLM API Integration
- Custom LLM API for template generation
- Text prompt-based template building
- Flexibility for session host and user input
- **Note**: Session host can prompt and give feedback to users/LLM to generate more relevant or concise responses

#### 2.5 Collaborative Question Generation
- Session host controls maximum number of questions in template
- Host can prompt users and LLM in chatrooms
- Generate relevant questions/riddles for host approval/disapproval

#### 2.6 Question Queue System
- **Example**: If host limits template to 5 questions:
  - LLM and users can offer 10+ questions
  - Queue system for managing question suggestions
  - Host can pull from either:
    - User-generated questions queue
    - LLM-generated questions queue
  - Host approval/disapproval system
  - Queue refill on user/host request

---

### 3. Template Simulation System

**Core Idea**: Use templates published in step 2 or templates published by other users (publicly or shared between friends)

*Feature: Special links to share templates privately*

#### 3.1 Template Discovery
- **Public Template Gallery**: All templates published publicly
- **Template Metadata**:
  - Template name and description
  - Subject and sub-subject
  - Publishing user
  - Privacy settings (private/public)
- **Search and Filter System**: Find specific templates for simulation

#### 3.2 Interview Session Setup
- Interview option opens on specified pre-built template chosen from 3.1

#### 3.3 Simulation Configuration
- **Interviewee Options**:
  - Choose number of questions to answer
  - Set time limits (optional)
- **Note**: Possibly allow spectators to watch and give feedback

#### 3.4 Simulation Execution
- Start simulation based on chosen template and configurations from 3.3
- Interactive interface for user to type answers to questions/riddles

#### 3.5 Results Management
- Export/publish simulation results
- Results sharing for feedback collection

#### 3.6 Template Analytics Dashboard
- **Data Tracking**:
  - Number of times simulation was run on template
  - Average scores
  - Performance metrics

---

## Security Implementation

### Rate Limiting
- **Button Interactions**: Limit clicks to X number per second and per minute
- Prevent spam and abuse

### Password Security
- **Hashing and Storage**: Implement secure password hashing (explore various methods)
- No plain text password storage

### LLM API Security
- **Error Handling**: Comprehensive error management
- **Load Protection**: Prevent LLM API overload
- Rate limiting for API calls

### Access Control Testing
- **Comprehensive Testing**: Implement tests as taught in class
- **Feature Access Control**: Test user access permissions for different features
- **Security Testing**: Ensure proper authentication and authorization

---

## Implementation Priorities

1. **Phase 1**: Authentication system and basic template creation
2. **Phase 2**: Collaborative session management and LLM integration
3. **Phase 3**: Simulation system and template discovery
4. **Phase 4**: Security hardening and comprehensive testing

This proposal outlines a comprehensive interview preparation platform that emphasizes collaboration, AI-assisted content creation while maintaining strong security standards.