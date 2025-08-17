# Core Project Requirements

## Basic Requirements

- **Topic**: Can be anything as long as it meets technical requirements
- **Docker**: Must run first try on any computer using Docker
- **Documentation**: Clear instructions in README.md file on how to run the project and tests
- **Focus**: Project judged on backend ONLY - no points for AI model complexity or visual design

## Backend Architecture Requirements

### Minimum Images
At least 2 Docker images required:

**Option 1**: Web + MongoDB + API (2 images)  
**Option 2**: Web + MongoDB + AI Model (3 images)

### Core Components
- **AI Model**: Can be simple API call to existing model - complexity not rewarded
- **Database**: Must use MongoDB for persistent data storage
- **Security**:
  - Never save passwords as plain text
  - Only web container exposed to clients
  - Clients cannot directly communicate with AI model & database

## Risk Assessment Requirements

Must address these four areas:

### 1. Availability & Redundancy
- What can go wrong? 
- What happens then? 
- *(Answer can't be "it crashes")*

### 2. Scalability
- How to expand when startup gains traction?
- Handle multiple concurrent users (use async/parallel programming)

### 3. Spam Protection
- How to deal with request spamming
- Prevent financial losses

### 4. Security
- Proper authentication and access controls

## Testing Requirements

### Required Test Types
Must implement ALL types of tests:

- **Unit Tests**
- **Integration Tests** 
- **System (End-to-End) Tests**
- **Stress Tests**
- **Security Tests** (e.g., features only accessible after login)

### Testing Standards
- Tests must cover all implemented features, typical use cases, and edge cases
- Tests must run first try on any computer
- Must test all logical features (e.g., sign-up, login procedures)
- No cheating - they will verify test implementations
- Use environment variables for testing isolated components (`TESTING=true`)

## Version Control Requirements

### GitHub Standards
- Must use GitHub (no zip files accepted)
- Regular commits (not one every 3 weeks)
- Informative commit messages (not "FINAL FINAL FINAL")
- All group members must contribute commits

## Submission Requirements

Submit these three items:

1. **GitHub repository link**
2. **Demo video** of you using the app
3. **Written report** including:
   - App explanation
   - Features description
   - Detailed test explanations for each feature
   - Risk assessment (as detailed above)

## Important Deadlines & Penalties

- **Project proposal**: Due today (when guidelines were given)
- **Final submission**: August 10th, 2025
- **Penalty**: -5 points each time code doesn't run and needs resubmission
- **Warning**: Don't wait until last few days before deadline
- **Severe penalty** for malicious test cheating

## Additional Notes

- Azure Virtual Machine available for testing (highly recommended)
- No strict project structure required "as long as it works"
- Manual testing will include stress testing, random inputs, concurrent users, and spam requests
- Environment variables should be used appropriately (`.env` files)

---

**The project emphasizes backend robustness, comprehensive testing, and production-ready deployment over visual appeal or AI complexity.**