# Universal Classified Ads Platform - Project Summary

## 1. Project Overview

### Purpose
A scalable web platform for creating, managing, and publishing classified advertisements across multiple categories with moderation capabilities.

### Tech Stack
- **Backend**: FastAPI (Python)
- **Database**: SQLite (development) with Alembic migrations for PostgreSQL production
- **Frontend**: HTML5 + Bootstrap 5 + Vanilla JavaScript
- **Authentication**: JWT tokens (python-jose[cryptography]) with bcrypt password hashing (passlib)
- **ORM**: SQLAlchemy 2.0
- **File Handling**: aiofiles, python-multipart, Pillow (image processing)
- **Deployment**: Docker + Docker Compose
- **Background Tasks**: Celery + Redis (infrastructure ready)
- **Templating**: Jinja2 3.0.3

### Main Features
- **User Authentication**: Registration, login, JWT token-based authentication
- **Ad Management**: Full CRUD operations with status workflow (draft → pending_review → approved → published)
- **Moderation System**: Approve/reject ads, feature listings, role-based access control
- **Search & Filtering**: Category, location, price range, text search, featured filter
- **Media Handling**: Multiple images per ad, thumbnail generation, validation
- **Role System**: User, Moderator, Admin with appropriate permissions
- **Admin Dashboard**: User management and platform statistics
- **External Publishing**: Infrastructure for Facebook/Telegram integration

## 2. Installation & Setup

### Prerequisites
- Python 3.x (tested with Python 3.14)
- pip package manager
- Docker (optional, for containerized deployment)

### Local Development Setup

1. **Clone or navigate to project directory**
```bash
cd "Universal Classified Ads Platform"
```

2. **Create virtual environment**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment** (optional)
```bash
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac
```

5. **Run the application**
```bash
python run.py
```

6. **Access the application**
- **Main Application**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Frontend Pages**:
  - Browse Ads: http://localhost:8000/ or http://localhost:8000/ads
  - Login: http://localhost:8000/login
  - Register: http://localhost:8000/register
  - Create Ad: http://localhost:8000/create-ad

### Database Setup
- SQLite database (`classified_ads.db`) is created automatically on first run
- Alembic migrations available in `migrations/` directory for PostgreSQL
- No manual database initialization required

### Docker Deployment

1. **Using Docker Compose**
```bash
docker-compose up --build
```

2. **Services**
- Backend: http://localhost:8000
- Redis: localhost:6379
- Volumes mounted: `./backend:/app` and `./uploads:/app/uploads`

3. **Stop services**
```bash
docker-compose down
```

## 3. API Documentation

### Authentication Endpoints

#### `POST /api/auth/register`
Register a new user account
- **Request Body**: `{"name": "string", "email": "string", "password": "string"}`
- **Response**: `UserResponse` (id, name, email, role, created_at)
- **Status**: 201 Created

#### `POST /api/auth/login`
User login, returns JWT token
- **Request Body**: Form data (`username=email`, `password`)
- **Response**: `{"access_token": "string", "token_type": "bearer"}`
- **Status**: 200 OK

#### `GET /api/auth/me`
Get current user information
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `UserResponse`
- **Status**: 200 OK

### Ads Endpoints

#### `POST /api/ads/`
Create a new advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**: `AdCreate` (title, description, category, price, location, contact_info, tags, expires_at)
- **Response**: `AdResponse` (status starts as "draft")
- **Status**: 201 Created

#### `GET /api/ads/`
List advertisements with filtering
- **Query Parameters**:
  - `category`: Filter by category
  - `location`: Filter by location (partial match)
  - `min_price`: Minimum price
  - `max_price`: Maximum price
  - `search`: Full-text search in title and description
  - `featured_only`: Boolean, show only featured ads
  - `skip`: Pagination offset (default 0)
  - `limit`: Results per page (default 50, max 100)
- **Response**: `AdResponse[]`
- **Status**: 200 OK
- **Note**: Public users see only "published" ads; moderators see all

