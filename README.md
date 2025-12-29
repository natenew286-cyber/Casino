# Casino Backend API

Django REST Framework backend for the Casino application with PostgreSQL, JWT authentication, OTP verification, and password reset functionality.

## Features

- **User Authentication**: JWT-based authentication with access and refresh tokens
- **Email Verification**: OTP-based email verification using Outlook SMTP
- **Password Security**: Argon2 password hashing
- **Password Reset**: Secure password reset via email links
- **PostgreSQL Database**: Production-ready database setup
- **Docker Support**: Containerized deployment

## Prerequisites

- Python 3.12+
- PostgreSQL 12+
- Docker (optional, for containerized deployment)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Django Secret Key (generate a new one for production)
SECRET_KEY=your-secret-key-here

# Database Configuration (PostgreSQL)
DB_NAME=casino_db
DB_USER=casino_user
DB_PASSWORD=casino_password
DB_HOST=localhost
DB_PORT=5432

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=900
JWT_REFRESH_TOKEN_LIFETIME=604800

# Email Configuration
# For Outlook: smtp-mail.outlook.com, port 587, TLS=True, SSL=False
# For QQ: smtp.qq.com, port 465, TLS=False, SSL=True
# For Gmail: smtp.gmail.com, port 587, TLS=True, SSL=False
EMAIL_HOST=smtp.qq.com
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@qq.com
EMAIL_HOST_PASSWORD=your-email-authorization-code

# Frontend URL (for password reset links)
FRONTEND_URL=http://localhost:3000

# OTP Configuration
OTP_EXPIRY_MINUTES=10
PASSWORD_RESET_TOKEN_EXPIRY_HOURS=1

# Redis Configuration (optional, for caching and Celery)
REDIS_URL=redis://localhost:6379/0

# Celery Configuration (optional)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Debug Mode (set to False in production)
DEBUG=True

# Allowed Hosts (comma-separated)
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Set up PostgreSQL Database

```bash
# Create database
createdb casino_db

# Or using psql
psql -U postgres
CREATE DATABASE casino_db;
CREATE USER casino_user WITH PASSWORD 'casino_password';
GRANT ALL PRIVILEGES ON DATABASE casino_db TO casino_user;
```

### 6. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create superuser (optional)

```bash
python manage.py createsuperuser
```

### 8. Run the development server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## Docker Setup

### Build the Docker image

```bash
docker build -t casino-backend .
```

### Run the container

```bash
docker run -d \
  --name casino-backend \
  -p 8000:8000 \
  --env-file .env \
  casino-backend
```

### Using Docker Compose (recommended)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: casino_db
      POSTGRES_USER: casino_user
      POSTGRES_PASSWORD: casino_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db

volumes:
  postgres_data:
```

Run with:

```bash
docker-compose up -d
```

## API Endpoints

### Authentication

#### Register User
- **POST** `/api/auth/register/`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123",
    "first_name": "John",
    "last_name": "Doe"
  }
  ```
- **Response**: User object and message to verify email

#### Verify OTP
- **POST** `/api/auth/verify-otp/`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "otp_code": "123456"
  }
  ```
- **Response**: Success message and verified user object

#### Resend OTP
- **POST** `/api/auth/resend-otp/`
- **Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```

#### Login
- **POST** `/api/auth/login/`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123"
  }
  ```
- **Response**: Access token, refresh token, and user object

#### Refresh Token
- **POST** `/api/auth/refresh/`
- **Body**:
  ```json
  {
    "refresh_token": "your-refresh-token"
  }
  ```
- **Response**: New access token and refresh token

#### Logout
- **POST** `/api/auth/logout/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "refresh_token": "your-refresh-token"
  }
  ```

### Password Reset

#### Request Password Reset
- **POST** `/api/auth/password-reset-request/`
- **Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response**: Success message (email sent)

#### Reset Password
- **POST** `/api/auth/password-reset/`
- **Body**:
  ```json
  {
    "token": "reset-token-from-email",
    "new_password": "newsecurepassword123"
  }
  ```

### User Profile

#### Get Profile
- **GET** `/api/auth/profile/`
- **Headers**: `Authorization: Bearer <access_token>`

#### Update Profile
- **PUT/PATCH** `/api/auth/profile/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**: Profile fields to update

#### Change Password
- **POST** `/api/auth/change-password/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "old_password": "oldpassword",
    "new_password": "newpassword"
  }
  ```

## JWT Authentication

### How JWT Tokens Work

1. **Access Token**: Short-lived token (default: 15 minutes) used for API requests
2. **Refresh Token**: Long-lived token (default: 7 days) used to obtain new access tokens

### Using JWT Tokens

Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Token Refresh Flow

When the access token expires:

1. Call `/api/auth/refresh/` with the refresh token
2. Receive new access and refresh tokens
3. Use the new access token for subsequent requests

## Email Configuration

### Email Provider Setup

The application supports multiple email providers. Configure the following environment variables:

#### QQ Email Setup (Recommended for Chinese users)
1. Use your QQ email address for `EMAIL_HOST_USER`
2. Get an authorization code from QQ Mail settings:
   - Go to QQ Mail → Settings → Account
   - Enable "POP3/SMTP Service" or "IMAP/SMTP Service"
   - Generate an authorization code (not your password)
3. Configuration:
   ```
   EMAIL_HOST=smtp.qq.com
   EMAIL_PORT=465
   EMAIL_USE_TLS=False
   EMAIL_USE_SSL=True
   EMAIL_HOST_USER=your-email@qq.com
   EMAIL_HOST_PASSWORD=your-authorization-code
   ```

#### Outlook SMTP Setup
1. Use your Outlook email address for `EMAIL_HOST_USER`
2. For Outlook, you may need to:
   - Enable "Less secure app access" or use an App Password
   - Use `smtp-mail.outlook.com` as the host
   - Port 587 with TLS enabled
3. Configuration:
   ```
   EMAIL_HOST=smtp-mail.outlook.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_USE_SSL=False
   EMAIL_HOST_USER=your-email@outlook.com
   EMAIL_HOST_PASSWORD=your-email-password
   ```

#### Gmail Setup
1. Use your Gmail address for `EMAIL_HOST_USER`
2. Enable "Less secure app access" or use an App Password
3. Configuration:
   ```
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_USE_SSL=False
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   ```

### Testing Email

To test email sending:

```python
from django.core.mail import send_mail

send_mail(
    'Test Subject',
    'Test message',
    'from@outlook.com',
    ['to@example.com'],
    fail_silently=False,
)
```

## Security Features

- **Argon2 Password Hashing**: Industry-standard password hashing
- **JWT Token Security**: Secure token generation and validation
- **OTP Expiration**: OTPs expire after 10 minutes
- **Password Reset Token Expiration**: Reset tokens expire after 1 hour
- **Input Validation**: All inputs are validated and sanitized
- **Environment Variables**: Sensitive data stored in `.env`

## Database Configuration

The application uses PostgreSQL. Configure the connection using environment variables:

- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Linting

```bash
flake8 .
```

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Set a strong `SECRET_KEY`
3. Configure proper `ALLOWED_HOSTS`
4. Use a production database
5. Set up proper email service
6. Use HTTPS
7. Configure proper CORS settings
8. Set up monitoring and logging

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check database credentials in `.env`
- Ensure database exists and user has permissions

### Email Sending Issues

- Verify Outlook SMTP credentials
- Check if App Password is required
- Verify network connectivity
- Check email service logs

### JWT Token Issues

- Verify `SECRET_KEY` is set
- Check token expiration settings
- Ensure tokens are included in requests

## License

[Your License Here]
