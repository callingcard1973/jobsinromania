# Universal Classified Ads Platform

A scalable web platform for creating, managing, and publishing classified advertisements across multiple categories.

## Features

- User authentication with JWT
- Ad creation and management
- Moderation system (approve/reject/feature ads)
- Search and filtering
- Image upload with thumbnails
- Responsive Bootstrap 5 frontend
- Docker deployment ready

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (SQLite for development)
- **Frontend**: HTML5 + Bootstrap 5 + Vanilla JavaScript
- **Authentication**: JWT-based
- **ORM**: SQLAlchemy
- **Deployment**: Docker

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)

### Development Setup

1. Clone the repository and navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```bash
cp .env.example .env
```

5. Run the application:
```bash
python run.py
```

The API will be available at `http://localhost:8000`

### Docker Setup

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

The application will be available at `http://localhost:8000`

## API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/      # API endpoints
│   │   │   └── schemas/     # Pydantic models
│   │   ├── core/            # Configuration, database, security
│   │   ├── models/          # SQLAlchemy models
│   │   └── main.py          # FastAPI app
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── static/              # CSS and JS files
│   └── templates/           # HTML templates
├── docker-compose.yml
└── README.md
```

## User Roles

- **User**: Can create and manage their own ads
- **Moderator**: Can approve/reject ads, feature ads
- **Admin**: Full access including user management and stats

## Default Categories

- Real Estate
- Jobs
- Services
- Vehicles
- Electronics
- Agriculture
- Miscellaneous

## Environment Variables

- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: JWT secret key (change in production!)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `UPLOAD_DIR`: Directory for uploaded images
- `MAX_UPLOAD_SIZE`: Maximum image size in bytes
- `ALLOWED_IMAGE_TYPES`: Comma-separated list of allowed MIME types

## License

MIT