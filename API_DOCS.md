# xBrain API Documentation

**Base URL:** `https://xbrain-backend-chbfe7hscpbqergn.francecentral-01.azurewebsites.net`

All requests use `Content-Type: application/json` unless stated otherwise.

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

```json
{
  "email": "user@example.com",
  "username": "johndoe123",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "bio": "optional bio text"
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

### 5. Forgot Password
`POST /api/auth/forgot-password/`

Initiates the password reset process by sending an OTP to the user's email.

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
  "email": "user@example.com",
  "message": "Password reset code sent to your email."
}
```

**Possible errors (400):**
| Scenario | Example message |
|----------|-----------------|
| Email not found | `"User with this email not found."` |

---

### 6. Verify Reset OTP
`POST /api/auth/verify-reset-otp/`

Verifies the reset OTP and returns a temporary token needed to set the new password.

| Field | Type | Required |
|-------|------|----------|
| `email` | `string` | yes |
| `otp`   | `string` | yes (exactly 6 characters) |

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response (200):**
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "reset_token": "a1b2c3d4-e5f6-7890-uuid-here"
}
```

**Possible errors (400):**
| Scenario | Error key |
|----------|-----------|
| Wrong/expired OTP | `otp` |

---

### 7. Reset Password
`POST /api/auth/reset-password/`

Sets the new password using the reset token obtained from the previous step.

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `email`        | `string` | yes | |
| `token`        | `string` | yes | The `reset_token` from step 6 |
| `new_password` | `string` | yes | min 8 chars, uppercase + lowercase + number + special char |

```json
{
  "email": "user@example.com",
  "token": "a1b2c3d4-e5f6-7890-uuid-here",
  "new_password": "NewSecurePass123!"
}
```

**Response (200):**
```json
{
  "message": "Password reset successfully. You can now log in."
}
```

**Possible errors (400):**
| Scenario | Error key |
|----------|-----------|
| Wrong/expired token | `token` |
| Weak password | `new_password` |

---

### 8. Refresh Token
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

Save both - the old refresh token is blacklisted. Refresh token is valid for 7 days.

### How tokens work

After login or verification you get two tokens. The **access token** goes in every request header to prove you're logged in - it expires after 1 hour. The **refresh token** is only used to get a new access token when the old one expires, so the user doesn't have to log in again. Store both with `flutter_secure_storage`. If a request returns 401, call `/api/auth/token/refresh/`. If the refresh token is also expired (7 days), redirect to login.

---

## Protected Endpoints

These require: `Authorization: Bearer <access_token>`

### 9. Get My Profile
`GET /api/users/me/`

Returns the current user's full profile (same shape as the user object in login/verify responses).

---

### 10. Update My Profile
`PATCH /api/users/me/`

Updates the authenticated user's profile. Uses `Content-Type: multipart/form-data` to support profile image upload. All fields are optional - only send the fields you want to update.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `first_name` | `string` | no | max 50 chars |
| `last_name` | `string` | no | max 50 chars |
| `phone_number` | `string` | no | 7-15 digits, optional `+` prefix |
| `bio` | `string` | no | max 500 chars |
| `profile_image` | `file` | no | image file (jpg, png, etc.) |

**Response (200):** Returns the full updated user profile (same shape as GET `/api/users/me/`).

**Possible errors (400):**
| Scenario | Example message |
|----------|-----------------|
| Invalid image file | `"Upload a valid image."` |

---

### 11. Get All Specializations
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

### 12. My Specializations

**GET** `/api/users/me/specializations/` - returns current specializations and form status

**Response (200):**
```json
{
  "specialization_form_completed_at": null,
  "specializations": []
}
```

**PUT** `/api/users/me/specializations/` - set specializations (replaces all existing ones)

| Field | Type | Required |
|-------|------|----------|
| `specialization_ids` | `string[] (UUIDs)` | yes |

```json
{
  "specialization_ids": ["uuid-1", "uuid-2"]
}
```

**PATCH** `/api/users/me/specializations/` - skip the specialization selection form

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

## Q&A Endpoints

These power the Questions, Answers, and Replies feature. All require `Authorization: Bearer <access_token>` for write operations. Read operations work for any authenticated user.

**Quick mental model**:
- A **Question** is a post with content + 1 to 3 specializations.
- A Question can have unlimited **Answers** (top-level).
- Each Answer can have unlimited **Replies**.
- Replies cannot have their own replies (depth limit = 1).
- Only the asker can mark their question resolved/unresolved.
- Only authors can edit or delete their own questions/answers/replies.

---

### 13. List Questions
`GET /api/questions/`

Paginated newest-first list of questions.

**Query params (all optional):**

| Param | Type | Notes |
|-------|------|-------|
| `author` | UUID | Show only questions by this user |
| `specialization` | UUID | Show only questions tagged with this spec (matches even if the question has other specs too) |
| `is_resolved` | `true` / `false` | Filter by resolved status |
| `q` | string | Search question content (case-insensitive substring) |
| `page` | integer | Pagination (default 20 per page) |

**Response (200):**
```json
{
  "count": 47,
  "next": "https://.../api/questions/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "author": {
        "id": "uuid",
        "username": "johndoe123",
        "profile_image_url": "https://.../profile.jpg"
      },
      "content_preview": "How do I deploy a Django app to Azure with Postgres? I'm running into...",
      "specializations": [
        { "id": "uuid", "name": "Backend" },
        { "id": "uuid", "name": "DevOps" }
      ],
      "is_resolved": false,
      "answers_count": 12,
      "created_at": "2026-04-28T12:00:00Z"
    }
  ]
}
```

`content_preview` is the first 120 chars of the question content. Get the full content from the detail endpoint.

`answers_count` is the **total** of top-level answers and replies combined (Facebook-style "12 comments").

---

### 14. Create a Question
`POST /api/questions/`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `content` | `string` | yes | 1–5000 chars, not whitespace-only |
| `specializations` | `string[] (UUIDs)` | yes | 1 to 3 specialization UUIDs |
| `is_resolved` | `boolean` | no | defaults to `false` |

```json
{
  "content": "How do I deploy a Django app to Azure with Postgres?",
  "specializations": ["uuid-of-backend", "uuid-of-devops"]
}
```

**Response (201):** Returns the **full detail shape** (same as `GET /api/questions/{id}/` below) so you don't need a follow-up GET to render the new question.

**Possible errors (400):**

| Scenario | Error key | Example message |
|----------|-----------|-----------------|
| No specs | `specializations` | `"At least one specialization is required."` |
| More than 3 specs | `specializations` | `"A question can have at most 3 specializations."` |
| Unknown spec UUID | `specializations` | `"Invalid pk \"...\" - object does not exist."` |
| Empty content | `content` | `"Content cannot be empty."` |
| Content too long | `content` | `"Ensure this field has no more than 5000 characters."` |

**Errors (401):** No or invalid token.

---

### 15. Get a Question (with embedded answers)
`GET /api/questions/{id}/`

Returns the question plus its **first 10 top-level answers**, each with the **first 2 replies inline**. For more, use the dedicated answer / reply list endpoints below.

**Response (200):**
```json
{
  "id": "uuid",
  "author": {
    "id": "uuid",
    "username": "johndoe123",
    "profile_image_url": "https://.../profile.jpg"
  },
  "content": "Full question text here...",
  "specializations": [
    { "id": "uuid", "name": "Backend" }
  ],
  "is_resolved": false,
  "resolved_at": null,
  "answers_count": 12,
  "answers": [
    {
      "id": "uuid",
      "question": "uuid",
      "author": { "id": "uuid", "username": "...", "profile_image_url": null },
      "content": "Answer body...",
      "parent_answer": null,
      "replies_count": 3,
      "replies": [
        {
          "id": "uuid",
          "question": "uuid",
          "author": { "id": "uuid", "username": "...", "profile_image_url": null },
          "content": "Reply body...",
          "parent_answer": "uuid-of-the-answer-above",
          "replies_count": 0,
          "created_at": "2026-04-28T13:00:00Z",
          "updated_at": "2026-04-28T13:00:00Z"
        }
      ],
      "created_at": "2026-04-28T12:30:00Z",
      "updated_at": "2026-04-28T12:30:00Z"
    }
  ],
  "created_at": "2026-04-28T12:00:00Z",
  "updated_at": "2026-04-28T12:00:00Z"
}
```

**Important**: each top-level answer has both `replies_count` (total) and `replies` (first 2 only). If `replies_count > replies.length`, fetch the rest from `GET /api/answers/{id}/replies/`.

**Errors (404):** Question does not exist.

---

### 16. Update a Question
`PATCH /api/questions/{id}/`

Author only. Returns the same detail shape as the GET above.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `content` | `string` | no | 1–5000 chars |
| `specializations` | `string[]` | no | If present, still 1–3 UUIDs |
| `is_resolved` | `boolean` | no | (Prefer the dedicated `/resolve/` endpoint below for clarity) |

**Errors:**
- `400` — same validation rules as create.
- `403` — request user is not the question's author.
- `404` — question does not exist.

---

### 17. Delete a Question
`DELETE /api/questions/{id}/`

Author only. **Cascades** — deleting a question also deletes all its answers and replies.

**Response (204):** No content.

**Errors:**
- `403` — not the author.
- `404` — does not exist.

---

### 18. Mark Question Resolved
`POST /api/questions/{id}/resolve/`

Asker only. Idempotent — calling on an already-resolved question is a no-op `200`. No request body.

**Response (200):** Full question detail shape with `is_resolved: true` and `resolved_at` set.

**Errors:**
- `403` — not the asker.
- `404` — does not exist.

---

### 19. Mark Question Unresolved
`POST /api/questions/{id}/unresolve/`

Asker only. Idempotent. No request body. For when the asker realizes the question still needs more discussion.

**Response (200):** Full question detail shape with `is_resolved: false` and `resolved_at: null`.

**Errors:**
- `403` — not the asker.
- `404` — does not exist.

---

### 20. List Top-Level Answers
`GET /api/questions/{question_id}/answers/`

Paginated list of **top-level** answers under a question (replies are NOT included here).

**Response (200):**
```json
{
  "count": 12,
  "next": "https://.../api/questions/<uuid>/answers/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "question": "uuid-of-question",
      "author": { "id": "uuid", "username": "...", "profile_image_url": "..." },
      "content": "Answer body...",
      "parent_answer": null,
      "replies_count": 3,
      "created_at": "2026-04-28T12:30:00Z",
      "updated_at": "2026-04-28T12:30:00Z"
    }
  ]
}
```

Note: `parent_answer` is `null` here because this endpoint only returns top-level answers. To fetch replies under a specific answer, use endpoint 23 below.

**Errors (404):** Question does not exist.

---

### 21. Post an Answer to a Question
`POST /api/questions/{question_id}/answers/`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `content` | `string` | yes | 1–5000 chars, not whitespace-only |

```json
{ "content": "You should use Azure App Service with Postgres Flexible Server..." }
```

**Response (201):** The created answer in the same shape as the list response above. `replies_count` will be `0`.

**Errors:**
- `400` — empty or too-long content.
- `401` — no token.
- `404` — question does not exist.

---

### 22. Get / Update / Delete a Single Answer or Reply
`GET / PATCH / DELETE /api/answers/{id}/`

Same view handles top-level answers and replies (both are stored as `Answer` rows). The `parent_answer` field tells you which: `null` = top-level, UUID = reply.

**GET (any user):**
```json
{
  "id": "uuid",
  "question": "uuid",
  "author": { ... },
  "content": "...",
  "parent_answer": null,
  "replies_count": 3,
  "created_at": "...",
  "updated_at": "..."
}
```

**PATCH (author only):** Only `content` may be edited.

```json
{ "content": "Edited answer body" }
```

**DELETE (author only):** **Cascades** — deleting a top-level answer deletes all its replies.

**Errors:**
- `400` — empty content on PATCH.
- `403` — not the author (PATCH or DELETE).
- `404` — does not exist.

---

### 23. List Replies under an Answer
`GET /api/answers/{id}/replies/`

Paginated list of replies under a specific top-level answer.

**Response (200):**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "question": "uuid-of-the-parent-question",
      "author": { "id": "uuid", "username": "...", "profile_image_url": null },
      "content": "Reply body...",
      "parent_answer": "uuid-of-the-parent-answer",
      "replies_count": 0,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

`replies_count` on a reply is always `0` because of the depth-1 limit.

**Errors (404):** Answer does not exist.

---

### 24. Post a Reply to an Answer
`POST /api/answers/{id}/replies/`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `content` | `string` | yes | 1–5000 chars, not whitespace-only |

```json
{ "content": "Or AWS Elastic Beanstalk works too." }
```

**Response (201):** The created reply with `parent_answer` set to the URL's answer ID.

**Important**: replies cannot have replies. If you POST to `/api/answers/<id>/replies/` where `<id>` is itself a reply, you get `400` with the message `"Replies cannot have replies — depth limit is 1."`

**Errors:**
- `400` — empty content, OR trying to reply to a reply (depth-1 enforcement).
- `401` — no token.
- `404` — parent answer does not exist.

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
| 4 | POST | `/api/auth/resend-otp/` | No | Resend registration OTP |
| 5 | POST | `/api/auth/forgot-password/` | No | Send password reset OTP |
| 6 | POST | `/api/auth/verify-reset-otp/` | No | Verify reset OTP |
| 7 | POST | `/api/auth/reset-password/` | No | Set new password |
| 8 | POST | `/api/auth/token/refresh/` | No | Refresh expired tokens |
| 9 | GET | `/api/users/me/` | Yes | Get my profile |
| 10 | PATCH | `/api/users/me/` | Yes | Update profile / upload image |
| 11 | GET | `/api/specializations/` | Yes | List all specializations |
| 12 | GET | `/api/users/me/specializations/` | Yes | My specializations |
| 12 | PUT | `/api/users/me/specializations/` | Yes | Set my specializations |
| 12 | PATCH | `/api/users/me/specializations/` | Yes | Skip specialization form |
| 13 | GET | `/api/questions/` | Read-only OK | List questions (paginated) |
| 14 | POST | `/api/questions/` | Yes | Create a question |
| 15 | GET | `/api/questions/{id}/` | Read-only OK | Question detail + 10 answers + 2 replies each |
| 16 | PATCH | `/api/questions/{id}/` | Yes (author) | Update a question |
| 17 | DELETE | `/api/questions/{id}/` | Yes (author) | Delete a question (cascades) |
| 18 | POST | `/api/questions/{id}/resolve/` | Yes (asker) | Mark question resolved |
| 19 | POST | `/api/questions/{id}/unresolve/` | Yes (asker) | Mark question unresolved |
| 20 | GET | `/api/questions/{id}/answers/` | Read-only OK | List top-level answers |
| 21 | POST | `/api/questions/{id}/answers/` | Yes | Post an answer |
| 22 | GET | `/api/answers/{id}/` | Read-only OK | Get single answer / reply |
| 22 | PATCH | `/api/answers/{id}/` | Yes (author) | Update an answer / reply |
| 22 | DELETE | `/api/answers/{id}/` | Yes (author) | Delete an answer / reply (cascades) |
| 23 | GET | `/api/answers/{id}/replies/` | Read-only OK | List replies under an answer |
| 24 | POST | `/api/answers/{id}/replies/` | Yes | Post a reply (depth-1 only) |

---

## Important Notes

### Profile Image Upload

`profile_image` has been **removed** from the Register endpoint. Registration is now pure JSON - no `multipart/form-data` needed.

To upload a profile image, use the **Update Profile** endpoint after the user has registered and received their token:

```
PATCH /api/users/me/
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

