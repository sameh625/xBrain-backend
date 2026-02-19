<!--
Sync Impact Report - Constitution v1.0.0
==========================================
Version: INITIAL → 1.0.0
Ratification Date: 2026-02-11
Last Amended: 2026-02-11

Modified Principles: None (initial creation)
Added Sections:
  - Core Principles (5 principles)
  - Security Standards
  - Development Workflow
  - Governance

Templates Requiring Updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section compatible
  ✅ .specify/templates/spec-template.md - Requirements structure compatible
  ✅ .specify/templates/tasks-template.md - Task organization compatible

Follow-up TODOs: None
-->

# xBrain Constitution

## Core Principles

### I. API-First Design

Every feature MUST be designed as a RESTful API endpoint first. The backend exists solely to serve the mobile application.

- All functionality exposed via versioned API endpoints under `/api/`
- Endpoints MUST follow REST conventions (GET, POST, PATCH, DELETE)
- Request/response bodies MUST use JSON format
- All endpoints MUST be documented with clear input/output schemas
- API versioning via URL path (e.g., `/api/v1/`) when breaking changes are required

**Rationale**: The mobile app depends entirely on the backend API. API-first ensures consistent contracts and enables parallel frontend/backend development.

### II. Security by Default (NON-NEGOTIABLE)

Security MUST be built into every feature from the start, not added as an afterthought.

- All authenticated endpoints MUST use JWT tokens (via djangorestframework-simplejwt)
- Password validation MUST enforce minimum requirements (8+ chars, uppercase, lowercase, number, special char)
- Rate limiting MUST be applied to sensitive endpoints (login, OTP, registration)
- All user inputs MUST be validated and sanitized before processing
- Email verification MUST be required before account activation
- No sensitive data (passwords, tokens, API keys) in logs or responses

**Rationale**: This application handles user authentication and personal data. Security vulnerabilities could expose user accounts and damage trust.

### III. Clean Architecture & Separation of Concerns

Code MUST be organized following Django and REST Framework conventions with clear separation between layers.

- **Models** (`models.py`): Data structures and database relationships only
- **Serializers** (`serializers.py`): Input validation and output serialization
- **Views** (`views.py`): Request handling and business logic orchestration
- **Utils** (`utils.py`): Reusable utility functions (no business logic)
- **Signals** (`signals.py`): Automatic behaviors triggered by model events
- **URLs** (`urls.py`): Route definitions only, no logic

Each layer MUST have a single responsibility. Cross-cutting concerns use Django's built-in mechanisms (signals, middleware).

**Rationale**: Clean separation makes code testable, maintainable, and allows team members to work on different layers without conflicts.

### IV. Explicit Over Implicit

All behavior MUST be explicit and discoverable through code reading.

- All model relationships MUST be explicitly defined (no magic foreign keys)
- Automatic behaviors (like PointsWallet creation) MUST use Django signals with clear documentation
- Environment configuration MUST use `.env` with documented defaults in `.env.example`
- All API endpoints MUST be registered in `urls.py` with named routes
- Database constraints MUST be defined at the model level (unique, validators, indexes)

**Rationale**: Explicit code reduces debugging time and makes onboarding easier. New developers should understand the system by reading the code, not memorizing hidden behaviors.

### V. Test User Journeys, Not Just Functions

Testing MUST focus on complete user workflows, not isolated functions.

- Integration tests MUST cover complete authentication flows (register → OTP → verify → login)
- Tests MUST validate both success and error scenarios
- API tests MUST verify response structure, status codes, and error messages
- Security features (rate limiting, lockouts) MUST have dedicated test cases

**Rationale**: Users experience workflows, not individual functions. Testing journeys ensures features work end-to-end and catches integration issues early.

## Security Standards

### Authentication & Authorization

- JWT access tokens: 1 hour lifetime
- JWT refresh tokens: 7 days lifetime
- OTP codes: 6 digits, 5 minute expiry
- Login rate limiting: 5 attempts, 15 minute lockout
- OTP resend: 60 second cooldown, max 3 attempts

### Data Protection

- All passwords MUST be hashed using Django's built-in password hashing
- Phone numbers and emails MUST be unique across all users
- User IDs MUST use UUID (not sequential integers) to prevent enumeration attacks
- Points balance MUST use PositiveIntegerField (cannot be negative)

### Required Security Features

- CORS configuration for mobile app domains
- CSRF protection for session-based views (if any)
- Input validation on all serializer fields
- Error messages MUST NOT leak implementation details

## Development Workflow

### Code Organization

1. All API code lives in the `api/` Django app
2. Project configuration lives in `xBrain/` settings
3. All database models use UUID primary keys
4. All timestamps use `auto_now_add` and `auto_now`

### Adding New Features

1. Create/update models in `api/models.py`
2. Create migrations: `python manage.py makemigrations api`
3. Apply migrations: `python manage.py migrate`
4. Create serializers in `api/serializers.py`
5. Create views in `api/views.py`
6. Register URLs in `api/urls.py`
7. Test the complete user journey

### Required Documentation

- CLAUDE.md: Architecture overview and development commands
- .env.example: All environment variables with descriptions
- Docstrings: All utility functions and complex view logic

## Governance

### Amendment Process

1. Propose amendment with clear rationale
2. Document impact on existing code
3. Update version number following semantic versioning:
   - **MAJOR**: Backward-incompatible principle changes
   - **MINOR**: New principles or expanded sections
   - **PATCH**: Clarifications and typo fixes
4. Update dependent templates if affected
5. Update `LAST_AMENDED_DATE` to current date

### Compliance

- All new code MUST adhere to these principles
- Code reviews MUST verify constitutional compliance
- Deviations MUST be documented with justification in code comments
- CLAUDE.md provides runtime development guidance

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-11 | Initial constitution |

**Version**: 1.0.0 | **Ratified**: 2026-02-11 | **Last Amended**: 2026-02-11
