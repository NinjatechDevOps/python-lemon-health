# Lemon Health Authentication Module User Guide

## Overview

The Lemon Health Authentication Module is a modular, plug-and-play authentication and authorization system built for FastAPI applications. It provides a comprehensive solution for user management, authentication, token handling, OTP verification, and role-based access control.

## Features

- One-line integration with `AuthModule(app, config)`
- Mobile authentication with SMS verification
- Extensible authentication provider system
- JWT-based access and refresh token management
- OTP services with Twilio integration
- Role-based access control (RBAC)
- Configurable settings with sensible defaults

## Quick Start

### 1. Installation

First, ensure you have the required dependencies:

```bash
pip install fastapi uvicorn pydantic sqlalchemy passlib[bcrypt]==1.7.4 bcrypt==3.2.2 python-jose[cryptography] python-multipart twilio
```

### 2. Integration

In your main application file:

```python
from fastapi import FastAPI
from auth.main import AuthModule

# Initialize FastAPI app
app = FastAPI()

# Initialize the Auth Module with one line
auth_module = AuthModule(app, {
    "SECRET_KEY": "your-secret-key",
    "DATABASE_URL": "postgresql+asyncpg://user:password@localhost/dbname",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    "REFRESH_TOKEN_EXPIRE_DAYS": 7,
    "TWILIO_ACCOUNT_SID": "your-twilio-sid",
    "TWILIO_AUTH_TOKEN": "your-twilio-token",
    "TWILIO_PHONE_NUMBER": "your-twilio-phone",
    "ENABLE_MOBILE_AUTH": True
})
```

That's it! The module automatically registers all necessary routes and initializes the database tables.

## Configuration Options

The `AuthModule` accepts the following configuration options:

| Option | Description | Default |
|--------|-------------|---------|
| `SECRET_KEY` | Secret key for JWT token generation | Required |
| `DATABASE_URL` | Database connection string | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiration time in minutes | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiration time in days | 90 |
| `TWILIO_ACCOUNT_SID` | Twilio account SID for SMS | Optional |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Optional |
| `TWILIO_PHONE_NUMBER` | Twilio phone number | Optional |
| `ENABLE_MOBILE_AUTH` | Enable mobile authentication | True |
| `ENABLE_EMAIL_AUTH` | Enable email authentication | False |
| `ENABLE_GOOGLE_AUTH` | Enable Google OAuth authentication | False |

## Available Endpoints

Once integrated, the following endpoints are available:

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login with mobile number and password
- `POST /api/auth/verify` - Verify mobile number with OTP
- `POST /api/auth/refresh-token` - Refresh access token
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password with verification code
- `POST /api/auth/change-password` - Change password (authenticated)
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/providers` - List available authentication providers

## Authentication Providers

The module uses a factory pattern for authentication providers, making it easy to add new authentication methods.

### Available Providers

- `mobile` - Mobile number authentication with SMS verification

### Adding a New Provider

To add a new authentication provider:

1. Create a new provider class that extends `AuthProvider`:

```python
from apps.auth.providers.base import AuthProvider

class EmailAuthProvider(AuthProvider):
    async def authenticate(self, db, credentials):
        # Implementation
        pass
        
    async def register(self, db, user_data):
        # Implementation
        pass
```

2. Register the provider in the factory:

```python
from apps.auth.providers.base import AuthProviderFactory
AuthProviderFactory.register_provider("email", EmailAuthProvider)
```

## OTP Service

The module includes an OTP service for verification codes:

```python
from apps.auth.services.otp import otp_service

# Create verification code
success, message = await otp_service.create_verification_code(
    db=db,
    verification_type=VerificationType.SIGNUP,
    recipient="1234567890",
    country_code="+1",
    user_id=user.id
)

# Verify code
success, message = await otp_service.verify_code(
    db=db,
    verification_type=VerificationType.SIGNUP,
    recipient="1234567890",
    country_code="+1",
    code="123456",
    user_id=user.id
)
```

### Adding a New OTP Provider

The OTP service uses a provider pattern. To add a new provider:

1. Create a new provider class that extends `OTPProvider`:

```python
from apps.auth.services.otp import OTPProvider

class EmailOTPProvider(OTPProvider):
    async def send_otp(self, recipient, message):
        # Implementation
        pass
```

2. Create an instance of the OTP service with your provider:

```python
email_otp_service = OTPService(EmailOTPProvider())
```

## Token Service

The module includes a token service for JWT token management:

```python
from apps.auth.services.token import token_service

# Create access token
access_token = token_service.create_access_token(
    subject=str(user.id),
    extra_data={"is_verified": user.is_verified}
)

# Create refresh token
refresh_token = token_service.create_refresh_token(
    subject=str(user.id)
)

# Verify token
token_data = token_service.verify_token(token)
```

## Role-Based Access Control

The module includes a role-based access control system:

### Models

- `Role` - Represents a role in the system
- `Permission` - Represents a permission in the system
- Many-to-many relationships between users and roles, and roles and permissions

### Dependencies

Use these dependencies to protect your endpoints:

```python
from apps.accounts.deps import has_permission, has_role

@app.get("/admin", dependencies=[Depends(has_role("admin"))])
async def admin_endpoint():
    return {"message": "Admin access"}

@app.get("/users", dependencies=[Depends(has_permission("read:users"))])
async def list_users():
    return {"message": "Users list"}
```

## Database Models

The module includes the following database models:

- `User` - Core user model with authentication information
- `VerificationCode` - For storing OTP verification codes
- `Profile` - For storing additional user information
- `Role` - For RBAC roles
- `Permission` - For RBAC permissions

## Best Practices

1. **Security**: Always use HTTPS in production to protect tokens and credentials.
2. **Configuration**: Store sensitive configuration in environment variables.
3. **Token Storage**: Store tokens securely on the client side.
4. **Password Handling**: Never store plain text passwords; the module uses bcrypt for hashing.

## Extending the Module

The module is designed to be extensible:

1. **New Authentication Methods**: Add new providers by extending `AuthProvider`.
2. **New OTP Providers**: Add new OTP providers by extending `OTPProvider`.
3. **Custom User Fields**: Extend the `User` model with additional fields.
4. **Custom Endpoints**: Add custom endpoints to the router.

## Troubleshooting

- **Token Issues**: Ensure your `SECRET_KEY` is consistent and secure.
- **SMS Not Sending**: Check your Twilio credentials and phone number.
- **Database Errors**: Ensure your database is properly configured and migrations are applied.

## Security Considerations

- The module uses bcrypt for password hashing.
- JWT tokens are used for authentication with configurable expiration.
- OTP codes expire after a configurable time period.
- Role-based access control for fine-grained permissions.

## Conclusion

The Lemon Health Authentication Module provides a comprehensive solution for authentication and authorization in FastAPI applications. With its modular design and extensible architecture, it can be easily integrated into any project and customized to meet specific requirements. 