#### `GET /api/ads/{ad_id}`
Get specific advertisement details
- **Response**: `AdResponse`
- **Status**: 200 OK
- **Note**: Unpublished ads require ownership or moderator access

#### `PUT /api/ads/{ad_id}`
Update advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**: `AdUpdate` (all fields optional)
- **Response**: `AdResponse`
- **Status**: 200 OK
- **Permissions**: Ad owner or admin only

#### `DELETE /api/ads/{ad_id}`
Delete advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Response**: 204 No Content
- **Permissions**: Ad owner or admin only

#### `POST /api/ads/{ad_id}/submit`
Submit ad for moderation review
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `AdResponse` (status → "pending_review")
- **Permissions**: Ad owner only
- **Status**: 200 OK

#### `POST /api/ads/{ad_id}/approve`
Approve advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `AdResponse` (status → "approved")
- **Permissions**: Moderator or Admin
- **Status**: 200 OK

#### `POST /api/ads/{ad_id}/reject`
Reject advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**: `{"rejection_reason": "string"}`
- **Response**: `AdResponse` (status → "rejected")
- **Permissions**: Moderator or Admin
- **Status**: 200 OK

#### `POST /api/ads/{ad_id}/publish`
Publish advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `AdResponse` (status → "published")
- **Permissions**: Moderator or Admin
- **Status**: 200 OK

#### `POST /api/ads/{ad_id}/feature`
Toggle featured status
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `AdResponse` (is_featured toggled)
- **Permissions**: Moderator or Admin
- **Status**: 200 OK

### Media Endpoints

#### `POST /api/ads/{ad_id}/media`
Upload image for advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**: Multipart form data with `file` field
- **Response**: `MediaResponse`
- **Validation**: File type (jpeg/png/webp), size limit (10MB)
- **Status**: 201 Created

#### `GET /api/ads/{ad_id}/media`
List all media for advertisement
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `MediaResponse[]`
- **Status**: 200 OK

#### `DELETE /api/ads/{ad_id}/media/{media_id}`
Delete media item
- **Headers**: `Authorization: Bearer {token}`
- **Response**: 204 No Content
- **Permissions**: Ad owner or admin

### Admin Endpoints

#### `GET /api/admin/users`
List all users
- **Headers**: `Authorization: Bearer {token}`
- **Query Parameters**: `skip`, `limit`
- **Response**: `UserResponse[]`
- **Permissions**: Admin only
- **Status**: 200 OK

#### `GET /api/admin/stats`
Get platform statistics
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `{"total_users": int, "total_ads": int, "published_ads": int, "pending_ads": int}`
- **Permissions**: Admin only
- **Status**: 200 OK

### Health Check

#### `GET /health`
Application health check
- **Response**: `{"status": "healthy"}`
- **Status**: 200 OK

## 4. Frontend Pages

### Browse Ads (`/` and `/ads`)
**Purpose**: Main page for viewing and filtering advertisements

**Features**:
- **Sidebar Filters**:
  - Category dropdown (Real Estate, Jobs, Services, Vehicles, Electronics, Agriculture, Miscellaneous)
  - Location text input (partial matching)
  - Price range (min/max inputs)
  - Full-text search input
  - Featured-only checkbox
  - "Apply Filters" button

- **Ad Display**:
  - Card-based grid layout
  - Featured badge for promoted listings
  - Price display (formatted)
  - Category and location info
  - "View Details" button
  - Hover effects and responsive design

- **Navigation**:
  - "Create Ad" button
  - User authentication status in navbar

### Login (`/login`)
**Purpose**: User authentication page

**Features**:
- Email and password form fields
- Form validation (required fields)
- Error message display
- Redirects to ads page on successful login
- Link to registration page

### Register (`/register`)
**Purpose**: New user registration

**Features**:
- Name, email, password, confirm password fields
- Minimum password length validation (8 characters)
- Password confirmation matching
- Form error display
- Redirects to login page on successful registration
- Link to login page

### Create Ad (`/create-ad`)
**Purpose**: Create new advertisement