All fields are optional - send only what you want to update:
- `first_name`
- `last_name`
- `phone_number`
- `bio`
- `profile_image` (file)

**User flow:**
1. `POST /api/auth/register/` => send JSON, get OTP email
2. `POST /api/auth/verify-email/` => send OTP, get `access_token`
3. `PATCH /api/users/me/` => upload profile image with the token

---

### Q&A Integration Notes (for the Flutter team)

A few semantics worth knowing before you start wiring screens.

#### Mental model

```
Question (a post)
├── Answer (top-level, parent_answer = null)
│   ├── Reply (parent_answer = <answer.id>)
│   └── Reply
└── Answer (top-level)
    └── Reply
```

- Top-level answers and replies are **the same model** server-side. The discriminator is `parent_answer`: `null` means top-level, a UUID means it's a reply.
- Replies cannot have replies. The server rejects depth-2 posts with `400`.

#### `answers_count` on a Question

It's the **total** count of all answers under the question — top-level answers plus replies, combined. Same shape as Facebook's "12 comments" badge. If a question has 3 top-level answers and each has 2 replies, `answers_count` is `9`.

#### `replies_count` on an Answer

Per-answer count of replies under that specific answer. For top-level answers it can be any non-negative number. For replies it's always `0` (depth-1 cap).

