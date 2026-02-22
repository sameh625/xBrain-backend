# xBrain API Documentation

**Base URL:** `https://xbrain-backend.onrender.com`

All requests use `Content-Type: application/json`.

Protected endpoints need the header: `Authorization: Bearer <access_token>`

---

## Auth Endpoints

### Register
`POST /api/auth/register/`

```json
{
  "email": "user@example.com",
  "username": "johndoe123",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "bio": "optional bio text",
  "profile_image": null
}
```

**Validation rules:**
- `username`: 8-16 chars, starts with a letter, unique
- `password`: min 8 chars, needs uppercase + lowercase + number + special char
- `phone_number`: 7-15 digits (optional + prefix), unique
- `bio` and `profile_image` are optional

**Response (200):**
```json
{
  "message": "OTP sent successfully. Please check your email for verification code.",
  "email": "user@example.com",
  "otp": "583921"
}
```

The `otp` field is included in the response directly. Use it in the next step.

---

### Verify Email
`POST /api/auth/verify-email/`

```json
{
  "email": "user@example.com",
  "otp": "583921"
}
```

**Response (201):**
```json
{
  "message": "Email verified successfully. Welcome to xBrain!",
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "bio": "",
    "profile_image_url": null,
    "specializations": [],
    "wallet": {
      "id": "wallet-uuid",
      "balance": 0
    },
    "created_at": "2026-02-22T12:00:00Z",
    "updated_at": "2026-02-22T12:00:00Z"
  }
}
```

The user is automatically logged in after verification - you get both tokens right away.

---

### Login
`POST /api/auth/login/`

You can use either email or username in the `identifier` field.

```json
{
  "identifier": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "bio": "",
    "profile_image_url": null,
    "specializations": [],
    "wallet": {
      "id": "wallet-uuid",
      "balance": 0
    },
    "created_at": "2026-02-22T12:00:00Z",
    "updated_at": "2026-02-22T12:00:00Z"
  }
}
```

**Failed login:** returns how many attempts are left. After 5 failures the account locks for 15 minutes.

---

### Resend OTP
`POST /api/auth/resend-otp/`

```json
{
  "email": "user@example.com"
}
```

There's a 60-second cooldown between resends, and a max of 3 resend attempts.

---

### Refresh Token
`POST /api/auth/token/refresh/`

When the access token expires (after 1 hour), call this with the refresh token to get a new pair.

```json
{
  "refresh": "eyJ0eXAi..."
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAi...",
  "refresh": "eyJ0eXAi..."
}
```

Save both tokens - the old refresh token gets blacklisted after use. The refresh token itself is valid for 7 days.

### How tokens work

After login or verification, you get two tokens. The **access token** is what you send with every request to prove you're logged in - it expires after 1 hour. The **refresh token** is used only to get a new access token when the old one expires, so the user doesn't have to log in again. Store both securely (e.g. `flutter_secure_storage`). If a request returns 401, call `/api/auth/token/refresh/` to get fresh tokens. If the refresh token is also expired (after 7 days), the user needs to log in again.

---

## Protected Endpoints

These require the header: `Authorization: Bearer <access_token>`

### Get My Profile
`GET /api/users/me/`

Returns the current user's full profile (same shape as the user object in login response).

---

### Get All Specializations
`GET /api/specializations/`

Returns every available specialization in the system.

**Response (200):**
```json
{
  "count": 8,
  "results": [
    {
      "id": "uuid",
      "name": "Back-end Development",
      "description": "Server-side development..."
    }
  ]
}
```

---

### Get/Set My Specializations
`GET /api/users/me/specializations/` - returns current user's specializations

`PUT /api/users/me/specializations/` - set the user's specializations (replaces all)

```json
{
  "specialization_ids": ["uuid-1", "uuid-2"]
}
```

`PATCH /api/users/me/specializations/` - skip the specialization form

```json
{
  "skip": true
}
```

---

## Error Format

All errors come back as 400 with a JSON body. The key is the field name, the value is an array of error messages:

```json
{
  "email": ["This email is already registered."],
  "password": ["Password must contain at least one uppercase letter"]
}
```

For auth errors on protected endpoints you'll get 401:

```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## Quick Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register/` | No | Register + get OTP |
| POST | `/api/auth/verify-email/` | No | Verify OTP + create account |
| POST | `/api/auth/login/` | No | Login (email or username) |
| POST | `/api/auth/resend-otp/` | No | Resend OTP |
| POST | `/api/auth/token/refresh/` | No | Get new tokens |
| GET | `/api/users/me/` | Yes | Get my profile |
| GET | `/api/specializations/` | Yes | List all specializations |
| GET | `/api/users/me/specializations/` | Yes | My specializations |
| PUT | `/api/users/me/specializations/` | Yes | Set my specializations |
| PATCH | `/api/users/me/specializations/` | Yes | Skip specialization form |