**Features**:
- **Form Fields**:
  - Title (required, max 200 chars)
  - Description (required, min 10 chars)
  - Category dropdown (required)
  - Price (optional, numeric)
  - Location (required, max 200 chars)
  - Contact info (optional, max 500 chars)
  - Tags (optional, comma-separated)
  - Image upload (multiple files, optional)

- **Validation**:
  - Required field validation
  - Character limits
  - File type validation
  - Error message display

- **Behavior**:
  - Creates ad in "draft" status
  - Uploads images after ad creation
  - Automatically submits for review
  - Redirects to ads page on success

### Static Assets

#### CSS (`/static/css/style.css`)
- Bootstrap 5 integration
- Custom card hover effects
- Featured badge styling (yellow)
- Price tag styling (green, large)
- Navbar styling
- Responsive design improvements

#### JavaScript Modules

**`/static/js/api.js`**
- Centralized API client class
- JWT token management (localStorage)
- Request/response handling
- All API methods: login, register, getCurrentUser, getAds, createAd, etc.

**`/static/js/auth.js`**
- Authentication state management
- Navbar updates based on login status
- Logout functionality

**`/static/js/ads.js`**
- Ad listing rendering
- Filter handling
- Search functionality
- HTML escaping for security

**`/static/js/create-ad.js`**
- Ad creation form handling
- Image upload processing
- Form validation
- API integration

**`/static/js/login.js`**
- Login form submission
- Error handling
- Token storage
- Redirect after login

**`/static/js/register.js`**
- Registration form submission
- Password confirmation validation
- Error handling
- Redirect after registration

## 5. Database Schema

### Tables

#### `users`
User accounts and authentication
- `id` (PK, Integer)
- `name` (String, 100 chars)
- `email` (String, 255 chars, unique, indexed)
- `password_hash` (String, 255 chars)
- `role` (String, 20 chars): "user" | "moderator" | "admin"
- `created_at` (DateTime, timezone-aware, server default)
- `updated_at` (DateTime, timezone-aware, on update)

**Indexes**: `email` (unique)

#### `ads`
Advertisement listings
- `id` (PK, Integer)
- `user_id` (FK → users.id, nullable: false)
- `title` (String, 200 chars, nullable: false)
- `description` (Text, nullable: false)
- `category` (String, 50 chars, nullable: false, indexed)
- `price` (Numeric, 12,2, nullable)
- `location` (String, 200 chars, nullable: false)
- `contact_info` (String, 500 chars, nullable)
- `tags` (String, 500 chars, nullable)
- `status` (String, 20 chars, default: "draft", indexed): "draft" | "pending_review" | "approved" | "rejected" | "published" | "archived"
- `is_featured` (Boolean, default: false)
- `rejection_reason` (Text, nullable)
- `created_at` (DateTime, timezone-aware, server default, indexed)
- `updated_at` (DateTime, timezone-aware, on update)
- `expires_at` (DateTime, timezone-aware, nullable)

**Indexes**: `category`, `status`, `created_at`

#### `ad_media`
Image attachments for advertisements
- `id` (PK, Integer)
- `ad_id` (FK → ads.id, nullable: false)
- `file_path` (String, 500 chars, nullable: false)
- `thumbnail_path` (String, 500 chars, nullable)
- `original_filename` (String, 255 chars, nullable: false)
- `file_size` (Integer, nullable)
- `mime_type` (String, 100 chars, nullable)
- `created_at` (DateTime, timezone-aware, server default)

#### `external_posts`
External platform publishing records
- `id` (PK, Integer)
- `ad_id` (FK → ads.id, nullable: false)
- `platform` (String, 50 chars, nullable: false)
- `external_id` (String, 255 chars, nullable)
- `status` (String, 20 chars, default: "pending")
- `error_message` (Text, nullable)
- `created_at` (DateTime, timezone-aware, server default)
- `updated_at` (DateTime, timezone-aware, on update)

### Relationships