#### Two independent UI checks

These are different things — don't conflate them:

```dart
// Is this a reply or a top-level answer?
final isTopLevel = answer.parent_answer == null;

// Does this answer have nested replies the user can expand?
final hasReplies = answer.replies_count > 0;
```

A top-level answer with zero replies is normal — show a "Reply" button on it, just no expander.

#### Loading more answers / replies

The question detail endpoint returns the **first 10 top-level answers**, each with the **first 2 replies** inline. To load more:

| To get | Call |
|---|---|
| Top-level answers 11+ | `GET /api/questions/<question_id>/answers/?page=2` |
| Replies 3+ under a specific answer | `GET /api/answers/<answer_id>/replies/?page=1` |

All paginated endpoints return the standard envelope:

```json
{
  "count": 47,
  "next": "https://.../?page=2",
  "previous": null,
  "results": [...]
}
```

Walk `next` URLs until they're `null`.

#### Permission boundaries

| Action | Who can do it |
|---|---|
| Read any question / answer / reply | Anyone authenticated |
| Create question / answer / reply | Anyone authenticated |
| Edit question / answer / reply | The original author only |
| Delete question / answer / reply | The original author only |
| Resolve / unresolve a question | The question's asker only |

The server enforces all of these. A non-author trying to PATCH gets `403 Forbidden`. Show or hide the edit/delete buttons on the client based on `answer.author.id == current_user.id`, but trust the server to be the final word.

