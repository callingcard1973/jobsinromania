# AGENTS.md - Universal Classified Ads Platform

This document helps AI agents work effectively in this codebase.

## Project Overview

A scalable classified ads platform built with FastAPI (backend) and vanilla JavaScript/Bootstrap 5 (frontend). Users can create, manage, and publish advertisements across multiple categories with moderation capabilities.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy + PostgreSQL/SQLite
- Frontend: HTML5 + Bootstrap 5 + Vanilla JavaScript
- Auth: JWT-based with role system (User/Moderator/Admin)
- Deployment: Docker + Docker Compose

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/      # API route handlers
│   │   │   └── schemas/     # Pydantic models for request/response
│   │   ├── core/            # Config, database, security, deps
│   │   ├── models/          # SQLAlchemy ORM models
│   │   └── main.py          # FastAPI app initialization
│   ├── requirements.txt
│   └── run.py               # Application entry point
├── frontend/
│   ├── static/
│   │   ├── css/             # Stylesheets
│   │   └── js/              # Frontend JavaScript
│   └── templates/           # HTML templates (Jinja2)
├── docker-compose.yml
└── migrations/              # Database migrations (Alembic)
```

## Essential Commands

### Development
```bash
# Setup (from backend directory)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Run development server
python run.py
# Server runs on http://localhost:8000

# API Documentation
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Docker
```bash
# Build and run all services
docker-compose up --build

# Run in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend
```

### Database
```bash
# The app uses SQLAlchemy's Base.metadata.create_all() on startup
# For production migrations, use Alembic:
alembic upgrade head
```

## Architecture & Data Flow

### Core Concept: The "Ad" Entity
Everything revolves around `Ad` objects. Key flow:
1. User creates ad (status: `draft`)
2. User submits ad (status: `pending_review`)
3. Moderator approves/rejects
4. If approved, ad can be published (status: `published`)
5. Published ads are visible to public

### Database Models
- **User**: id, name, email, password_hash, role, created_at
- **Ad**: id, user_id, title, description, category, price, location, status, is_featured, etc.
- **AdMedia**: id, ad_id, file_path, thumbnail_path (images per ad)
- **ExternalPost**: id, ad_id, platform, external_id (for Facebook/external publishing)

### Role-Based Access Control
- **User**: Create/manage own ads, view published ads
- **Moderator**: Approve/reject/feature ads, view all ads
- **Admin**: All moderator permissions + user management + stats

### API Route Organization
Routes are grouped by domain:
- `/api/auth/*` - Authentication (register, login, current user)
- `/api/ads/*` - Ad CRUD, search, moderation actions
- `/api/ads/{id}/media/*` - Image upload/management
- `/api/admin/*` - Admin-only endpoints (users list, stats)

## Code Conventions & Patterns

### Backend (FastAPI)
- Use dependency injection for database sessions: `db: Session = Depends(get_db)`
- Use dependency injection for auth: `current_user: User = Depends(get_current_user)`
- Pydantic schemas in `app/api/schemas/` separate from models
- Response models use `response_model=SchemaName` in route decorators
- HTTP status codes via `status.HTTP_*` constants

### Database Models
- Use declarative base from `app/core/database.py`
- Relationships defined with `relationship()` and `back_populates`
- Timestamps: `created_at` with `server_default=func.now()`, `updated_at` with `onupdate=func.now()`
- Foreign keys cascade: `cascade="all, delete-orphan"`

### Frontend JavaScript
- API calls through `API` class in `api.js`
- Token storage: `localStorage.getItem('token')`
- All async functions use try/catch for error handling
- DOM manipulation after page load via `DOMContentLoaded` event

### Authentication Flow
1. User submits email/password to `/api/auth/login`
2. Server returns JWT access token
3. Client stores token in localStorage
4. Subsequent requests include `Authorization: Bearer {token}` header
5. Server validates via `get_current_user` dependency

## Gotchas & Non-Obvious Patterns

### Import Paths
- Backend uses relative imports from `app/` package (e.g., `from ...core.database import get_db`)
- Three dots (`...`) go up two levels from `app/api/routes/` to `app/`

### Database Connection
- SQLite uses `check_same_thread=False` for async compatibility
- PostgreSQL URL should be changed in `.env` for production
- Database auto-created on first run via `Base.metadata.create_all()`

### File Uploads
- Images stored in `uploads/` directory (configurable via `UPLOAD_DIR`)
- Thumbnails auto-generated at 300x300px
- File validation checks both MIME type and file size
- Delete removes both file and thumbnail from disk

### Ad Status Workflow
- Ads start as `draft`
- Must be submitted (`pending_review`) before moderation
- Only `approved` ads can be `published`
- Only `published` ads visible to non-authenticated users
- Moderators see all statuses, public sees only `published`

### Frontend Routing
- No SPA router - uses separate HTML templates
- FastAPI serves templates via Jinja2
- Static files mounted at `/static/`
- JavaScript handles client-side logic only

### Security
- Passwords hashed with bcrypt via passlib
- JWT tokens expire based on `ACCESS_TOKEN_EXPIRE_MINUTES` env var
- All protected routes require Bearer token in Authorization header
- Role checks via separate dependencies: `get_current_moderator`, `get_current_admin`

### Search Implementation
- Full-text search uses SQL `ilike` on title AND description
- Filters: category, location, price range, featured flag
- Pagination via `skip` and `limit` query params (default: skip=0, limit=50)

## Testing Recommendations

When adding features, test:
1. API endpoints via Swagger UI (`/docs`)
2. Auth flow (register → login → protected endpoint)
3. Ad workflow (create → submit → approve → publish)
4. Role permissions (user vs moderator vs admin)
5. Image upload and display
6. Search and filtering

## Environment Configuration

Required `.env` variables:
- `DATABASE_URL` - SQLite or PostgreSQL connection string
- `SECRET_KEY` - JWT signing key (MUST change in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token lifetime
- `UPLOAD_DIR` - Image storage directory
- `MAX_UPLOAD_SIZE` - Max file size in bytes
- `ALLOWED_IMAGE_TYPES` - Comma-separated MIME types

## Important Files

- `backend/app/main.py` - FastAPI app setup, route registration
- `backend/app/core/deps.py` - Auth dependencies (current_user, current_moderator, etc.)
- `backend/app/core/security.py` - Password hashing, JWT creation/validation
- `backend/app/api/routes/ads.py` - Core ad CRUD and moderation
- `frontend/static/js/api.js` - Frontend API client class

## Deployment Notes

- Application runs on port 8000 (configurable in run.py)
- Docker Compose includes Redis (for future Celery integration)
- Images directory should be mounted as volume in production
- For PostgreSQL, use connection pooling and configure SSL
- Set `ENVIRONMENT=production` in production `.env`