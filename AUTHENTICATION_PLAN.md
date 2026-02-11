# 🔐 Authentication System - Implementation Plan

## 📋 Features to Implement Today

### 1. Registration Endpoint
### 2. Login Endpoint  
### 3. Email Verification with OTP (Gmail)

---

## ❓ CLARIFICATION QUESTIONS - Please Answer All

### 📝 REGISTRATION ENDPOINT

#### Q1.1: Required Fields on Registration
Which fields are **required** vs **optional** when registering?

**Options:**
- [ ] Email (required - yes/no?) 
- [ ] Username (required - yes/no?)
- [ ] Password (required - yes/no?)
- [ ] First Name (required - yes/no?)
- [ ] Last Name (required - yes/no?)
- [ ] Phone Number (required - yes/no?)
- [ ] Bio (required - yes/no?)
- [ ] Profile Image (required - yes/no?)

**Your Answer:**
- [ ] Email (required - yes/no?) yes
- [ ] Username (required - yes/no?) yes
- [ ] Password (required - yes/no?) yes
- [ ] First Name (required - yes/no?) yes
- [ ] Last Name (required - yes/no?) yes
- [ ] Phone Number (required - yes/no?) yes
- [ ] Bio (required - yes/no?) no
- [ ] Profile Image (required - yes/no?) no


#### Q1.2: Password Requirements
What are the password rules?
- Minimum length? (e.g., 8 characters)
- Require uppercase letter?
- Require number?
- Require special character?

**Your Answer:**
- Minimum length? 8
- Require uppercase letter? yes
- Require number? yes
- Require special character? yes


#### Q1.3: Registration Flow
What happens after user submits registration?

**Option A - Email verification REQUIRED:**
```
1. User submits registration form
2. Account created but NOT activated (is_active=False)
3. OTP sent to email
4. User enters OTP
5. Account activated (is_active=True)
6. User can login
```

**Option B - Email verification OPTIONAL:**
```
1. User submits registration form
2. Account created AND activated (is_active=True)
3. OTP sent to email
4. User can login immediately (even without verifying)
5. Email verified later (optional)
```

**Which flow do you want? A or B?**

**Your Answer:**
**Option C - Email verification REQUIRED:**
```
1. User submits registration form
2. verify email and fields 
3. OTP sent to email
4. User enters OTP
5. Account created (if otp verified)
6. User can login
```


#### Q1.4: Response After Registration
What should the API return after successful registration?

**Option 1:** Return user data only (no tokens)
```json
{
  "message": "Registration successful. Please login with your Credentials.",
}
```

**Option 2:** Return user data + JWT tokens (auto-login)
```json
{
  "message": "Registration successful",
  "user": {...},
  "access_token": "...",
  "refresh_token": "..."
}
```

**Which option? 1 or 2?**
**Your Answer:**

1
---

### 🔑 LOGIN ENDPOINT

#### Q2.1: Login Credentials
What can users use to login?

- [ ] Email + Password
- [ ] Username + Password
- [ ] Either Email OR Username + Password

**Your Answer:**
Either Email OR Username + Password

#### Q2.2: Login Response
What should login return?

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {
    "id": "uuid",
    "email": "...",
    "username": "...",
    "first_name": "...",
    // Include specializations?
    // Include wallet balance?
    // Include certificates?
  }
}
```


**Should the response include:**
- [ ] User's specializations?
- [ ] User's wallet balance?
- [ ] User's certificates?
- [ ] Profile image URL?

**Your Answer:**
redirect to home page which needs wallet balance and profile image URL

#### Q2.3: Failed Login Attempts
Do you want to track/limit failed login attempts?
- Allow unlimited attempts?
- Lock account after X failed attempts?
- Add rate limiting?

**Your Answer:**
more than 5 attempts in one session lock for 15 min

#### Q2.4: Unverified Email Login
If user hasn't verified email yet, can they still login?
- [ ] Yes, allow login (but show "email not verified")
- [ ] No, block login until email verified

**Your Answer:**
no block login until email verified 

---

### ✉️ EMAIL VERIFICATION WITH OTP

#### Q3.1: OTP Details
**OTP Length:** How many digits? (e.g., 4, 6, 8)

**Your Answer:**
6 digits


**OTP Validity:** How long is OTP valid? (e.g., 5 minutes, 10 minutes, 30 minutes)

**Your Answer:**
5 minutes


**OTP Format:** 
- Numeric only (e.g., 123456)
- Alphanumeric (e.g., A1B2C3)

**Your Answer:**
Numeric only


#### Q3.2: OTP Storage
Where should we store OTP codes?

**Option A:** In database (new model: EmailVerification)
```python
class EmailVerification(models.Model):
    user = models.ForeignKey(User)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