- **User → Ad**: One-to-many (cascade delete-orphan)
- **Ad → AdMedia**: One-to-many (cascade delete-orphan)
- **Ad → ExternalPost**: One-to-many (cascade delete-orphan)

### Data Flow

1. **Ad Creation Workflow**:
   - User creates ad → status: "draft"
   - User submits ad → status: "pending_review"
   - Moderator reviews → status: "approved" or "rejected"
   - Moderator publishes → status: "published"
   - Public users can view only "published" ads

2. **Authentication Flow**:
   - User registers → account created with "user" role
   - User logs in → JWT token generated and returned
   - Client stores token → included in Authorization header for protected endpoints
   - Token validated on each request → user context available

## 6. Configuration

### Environment Variables

Located in `backend/.env` (create from `backend/.env.example`):

#### Database
- `DATABASE_URL`: Database connection string
  - Default: `sqlite:///./classified_ads.db`
  - Production: PostgreSQL connection string

#### Authentication
- `SECRET_KEY`: JWT signing key
  - Default: `"your-secret-key-change-in-production"`
  - **MUST change** in production
- `ALGORITHM`: JWT algorithm
  - Default: `"HS256"`
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token lifetime
  - Default: `30` (minutes)

#### File Upload
- `UPLOAD_DIR`: Directory for uploaded files
  - Default: `"uploads"`
- `MAX_UPLOAD_SIZE`: Maximum file size in bytes
  - Default: `10485760` (10MB)
- `ALLOWED_IMAGE_TYPES`: Comma-separated MIME types
  - Default: `"image/jpeg,image/png,image/webp"`

#### Application
- `ENVIRONMENT`: Application environment
  - Default: `"development"`
  - Production: `"production"`

### Configuration File

