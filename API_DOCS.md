# xBrain API Documentation

**Base URL:** _will be shared once deployment is finalized_

All requests use `Content-Type: application/json`.

Protected endpoints need the header: `Authorization: Bearer <access_token>`
---

## Auth Endpoints

### 1. Register
`POST /api/auth/register/`

Sends an OTP to the user's email. No account is created yet.

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `email` | `string` | yes | valid email, unique |
| `username` | `string` | yes | 8-16 chars, starts with letter, letters/numbers/dots/underscores/hyphens only, unique |
| `password` | `string` | yes | min 8 chars, must have uppercase + lowercase + number + special char |
| `first_name` | `string` | yes | max 50 chars |
| `last_name` | `string` | yes | max 50 chars |
| `phone_number` | `string` | yes | 7-15 digits, optional `+` prefix, unique |
| `bio` | `string` | no | max 500 chars |
| `profile_image` | `file` | no | image upload |

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

**Response (200):**
```json
{
  "message": "OTP sent successfully. Please check your email for verification code.",
  "email": "user@example.com"
}
```

The OTP is sent to the user's email. Use it in the next step.

**Possible errors (400):**

| Scenario | Error key | Example message |
|----------|-----------|-----------------|
| Email taken | `email` | `"This email is already registered."` |
| Email pending OTP | `email` | `"An OTP has already been sent to this email..."` |
| Username taken | `username` | `"This username is already taken."` |
| Username invalid | `username` | `"Username must start with a letter."` |
| Weak password | `password` | `"Password must contain at least one uppercase letter"` |
| Bad phone format | `phone_number` | `"Enter a valid phone number (7-15 digits, optional + prefix)."` |
| Phone taken | `phone_number` | `"This phone number is already registered."` |

---

### 2. Verify Email
`POST /api/auth/verify-email/`

Verifies the OTP and creates the user account. Returns tokens immediately (auto-login).

| Field | Type | Required |
|-------|------|----------|
| `email` | `string` | yes |
| `otp` | `string` | yes, exactly 6 characters |

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
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "bio": "",
    "profile_image_url": null,
    "specializations": [],
    "wallet": {
      "id": "663e8500-f30c-52e5-b827-557766551111",
      "balance": 0
    },
    "specialization_form_completed_at": null,
    "created_at": "2026-02-22T12:00:00Z",
    "updated_at": "2026-02-22T12:00:00Z"
  }
}
```

**Possible errors (400):**

| Scenario | Error key |
|----------|-----------|
| Wrong or expired OTP | `otp` |
| Registration data expired (10 min timeout) | `email` |

---

### 3. Login
`POST /api/auth/login/`

Works with either email or username in the `identifier` field.

| Field | Type | Required |
|-------|------|----------|
| `identifier` | `string` | yes (email or username) |
| `password` | `string` | yes |

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
  "user": { ... }
}
```

The `user` object is the same shape as the verify response above.

**Possible errors (400):**

| Scenario | Example message |
|----------|-----------------|
| Wrong credentials | `"Invalid credentials. 4 attempts remaining before account lockout."` |
| Account locked (5 fails) | `"Account locked due to too many failed login attempts. Please try again after 15 minutes."` |

---

### 4. Resend OTP
`POST /api/auth/resend-otp/`

Resends the OTP to the email. Only works if there's a pending registration.

| Field | Type | Required |
|-------|------|----------|
| `email` | `string` | yes |

```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "OTP resent successfully. Please check your email.",
  "email": "user@example.com"
}
```

**Limits:** 60-second cooldown between resends, max 3 resend attempts.

**Possible errors (400):**

| Scenario | Example message |
|----------|-----------------|
| No pending registration | `"No pending registration found for this email."` |
| Too soon | `"Please wait 45 seconds before requesting a new code"` |
| Max resends reached | `"Maximum OTP resend attempts reached."` |

---

### 5. Refresh Token
`POST /api/auth/token/refresh/`

| Field | Type | Required |
|-------|------|----------|
| `refresh` | `string` | yes |

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

Save both — the old refresh token is blacklisted. Refresh token is valid for 7 days.

### How tokens work

After login or verification you get two tokens. The **access token** goes in every request header to prove you're logged in — it expires after 1 hour. The **refresh token** is only used to get a new access token when the old one expires, so the user doesn't have to log in again. Store both with `flutter_secure_storage`. If a request returns 401, call `/api/auth/token/refresh/`. If the refresh token is also expired (7 days), redirect to login.

---

## Protected Endpoints

These require: `Authorization: Bearer <access_token>`

### 6. Get My Profile
`GET /api/users/me/`

Returns the current user's full profile (same shape as the user object in login/verify responses).

---

### 7. Get All Specializations
`GET /api/specializations/`

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

Returns `"message": "No specializations available"` with empty `results` if none exist.

---

### 8. My Specializations

**GET** `/api/users/me/specializations/` — returns current specializations and form status

**Response (200):**
```json
{
  "specialization_form_completed_at": null,
  "specializations": []
}
```

**PUT** `/api/users/me/specializations/` — set specializations (replaces all existing ones)

| Field | Type | Required |
|-------|------|----------|
| `specialization_ids` | `string[] (UUIDs)` | yes |

```json
{
  "specialization_ids": ["uuid-1", "uuid-2"]
}
```

**PATCH** `/api/users/me/specializations/` — skip the specialization selection form

| Field | Type | Required |
|-------|------|----------|
| `skip` | `boolean` | yes (must be `true`) |

```json
{
  "skip": true
}
```

Both PUT and PATCH set `specialization_form_completed_at` to the current time.

---

## Error Format

All validation errors come back as **400** with field-level messages:

```json
{
  "email": ["This email is already registered."],
  "password": ["Password must contain at least one uppercase letter"]
}
```

Auth errors on protected endpoints return **401**:

```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## Quick Reference

| # | Method | Endpoint | Auth | Description |
|---|--------|----------|------|-------------|
| 1 | POST | `/api/auth/register/` | No | Send OTP to email |
| 2 | POST | `/api/auth/verify-email/` | No | Verify OTP + create account |
| 3 | POST | `/api/auth/login/` | No | Login (email or username) |
| 4 | POST | `/api/auth/resend-otp/` | No | Resend OTP |
| 5 | POST | `/api/auth/token/refresh/` | No | Refresh expired tokens |
| 6 | GET | `/api/users/me/` | Yes | Get my profile |
| 7 | GET | `/api/specializations/` | Yes | List all specializations |
| 8 | GET | `/api/users/me/specializations/` | Yes | My specializations |
| 8 | PUT | `/api/users/me/specializations/` | Yes | Set my specializations |
| 8 | PATCH | `/api/users/me/specializations/` | Yes | Skip specialization form |