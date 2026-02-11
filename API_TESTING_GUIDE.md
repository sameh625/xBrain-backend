# 🔐 Authentication API - Testing Guide

## 🚀 Setup Instructions

### 1. Install Dependencies
```bash
cd /home/sameh/4th/grad_project/xBrain
pip install -r requirements.txt
```

### 2. Gmail App Password Setup

⚠️ **IMPORTANT: You CANNOT use your regular Gmail password for SMTP!**

**Steps to create Gmail App Password:**
1. Go to your Google Account: https://myaccount.google.com/
2. Click "Security" in the left sidebar
3. Enable "2-Step Verification" (if not already enabled)
4. After enabling 2-Step, go back to Security
5. Scroll down to "2-Step Verification" section
6. Click on "App passwords"
7. Select app: "Mail"
8. Select device: "Other" (Custom name) → Enter "xBrain"
9. Click "Generate"
10. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)
11. Update `.env` file with this password (remove spaces):
    ```
    EMAIL_HOST_PASSWORD=abcdefghijklmnop
    ```

###3. Update .env File
```bash
# Email Configuration
EMAIL_HOST_USER=xBrain2026@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password-here
```

### 4. Run Migrations
```bash
python manage.py makemigrations api
python manage.py migrate
```

### 5. Seed Specializations
```bash
python seed_specializations.py
```

### 6. Start Development Server
```bash
python manage.py runserver
```

---

## 📡 API Endpoints

### Base URL
```
http://localhost:8000/api/
```

---

## 1. User Registration (Step 1: Send OTP)

### Endpoint
```
POST /api/auth/register/
```

### Request Body
```json
{
  "email": "user@example.com",
  "username": "johndoe123",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "bio": "Full-stack developer",
  "profile_image": null
}
```

### Field Requirements
- **email**: Valid email, unique
- **username**: 8-16 chars, starts with letter, case-insensitive, unique
- **password**: Min 8 chars, uppercase, number, special char
- **first_name**: Required
- **last_name**: Required
- **phone_number**: Required, 7-15 digits, unique
- **bio**: Optional
- **profile_image**: Optional (file upload)

### Success Response (200 OK)
```json
{
  "message": "OTP sent successfully. Please check your email for verification code.",
  "email": "user@example.com"
}
```

### Error Responses

**Email already exists (400 Bad Request)**
```json
{
  "email": ["This email is already registered."]
}
```

**Username already taken (400 Bad Request)**
```json
{
  "username": ["This username is already taken."]
}
```

**Weak password (400 Bad Request)**
```json
{
  "password": ["Password must contain at least one uppercase letter"]
}
```

**Invalid phone number (400 Bad Request)**
```json
{
  "phone_number": ["Enter a valid phone number (7-15 digits, optional + prefix)."]
}
```

### cURL Example
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser123",
    "password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User",
    "phone_number": "+1234567890"
  }'
```

---

## 2. Verify Email (Step 2: Complete Registration)

### Endpoint
```
POST /api/auth/verify-email/
```

### Request Body
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

### Success Response (201 Created)
```json
{
  "message": "Email verified successfully. Welcome to xBrain!",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "username": "johndoe123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "bio": "Full-stack developer",
    "profile_image_url": null,
    "specializations": [],
    "wallet": {
      "id": "wallet-uuid",
      "balance": 0
    },
    "created_at": "2026-02-09T12:00:00Z",
    "updated_at": "2026-02-09T12:00:00Z"
  }
}
```

### Error Responses

**Invalid/Expired OTP (400 Bad Request)**
```json
{
  "otp": ["Invalid or expired OTP code."]
}
```

**Registration data not found (400 Bad Request)**
```json
{
  "email": ["Registration data not found. Please register again."]
}
```

### cURL Example
```bash
curl -X POST http://localhost:8000/api/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "otp": "123456"
  }'
```

---

## 3. Resend OTP

### Endpoint
```
POST /api/auth/resend-otp/
```

### Request Body
```json
{
  "email": "user@example.com"
}
```

### Success Response (200 OK)
```json
{
  "message": "OTP resent successfully. Please check your email.",
  "email": "user@example.com"
}
```

### Error Responses

**Too soon to resend (400 Bad Request)**
```json
{
  "error": "Please wait 45 seconds before requesting a new code"
}
```

**Max resends reached (400 Bad Request)**
```json
{
  "error": "Maximum OTP resend attempts reached. Please try again later."
}
```

**No pending registration (400 Bad Request)**
```json
{
  "email": ["No pending registration found for this email. Please register first."]
}
```

### cURL Example
```bash
curl -X POST http://localhost:8000/api/auth/resend-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }'
```

---

## 4. User Login

### Endpoint
```
POST /api/auth/login/
```

### Request Body (Login with Email)
```json
{
  "identifier": "user@example.com",
  "password": "SecurePass123!"
}
```

### Request Body (Login with Username)
```json
{
  "identifier": "johndoe123",
  "password": "SecurePass123!"
}
```

### Success Response (200 OK)
```json
{
  "message": "Login successful",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "bio": "Full-stack developer",
    "profile_image_url": "http://localhost:8000/media/profile_images/image.jpg",
    "specializations": [
      {
        "id": "spec-uuid",
        "name": "Back-end development",
        "description": "Server-side development..."
      }
    ],
    "wallet": {
      "id": "wallet-uuid",
      "balance": 100
    },
    "created_at": "2026-02-09T12:00:00Z",
    "updated_at": "2026-02-09T12:00:00Z"
  }
}
```

### Error Responses

**Invalid credentials (400 Bad Request)**
```json
{
  "error": "Invalid credentials. 4 attempts remaining before account lockout."
}
```

**Account locked (400 Bad Request)**
```json
{
  "error": "Account locked due to too many failed login attempts. Please try again after 15 minutes."
}
```

### cURL Example
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "test@example.com",
    "password": "SecurePass123!"
  }'
```