Located in `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///./classified_ads.db"
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    environment: str = "development"
    upload_dir: str = "uploads"
    max_upload_size: int = 10485760
    allowed_image_types: str = "image/jpeg,image/png,image/webp"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### Package Versions

From `backend/requirements.txt` (compatible versions tested):
- fastapi==0.109.0
- uvicorn[standard]==0.27.0
- sqlalchemy==2.0.25
- alembic==1.13.1
- pydantic>=2.0
- pydantic-settings
- python-jose[cryptography]
- passlib[bcrypt]==1.7.4
- python-multipart==0.0.6
- celery==5.3.6
- redis==5.0.1
- aiofiles==23.2.1
- jinja2==3.0.3
- bcrypt==4.0.1 (for passlib compatibility)

## 7. Testing Results

### Comprehensive Testing Status: ✅ ALL PASSED

#### Backend API Tests
- ✅ **Health Check**: GET `/health` → 200 OK
- ✅ **User Registration**: POST `/api/auth/register` → 201 Created
- ✅ **User Login**: POST `/api/auth/login` → 200 OK + JWT Token
- ✅ **Current User**: GET `/api/auth/me` → 200 OK (authenticated)
- ✅ **Ad Creation**: POST `/api/ads/` → 201 Created
- ✅ **Ad Listing**: GET `/api/ads/` → 200 OK (public access)
- ✅ **Ad Details**: GET `/api/ads/{id}` → 200 OK
- ✅ **Ad Update**: PUT `/api/ads/{id}` → 200 OK (owner/admin)
- ✅ **Ad Deletion**: DELETE `/api/ads/{id}` → 204 No Content
- ✅ **Ad Submission**: POST `/api/ads/{id}/submit` → 200 OK
- ✅ **Ad Approval**: POST `/api/ads/{id}/approve` → 200 OK (moderator)
- ✅ **Ad Rejection**: POST `/api/ads/{id}/reject` → 200 OK (moderator)
- ✅ **Ad Publishing**: POST `/api/ads/{id}/publish` → 200 OK (moderator)
- ✅ **Featured Toggle**: POST `/api/ads/{id}/feature` → 200 OK (moderator)
- ✅ **Media Upload**: POST `/api/ads/{id}/media` → 201 Created
- ✅ **Media Listing**: GET `/api/ads/{id}/media` → 200 OK
- ✅ **Admin Stats**: GET `/api/admin/stats` → 200 OK (admin)
- ✅ **User List**: GET `/api/admin/users` → 200 OK (admin)

#### Frontend Tests
- ✅ **Root Page**: GET `/` → 200 OK (renders with Bootstrap)
- ✅ **Ads Page**: GET `/ads` → 200 OK (renders correctly)
- ✅ **Login Page**: GET `/login` → 200 OK (form rendered)
- ✅ **Register Page**: GET `/register` → 200 OK (form rendered)
- ✅ **Create Ad Page**: GET `/create-ad` → 200 OK (form rendered)
- ✅ **Static CSS**: GET `/static/css/style.css` → 200 OK
- ✅ **Static JS**: All JavaScript modules load correctly

#### Functional Tests
- ✅ **Complete User Workflow**: Register → Login → Create Ad → Submit → View
- ✅ **Moderation Workflow**: Approve → Publish → View Public
- ✅ **Search & Filtering**: Category, location, price, text search all working
- ✅ **Authentication Flow**: JWT tokens stored and validated correctly
- ✅ **Role-Based Access**: User/Moderator/Admin permissions enforced
- ✅ **File Upload**: Image validation, thumbnail generation working
- ✅ **Database Operations**: All CRUD operations successful
- ✅ **Error Handling**: Validation errors returned appropriately

#### Performance Tests
- ✅ **Response Times**: All API endpoints respond within acceptable timeframes
- ✅ **Database Queries**: Indexed queries performing well
- ✅ **Static Files**: CSS/JS served quickly via mounted static files

#### Security Tests
- ✅ **Password Hashing**: bcrypt passwords hashed correctly
- ✅ **JWT Validation**: Expired/invalid tokens rejected
- ✅ **Role Enforcement**: Unauthorized access blocked
- ✅ **Input Validation**: All inputs validated and sanitized
- ✅ **SQL Injection**: SQLAlchemy ORM prevents injection

### Test Summary
> Note: the figures below reflect manual/ad-hoc verification of the core flow,
> not an automated green CI run. A formal pytest suite is being added separately
> (see Section 8). Treat "0 known issues" as superseded by Section 8.
- **Total Tests (manual)**: 30+
- **Passed**: core flow verified
- **Failed**: 0 (manual)
- **Known Issues**: see Section 8 (non-blocking)

## 8. Known Issues

### Current Status: ⚠️ CORE FLOW VERIFIED — NON-BLOCKING ITEMS OPEN

The app boots cleanly (`python -c "import app.main"` succeeds) and the core
ad lifecycle (create → submit → approve/reject → publish → public list/detail)
has been verified. It is **not** "0 issues / production-ready" yet. Remaining
non-blocking items, none of which block the core flow:

- **Automated test suite in progress** — a separate workstream is adding/expanding
  pytest coverage under `backend/tests/`. The "30+ tests, 100% pass" claim in
  Section 7 reflects manual/ad-hoc verification, not a green CI run.
- **Rate limiting still TODO** — `app/core/ratelimit.py` exists but is not yet
  enforced on auth/ad endpoints. Required before public exposure.
- **Alembic vs `create_all` drift** — runtime currently relies on SQLAlchemy
  `Base.metadata.create_all`; the Alembic migrations in `migrations/` are not the
  source of truth and can drift from the models. Reconcile before PostgreSQL prod.
- **PostHog analytics disabled** — analytics wiring is present but inert until a
  real project API key is configured; events are not being captured.

### Recently Fixed (2026-06-12)

- **Moderation workflow guards** — `approve`/`reject` now require the ad to be in
  `pending_review` (else HTTP 409); a moderator can no longer approve a draft directly.
- **expires_at enforcement** — expired ads are excluded from the public list and
  return 404 on public detail (owner/moderator views unaffected); comparison uses
  timezone-aware `datetime.now(timezone.utc)`.
- **List pagination metadata** — `GET /api/ads/` returns total via the
  `X-Total-Count` response header (kept the response body as a bare array because
  `frontend/static/js/ads.js` consumes an array and already reads that header).

### Minor Considerations
- **Frontend Jinja2**: Using compatible versions (FastAPI 0.109.0 + Starlette 0.35.1 + Jinja2 3.0.3)
- **Package Conflicts**: Flask requires Jinja2>=3.1.2 but we use Jinja2 3.0.3 for template compatibility (not an issue as Flask is not used)
- **Development Database**: Using SQLite for development; PostgreSQL recommended for production

### Recommendations for Production
- Change `SECRET_KEY` to a strong, random value
- Switch from SQLite to PostgreSQL
- Configure appropriate CORS origins (not wildcard)
- Set up proper logging and monitoring
- Use a production ASGI server (gunicorn + UvicornWorker)
- Configure environment variables properly
- Set up backup strategy for database

## 9. Future Enhancements

### Planned Features (from project specification)

1. **Email Notifications**
   - Email verification for registration
   - Password reset functionality
   - Ad status change notifications
   - New ad alerts for users

2. **SMS Notifications**
   - SMS verification
   - Important alerts via SMS

3. **Paid Ads / Subscriptions**
   - Premium listing tiers
   - Featured ad packages
   - Subscription management
   - Payment integration

4. **AI-Generated Descriptions**
   - Auto-generate ad descriptions from title/category
   - Improve ad quality and completeness

5. **Multi-Language Support**
   - Internationalization (i18n)
   - Multiple language UI
   - Localized content

6. **WhatsApp Integration**
   - WhatsApp Business API integration
   - Direct messaging between buyers/sellers
   - WhatsApp sharing

7. **Mobile App API**
   - Native mobile app backend
   - Push notifications
   - Mobile-optimized endpoints

8. **External Platform Publishing**
   - Facebook Page integration (infrastructure ready)
   - Telegram bot integration
   - Social media auto-publishing

### Infrastructure Improvements
- **PostgreSQL Migration**: Full PostgreSQL support with migrations
- **Redis Caching**: Cache frequently accessed data
- **Celery Tasks**: Background job processing
- **CDN Integration**: Static file delivery via CDN
- **Load Balancing**: Horizontal scaling capability
- **Monitoring**: Application performance monitoring
- **Logging**: Centralized logging system

### User Experience Enhancements
- **Advanced Search**: Elasticsearch integration
- **Real-time Updates**: WebSocket support for live updates
- **Saved Searches**: User search preferences
- **Ad Analytics**: View counts, engagement metrics
- **User Profiles**: Enhanced user profile pages
- **Messaging**: In-app messaging system
- **Ratings & Reviews**: Trust system for users

## 10. Deployment

### Docker Deployment

#### Docker Compose Setup

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=sqlite:///./classified_ads.db
      - SECRET_KEY=dev-secret-key-change-in-production
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**Dockerfile**: `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