```

**Option B:** In cache/Redis (faster, auto-expires)
```python
# Store in Django cache with TTL
cache.set(f'otp_{user.email}', otp_code, timeout=300)  # 5 min
```

**Which option? A or B?**

**Your Answer:**
B

#### Q3.3: Resend OTP
Can users request a new OTP?
- How long to wait before resending? (e.g., 60 seconds)
- Maximum resend attempts? (e.g., 3 times)

**Your Answer:**
60 seconds
3 times

#### Q3.4: Gmail Configuration
**Gmail Account for Sending:**
- Will you use your personal Gmail?
- Create a new Gmail account for the app?
- Use Gmail App Password (required for SMTP)?

**Your Answer:**
- Create a new Gmail account for the app? we already have one

**Email Template:**
What should the verification email look like?

**Option 1 - Simple:**
```
Subject: Verify your xBrain account

Your verification code is: 123456

This code will expire in 10 minutes.
```

**Option 2 - Detailed:**
```
Subject: Welcome to xBrain! Verify your email

Hi [First Name],

Thank you for joining xBrain!

Your verification code is: 123456

This code will expire in 10 minutes.

If you didn't create an account, please ignore this email.

Best regards,
The xBrain Team
```

**Which style? 1 or 2?**

**Your Answer:**
2

#### Q3.5: Verification Endpoint
After receiving OTP, how does user verify?

**POST /api/auth/verify-email/**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response on success:**
```json
{
  "message": "Email verified successfully",
  // Auto-login after verification?
  "access_token": "...",  // Include this?
  "refresh_token": "..."  // Include this?
}
```

**Should we auto-login after email verification?**

**Your Answer:**
Yes
---

## 🎯 SUGGESTED IMPLEMENTATION APPROACH

### Step 1: Email Backend Setup
```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Not regular password!
DEFAULT_FROM_EMAIL = 'xBrain <your-email@gmail.com>'
```

### Step 2: Create Serializers
- `UserRegistrationSerializer`
- `UserLoginSerializer`
- `EmailVerificationSerializer`
- `UserDetailSerializer` (for responses)

### Step 3: Create Views/ViewSets
- `RegisterView` (POST only)
- `LoginView` (POST only)
- `VerifyEmailView` (POST only)
- `ResendOTPView` (POST only)

### Step 4: URL Configuration
```python
urlpatterns = [
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/verify-email/', VerifyEmailView.as_view()),
    path('api/auth/resend-otp/', ResendOTPView.as_view()),
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),
]
```

### Step 5: OTP Generation & Sending
- Generate random OTP
- Store in database/cache
- Send email via Gmail SMTP
- Set expiration time

### Step 6: Testing
- Test registration
- Test OTP email delivery
- Test OTP verification
- Test login

---

## 📦 Additional Packages Needed

```bash
pip install django-environ  # For environment variables (Gmail password)
```

---

## 🔒 Security Considerations

### For Production:
1. **Environment Variables**
   - Store Gmail credentials in `.env` file
   - Never commit passwords to Git

2. **Rate Limiting**
   - Limit OTP requests (prevent spam)
   - Limit login attempts (prevent brute force)

3. **HTTPS Only**
   - Email credentials only over HTTPS in production

4. **OTP Security**
   - Use cryptographically secure random generator
   - Expire OTPs after time limit
   - Invalidate after successful verification

---

## 📁 Files We'll Create/Modify

### New Files:
- `api/serializers.py` (NEW)
- `api/views.py` (UPDATE from default)
- `api/urls.py` (NEW)
- `api/utils.py` (NEW - for OTP generation)
- `.env` (NEW - for Gmail credentials)

### Modified Files:
- `api/models.py` (possibly add EmailVerification model)
- `xBrain/settings.py` (add email configuration)
- `xBrain/urls.py` (include api.urls)
- `requirements.txt` (add django-environ)

---

## ⏱️ Estimated Time

- **Registration Endpoint:** 1-2 hours
- **Login Endpoint:** 1 hour
- **Email Verification with OTP:** 2-3 hours
- **Testing & Debugging:** 1-2 hours

**Total: 5-8 hours** (achievable in one day!)

---

## 🎓 What You'll Learn

- JWT token authentication
- Django serializers and validation
- Email sending with SMTP
- OTP generation and verification
- API endpoint creation
- Environment variable management

---

## ✅ SUCCESS CRITERIA

By end of today, you should have:

- [x] User can register with email/username/password
- [x] OTP sent to user's email
- [x] User can verify email with OTP
- [x] User can login and receive JWT tokens
- [x] Proper error handling for all cases
- [x] All endpoints tested and working

---

## 🚀 READY TO START?

**Please answer all the questions above, then I will:**
1. Create all serializers
2. Create all views
3. Configure email backend
4. Set up URLs
5. Create OTP utility functions
6. Add comprehensive error handling
7. Create testing guide

**Waiting for your answers!** 📝
xBrain2026@gmail
BrainX@2026