#### Cascade deletes

- Deleting a question deletes all its answers and replies.
- Deleting a top-level answer deletes all its replies.
- Deleting a reply just removes that one row.

Show a confirmation dialog before destructive operations — there's no undo.

#### Recommended end-to-end flow

```
1. POST /api/questions/                      → create a question
2. (Other user)
   POST /api/questions/<id>/answers/         → post a top-level answer
3. (Asker or anyone)
   POST /api/answers/<id>/replies/           → reply to that answer
4. (Asker only)
   POST /api/questions/<id>/resolve/         → mark resolved when satisfied
5. (Optional)
   POST /api/questions/<id>/unresolve/       → if more discussion needed
```

#### Fields server-side fills in (don't send these in request bodies)

For both questions and answers:
- `id` → server generates a UUID.
- `author` → server sets to `request.user`.
- `created_at`, `updated_at` → automatic.

For answers/replies specifically:
- `question` → server pulls from URL kwarg.
- `parent_answer` → server sets to `null` for top-level answers, to the parent's UUID for replies.

If you accidentally send these fields in the request body, the server ignores them. They're not honored from client input.

#### Self-answer is allowed

A user can answer their own question. Use case: "I figured it out myself, here's what worked." Useful for future searchers.

#### Anyone can reply to anyone

Replies aren't restricted to the question's author. Any authenticated user can reply to any answer to start a multi-party discussion. UI-wise, treat it like a forum thread.