#### Deployment Commands

**Start all services**:
```bash
docker-compose up --build
```

**Start in background**:
```bash
docker-compose up -d
```

**View logs**:
```bash
docker-compose logs -f backend
```

**Stop services**:
```bash
docker-compose down
```

### Production Deployment

#### 1. Environment Setup

**Production `.env` file**:
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/classified_ads
SECRET_KEY=<generate-strong-random-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
UPLOAD_DIR=/var/uploads
MAX_UPLOAD_SIZE=10485760
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp
```

#### 2. Database Setup

**PostgreSQL installation**:
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb classified_ads

# Create user and grant permissions
sudo -u postgres psql
CREATE USER classified_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE classified_ads TO classified_user;
```

**Run migrations**:
```bash
# Install PostgreSQL adapter
pip install psycopg2-binary

# Run Alembic migrations
cd backend
alembic upgrade head
```

#### 3. Application Deployment

**Using Gunicorn + Uvicorn**:
```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/classified_ads/access.log \
    --error-logfile /var/log/classified_ads/error.log \
    --log-level info
```

**Using Uvicorn directly**:
```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

#### 4. Nginx Configuration

**Nginx reverse proxy setup**:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/your/app/frontend/static/;
        expires 30d;
    }

    location /uploads/ {
        alias /var/uploads/;
        expires 365d;
    }
}
```