---

## 5. Refresh JWT Token

### Endpoint
```
POST /api/auth/token/refresh/
```

### Request Body
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Success Response (200 OK)
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### cURL Example
```bash
curl -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "your-refresh-token-here"
  }'
```

---

## 6. Get User Profile

### Endpoint
```
GET /api/users/me/
```

### Headers
```
Authorization: Bearer <access_token>
```

### Success Response (200 OK)
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe123",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "bio": "Full-stack developer",
  "profile_image_url": "http://localhost:8000/media/profile_images/image.jpg",
  "specializations": [],
  "wallet": {
    "id": "wallet-uuid",
    "balance": 0
  },
  "created_at": "2026-02-09T12:00:00Z",
  "updated_at": "2026-02-09T12:00:00Z"
}
```

### Error Response

**Unauthorized (401 Unauthorized)**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Invalid token (401 Unauthorized)**
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid"
}
```

### cURL Example
```bash
curl -X GET http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer your-access-token-here"
```

---

## 🧪 Testing Workflow

### Complete Registration Flow

```bash
# Step 1: Register user (sends OTP)
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser123",
    "password": "SecurePass123!",
    "first_name": "New",
    "last_name": "User",
    "phone_number": "+9876543210"
  }'

# Step 2: Check your email for OTP (6 digits)

# Step 3: Verify OTP (creates account + auto-login)
curl -X POST http://localhost:8000/api/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "otp": "123456"
  }'

# Response includes access_token and refresh_token
# Save these tokens for authenticated requests
```

### Login Flow

```bash
# Login with email
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "newuser@example.com",
    "password": "SecurePass123!"
  }'

# OR login with username
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "newuser123",
    "password": "SecurePass123!"
  }'

# Save access_token from response
```

### Authenticated Request

```bash
# Get user profile
curl -X GET http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer <your-access-token>"
```

---

## 🔒 Security Features

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

### Rate Limiting
- **OTP Resend**: 60 seconds delay, max 3 attempts
- **Login Attempts**: 5 failed attempts → 15 minute lockout

### Email Verification
- OTP valid for 5 minutes
- One-time use (deleted after verification)
- Cannot login without verified email

---

## 📧 Email Template

Users will receive this email:

```
Subject: Welcome to xBrain! Verify your email

Hi John,

Thank you for joining xBrain!

Your verification code is: 123456

This code will expire in 5 minutes.

If you didn't create an account, please ignore this email.

Best regards,
The xBrain Team
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Email not sending
**Error**: `SMTPAuthenticationError`

**Solution**: Make sure you're using Gmail App Password, not regular password
1. Enable 2-Step Verification
2. Generate App Password
3. Update `.env` file

### Issue 2: OTP expired
**Error**: `Invalid or expired OTP code`

**Solution**: OTP expires after 5 minutes. Request a new one via `/api/auth/resend-otp/`

### Issue 3: Account locked
**Error**: `Account locked due to too many failed login attempts`

**Solution**: Wait 15 minutes or clear cache:
```python
from django.core.cache import cache
cache.delete('login_attempts_user@example.com')
```

### Issue 4: Registration data not found
**Error**: `Registration data not found. Please register again.`

**Solution**: Pending registration expires after 10 minutes. Start registration process again.

---

## 🎯 Testing Checklist

- [ ] User can register with all required fields
- [ ] OTP email is received
- [ ] OTP verification creates account
- [ ] Auto-login after verification returns tokens
- [ ] Wallet is automatically created
- [ ] User can login with email
- [ ] User can login with username
- [ ] Failed logins increment attempt counter
- [ ] Account locks after 5 failed attempts
- [ ] Locked account unlocks after 15 minutes
- [ ] OTP resend works with 60 second delay
- [ ] Max 3 OTP resend attempts enforced
- [ ] Profile image upload works
- [ ] User profile includes wallet balance
- [ ] Token refresh works
- [ ] Authenticated endpoints require token

---

## 📝 Next Steps

After testing authentication:
1. Add user specializations (add/remove)
2. Add certificate management
3. Add profile update endpoint
4. Add password reset flow
5. Add user search/list endpoints

---

**Created**: February 2026  
**Status**: ✅ READY FOR TESTING  
**Gmail**: xBrain2026@gmail.com
