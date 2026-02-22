# xBrain API Documentation

**Base URL:** `https://xbrain-backend.onrender.com`

All requests use `Content-Type: application/json`.

Protected endpoints need the header: `Authorization: Bearer <access_token>`

---

## Data Types

### User Object

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string (UUID)` | auto-generated |
| `email` | `string` | max 255 chars, unique |
| `username` | `string` | 8-16 chars, unique, lowercase |
| `first_name` | `string` | max 50 chars |
| `last_name` | `string` | max 50 chars |
| `phone_number` | `string` | 7-15 digits, optional `+` prefix, unique |
| `bio` | `string` | max 500 chars, optional |
| `profile_image_url` | `string? (URL)` | nullable |
| `specializations` | `Specialization[]` | array of specialization objects |
| `wallet` | `Wallet` | auto-created on registration |
| `specialization_form_completed_at` | `string? (ISO 8601)` | nullable, null means not yet shown |
| `created_at` | `string (ISO 8601)` | auto-generated |
| `updated_at` | `string (ISO 8601)` | auto-updated |

### Wallet Object

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string (UUID)` | auto-generated |
| `balance` | `integer` | starts at 0, never negative |

### Specialization Object

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string (UUID)` | auto-generated |
| `name` | `string` | max 100 chars, unique |
| `description` | `string` | max 500 chars |

---

## Auth Endpoints

### Register
`POST /api/auth/register/`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `email` | `string` | yes | valid email, unique |
| `username` | `string` | yes | 8-16 chars, starts with letter, unique |
| `password` | `string` | yes | min 8, uppercase + lowercase + number + special char |
| `first_name` | `string` | yes | max 50 chars |
| `last_name` | `string` | yes | max 50 chars |
| `phone_number` | `string` | yes | 7-15 digits, optional + prefix, unique |
| `bio` | `string` | no | max 500 chars |
| `profile_image` | `file` | no | image file upload |

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
  "email": "user@example.com",
  "otp": "583921"
}
```

The `otp` field is included in the response directly. Use it in the next step.

---

### Verify Email
`POST /api/auth/verify-email/`

| Field | Type | Required |
|-------|------|----------|
| `email` | `string` | yes |
| `otp` | `string` | yes (exactly 6 digits) |

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
  "user": { ... }
}
```

The user is automatically logged in after verification — you get both tokens right away.

---

### Login
`POST /api/auth/login/`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `identifier` | `string` | yes | email or username |
| `password` | `string` | yes | |

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

The `user` object is the same shape as described in the Data Types section above.

Failed login returns how many attempts are left. After 5 failures the account locks for 15 minutes.

---

### Resend OTP
`POST /api/auth/resend-otp/`

| Field | Type | Required |
|-------|------|----------|
| `email` | `string` | yes |

There's a 60-second cooldown between resends, and a max of 3 resend attempts.

---

### Refresh Token
`POST /api/auth/token/refresh/`

| Field | Type | Required |
|-------|------|----------|
| `refresh` | `string` | yes |

**Response (200):**
```json
{
  "access": "eyJ0eXAi...",
  "refresh": "eyJ0eXAi..."
}
```

Save both tokens — the old refresh token gets blacklisted after use. The refresh token itself is valid for 7 days.

### How tokens work

After login or verification, you get two tokens. The **access token** is what you send with every request to prove you're logged in — it expires after 1 hour. The **refresh token** is used only to get a new access token when the old one expires, so the user doesn't have to log in again. Store both securely (e.g. `flutter_secure_storage`). If a request returns 401, call `/api/auth/token/refresh/` to get fresh tokens. If the refresh token is also expired (after 7 days), the user needs to log in again.

---

## Protected Endpoints

These require the header: `Authorization: Bearer <access_token>`

### Get My Profile
`GET /api/users/me/`

Returns the current user's full profile (same shape as the User object above).

---

### Get All Specializations
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

---

### Get/Set My Specializations
`GET /api/users/me/specializations/` — returns current user's specializations

`PUT /api/users/me/specializations/` — set the user's specializations (replaces all)

| Field | Type | Required |
|-------|------|----------|
| `specialization_ids` | `string[] (UUIDs)` | yes |

```json
{
  "specialization_ids": ["uuid-1", "uuid-2"]
}
```

`PATCH /api/users/me/specializations/` — skip the specialization form

| Field | Type | Required |
|-------|------|----------|
| `skip` | `boolean` | yes (must be true) |

```json
{
  "skip": true
}
```

---

## Error Format

All errors come back as 400 with a JSON body. The key is the field name, the value is an array of strings:

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

---