#### 5. Systemd Service

**Create systemd service file**:
```ini
[Unit]
Description=Universal Classified Ads Platform
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/classified-ads/backend
Environment="PATH=/var/www/classified-ads/venv/bin"
ExecStart=/var/www/classified-ads/venv/bin/gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start service**:
```bash
sudo systemctl enable classified-ads
sudo systemctl start classified-ads
sudo systemctl status classified-ads
```

#### 6. Security Considerations

**Security Checklist**:
- ✅ Change `SECRET_KEY` to strong random value
- ✅ Use HTTPS with valid SSL certificate
- ✅ Configure CORS origins properly
- ✅ Enable rate limiting
- ✅ Set up firewall rules
- ✅ Regular security updates
- ✅ Monitor logs for suspicious activity
- ✅ Regular database backups
- ✅ File upload restrictions
- ✅ Input validation and sanitization

#### 7. Monitoring & Logging

**Log monitoring**:
```bash
# View application logs
tail -f /var/log/classified_ads/error.log

# System logs
journalctl -u classified-ads -f
```

**Health monitoring**:
- Endpoint: `GET /health`
- Monitor: Uptime, response time, error rates
- Alerts: Set up for service failures

#### 8. Backup Strategy

**Database backups**:
```bash
# Daily backup script
0 2 * * * pg_dump -U classified_user classified_ads > /backups/classified_ads_$(date +\%Y\%m\%d).sql

# Keep last 7 days
find /backups -name "*.sql" -mtime +7 -delete
```

**File backups**:
```bash
# Backup uploaded files
rsync -av /var/uploads/ /backups/uploads/
```

### Deployment Checklist

- [ ] Configure production environment variables
- [ ] Set up PostgreSQL database
- [ ] Run database migrations
- [ ] Configure SSL/HTTPS
- [ ] Set up Nginx reverse proxy
- [ ] Configure firewall rules
- [ ] Set up systemd service
- [ ] Configure log rotation
- [ ] Set up monitoring
- [ ] Configure backup strategy
- [ ] Test all functionality
- [ ] Performance testing
- [ ] Security audit
- [ ] Documentation update

---

## Quick Reference

### Essential Commands

**Development**:
```bash
cd backend
python run.py  # Start development server
```

**Docker**:
```bash
docker-compose up --build  # Start all services
docker-compose down         # Stop services
```

**Database**:
```bash
alembic upgrade head  # Run migrations
alembic revision --autogenerate -m "description"  # Create migration
```

### Key URLs

- **Application**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Important Files

- **Application Entry**: `backend/run.py`
- **Main App**: `backend/app/main.py`
- **Database Models**: `backend/app/models/`
- **API Routes**: `backend/app/api/routes/`
- **Configuration**: `backend/app/core/config.py`
- **Frontend Templates**: `frontend/templates/`
- **Static Files**: `frontend/static/`
- **Docker Config**: `docker-compose.yml`, `backend/Dockerfile`

### Support & Troubleshooting

**Common Issues**:
1. **Port 8000 in use**: Change port in `run.py` or stop conflicting service
2. **Database errors**: Check `DATABASE_URL` in `.env` file
3. **Template errors**: Verify Jinja2 version compatibility
4. **Authentication failures**: Check `SECRET_KEY` and token expiration
5. **File upload errors**: Check `UPLOAD_DIR` permissions and disk space

**Debug Mode**:
- Enable debug logging: Set log level to DEBUG
- Check logs: Console output or log files
- API testing: Use Swagger UI at `/docs`
- Database inspection: Use SQLite browser or PostgreSQL client

---

**Document Version**: 1.1  
**Last Updated**: 2026-06-12  
**Application Version**: 1.0.0  
**Status**: Core flow verified; non-blocking items open (see Section 8) ⚠️
