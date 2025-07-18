# Lemon Health API

Backend API for the Lemon Health mobile application, built with FastAPI and PostgreSQL.

## Overview

Lemon Health is a health and wellness application that provides personalized nutrition and exercise advice based on user profiles and blood test reports. This repository contains the backend API that powers the mobile application.

## Features

- User authentication with mobile number verification via SMS
- User profile management
- JWT-based authentication with refresh tokens
- PostgreSQL database with SQLAlchemy ORM
- Asynchronous API endpoints

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy (Async)
- **Migrations**: Alembic
- **Authentication**: JWT (jose)
- **SMS Verification**: Twilio
- **Dependency Management**: pip

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Twilio account (for SMS verification)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd python-lemon-health
```

### 2. Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Copy the example environment file and update it with your configuration:

```bash
cp .env.example .env
```

Edit the `.env` file with your database credentials, Twilio API keys, and other settings:

```
# Database
DATABASE_URL=postgresql://username:password@localhost/lemonhealth_db

# Security
SECRET_KEY="your-secret-key"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30000
REFRESH_TOKEN_EXPIRE_DAYS=90

# Twilio (for SMS)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone
TWILIO_VERIFY_SERVICE_SID=your-verify-service-sid
```

### 5. Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE lemonhealth_db;

# Exit PostgreSQL
\q
```

### 6. Run Database Migrations

```bash
alembic upgrade head
```

### 7. Start the API Server

```bash
# For development
python main.py

# Or using uvicorn directly
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

### 8. API Documentation

FastAPI automatically generates interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
python-lemon-health/
├── alembic/                  # Database migrations
├── apps/                     # Application modules
│   ├── auth/                 # Authentication module
│   │   ├── deps.py           # Dependencies (current user, etc.)
│   │   ├── models.py         # Database models
│   │   ├── routes.py         # API endpoints
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── services.py       # Business logic
│   │   └── twilio_service.py # SMS verification
│   ├── core/                 # Core functionality
│   │   ├── config.py         # Configuration
│   │   ├── db.py             # Database setup
│   │   └── security.py       # Security utilities
│   └── profile/              # User profile module
│       ├── models.py         # Database models
│       ├── routes.py         # API endpoints
│       ├── schemas.py        # Pydantic schemas
│       └── services.py       # Business logic
├── .env                      # Environment variables
├── .env.example              # Example environment variables
├── alembic.ini               # Alembic configuration
├── main.py                   # Application entry point
└── requirements.txt          # Python dependencies
```

## API Endpoints

### Authentication

- `POST /api/auth/register`: Register a new user
- `POST /api/auth/verify`: Verify mobile number with SMS code
- `POST /api/auth/resend-verification`: Resend verification code
- `POST /api/auth/login`: Login with mobile number and password
- `POST /api/auth/refresh-token`: Get new access token using refresh token
- `POST /api/auth/forgot-password`: Request password reset
- `POST /api/auth/reset-password`: Reset password with verification code
- `POST /api/auth/change-password`: Change password (authenticated)

### Profile

- `GET /api/profile/me`: Get current user's profile
- `POST /api/profile/`: Create a new profile
- `PUT /api/profile/`: Update profile
- `DELETE /api/profile/`: Delete profile

## Development

### Creating New Migrations

After making changes to the database models, create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Running Tests

```bash
# Coming soon
```

## License

[License information]

## Contact

For questions or support, please contact [contact information].
