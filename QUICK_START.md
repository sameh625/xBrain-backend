# 🚀 Quick Reference - 3 Steps to Test

## Step 1: Setup Gmail App Password (2 minutes)

1. Go to: https://myaccount.google.com/security
2. Enable "2-Step Verification" (if not already)
3. Click "App passwords" → Select "Mail" → Generate
4. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)
5. Edit `.env` file in your project:
   ```bash
   nano .env
   ```
6. Update this line (remove spaces from password):
   ```
   EMAIL_HOST_PASSWORD=abcdefghijklmnop
   ```
7. Save and exit (Ctrl+X, Y, Enter)

---

## Step 2: Run Migrations (30 seconds)

```bash
cd /home/sameh/4th/grad_project/xBrain

python manage.py makemigrations api
python manage.py migrate
```

---

## Step 3: Test! (5 minutes)

### Start Server
```bash
python manage.py runserver
```

### Test Registration (New Terminal)
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "yourpersonal@email.com",
    "username": "testuser123",
    "password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User",
    "phone_number": "+1234567890"
  }'
```

**Expected response:**
```json
{
  "message": "OTP sent successfully. Please check your email for verification code.",
  "email": "yourpersonal@email.com"
}
```

### Check Your Email
- Check inbox for email from xBrain2026@gmail.com
- Copy the 6-digit OTP code

### Verify OTP
```bash
curl -X POST http://localhost:8000/api/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "yourpersonal@email.com",
    "otp": "123456"
  }'
```

**Expected response:**
```json
{
  "message": "Email verified successfully. Welcome to xBrain!",
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "user": {
    "id": "...",
    "email": "yourpersonal@email.com",
    "username": "testuser123",
    "wallet": {
      "balance": 0
    }
  }
}
```

---

## ✅ Success Checklist

- [ ] Server running on http://localhost:8000
- [ ] Registration returns "OTP sent successfully"
- [ ] Email received with 6-digit code
- [ ] OTP verification creates account
- [ ] Response includes access_token and user data
- [ ] User has wallet with balance: 0

---

## 🐛 Quick Troubleshooting

### Email not sending?
1. Check `.env` file has correct Gmail App Password
2. Make sure it's App Password, not regular password
3. No spaces in the password

### OTP expired?
- OTP valid for 5 minutes only
- Request new one: POST to `/api/auth/resend-otp/`

### Server error?
```bash
# Check server logs in terminal
# Common issue: Missing migrations
python manage.py migrate
```

---

## 📚 Full Documentation

- **API Testing**: `API_TESTING_GUIDE.md`
- **Implementation**: `AUTHENTICATION_IMPLEMENTATION.md`
- **Requirements**: `AUTHENTICATION_PLAN.md`

---

## 🎯 All Endpoints

| Endpoint | Purpose |
|----------|---------|
| POST `/api/auth/register/` | Send OTP |
| POST `/api/auth/verify-email/` | Verify OTP & create account |
| POST `/api/auth/login/` | Login |
| POST `/api/auth/resend-otp/` | Resend OTP |
| POST `/api/auth/token/refresh/` | Refresh token |
| GET `/api/users/me/` | Get profile |

---

**Ready? Let's test! 🚀**
