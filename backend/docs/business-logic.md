# Business Logic Layer

## Purpose
Encapsulates application rules and orchestration above raw database access.

## Location
- Package: `backend/services`
- Primary module: `user_service.py`

## Responsibilities
- Input validation (names, emails, password length)
- Delegating persistence to models layer
- Aggregating data for higher-level operations

## Key Services
- `UserService.register_user(name, email, password)`
  - Validates inputs
  - Calls models to create user
  - Returns success/failure with message

## Collaborators
- Models layer (`backend/models`): `User`, `Attempt`
- Web layer (`backend/app.py`): routes call services

## Future Enhancements
- Add more services (MockInterviewService, StatsService)
- Centralize error handling with custom exceptions
- Introduce DTOs/typed responses
