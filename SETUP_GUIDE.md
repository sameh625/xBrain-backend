# Explaino - Setup and Migration Guide

## 📋 What We've Built

### ✅ Models Created (5 Entities)
1. **User** - Custom user model with email authentication
2. **Specialization** - Tech specializations (Backend, AI, etc.)
3. **UserSpecialization** - Junction table (many-to-many)
4. **PointsWallet** - Points system (one-to-one with User)
5. **Certificate** - User certificates (URL links)

### ✅ Configuration Complete
- ✅ Custom User Model with UUID primary keys
- ✅ PostgreSQL database configuration
- ✅ JWT Authentication (djangorestframework-simplejwt)
- ✅ CORS enabled for mobile app
- ✅ REST Framework with pagination (20 items/page)
- ✅ Proper validators and indexes

---

## 🚀 Next Steps - Setup Instructions

### Step 1: Install Required Packages

```bash
cd /home/sameh/4th/grad_project/xBrain
pip install djangorestframework djangorestframework-simplejwt django-cors-headers psycopg2-binary
```

**Package Explanations:**
- `djangorestframework` - REST API framework
- `djangorestframework-simplejwt` - JWT authentication
- `django-cors-headers` - CORS support for mobile apps
- `psycopg2-binary` - PostgreSQL adapter for Python

---

### Step 2: Create PostgreSQL Database

**Option A: Using psql command line**
```bash
sudo -u postgres psql
```

Then in PostgreSQL shell:
```sql
CREATE DATABASE xbrain_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE xbrain_db TO postgres;
\q
```

**Option B: If PostgreSQL is not installed**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

### Step 3: Update Database Credentials (if needed)

Open `/home/sameh/4th/grad_project/xBrain/xBrain/settings.py` and update lines 80-82:

```python
"USER": "your_postgres_username",
"PASSWORD": "your_postgres_password",
```

---

### Step 4: Create Database Migrations

```bash
cd /home/sameh/4th/grad_project/xBrain
python manage.py makemigrations api
```

This will create migration files for all 5 models.

---

### Step 5: Apply Migrations

```bash
python manage.py migrate
```

This will create all database tables with proper relationships and indexes.

---

### Step 6: Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

You'll be prompted for:
- Email (used for login)
- Username (8-16 chars, must start with letter)
- Password

**Note:** A PointsWallet will be automatically created for this user!

---

### Step 7: Seed Initial Specializations

Create a file `/home/sameh/4th/grad_project/xBrain/seed_specializations.py`:

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xBrain.settings')
django.setup()

from api.models import Specialization

specializations = [
    {"name": "Back-end development", "description": "Server-side development, APIs, databases"},
    {"name": "Front-end development", "description": "User interfaces, responsive design, web applications"},
    {"name": "Mobile development", "description": "iOS, Android, React Native, Flutter"},
    {"name": "Data science", "description": "Data analysis, statistics, visualization"},
    {"name": "Machine learning", "description": "ML algorithms, model training, neural networks"},
    {"name": "Artificial intelligence", "description": "AI systems, NLP, computer vision"},
    {"name": "Cybersecurity", "description": "Network security, ethical hacking, penetration testing"},
    {"name": "Cloud computing", "description": "AWS, Azure, GCP, cloud architecture"},
    {"name": "DevOps", "description": "CI/CD, Docker, Kubernetes, automation"},
    {"name": "Databases", "description": "SQL, NoSQL, database design and optimization"},
]

for spec_data in specializations:
    spec, created = Specialization.objects.get_or_create(
        name=spec_data["name"],
        defaults={"description": spec_data["description"]}
    )
    if created:
        print(f"✅ Created: {spec.name}")
    else:
        print(f"⏭️  Already exists: {spec.name}")

print(f"\n✅ Total specializations: {Specialization.objects.count()}")
```

Run it:
```bash
python seed_specializations.py
```

---

## 🔧 Model Features Explained

### User Model
```python
# Key Features:
- UUID primary key (secure, scalable)
- Email-based authentication
- Case-insensitive username (8-16 chars, must start with letter)
- Phone number validation
- Profile image (URL)
- Many-to-many with Specializations
- Auto-created PointsWallet (via signals - see Step 8)
```

### Specialization Model
```python
# Key Features:
- UUID primary key
- Unique name with index
- Admin-managed (predefined list)
```

### UserSpecialization (Junction Table)
```python
# Key Features:
- Handles User <-> Specialization many-to-many
- Prevents duplicate relationships
- Tracks when specialization was added
```

### PointsWallet Model
```python
# Key Features:
- One-to-one with User
- Balance cannot be negative (PositiveIntegerField)
- Helper methods: add_points(), deduct_points()
- Automatic creation needed (via signals)
```

### Certificate Model
```python
# Key Features:
- Stores URL links (not files)
- Visible to everyone
- Associated with User (one-to-many)
```

---

## Step 8: Create Signal to Auto-Create PointsWallet

Create `/home/sameh/4th/grad_project/xBrain/api/signals.py`:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, PointsWallet


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Automatically create a PointsWallet when a new User is created
    """
    if created:
        PointsWallet.objects.create(user=instance, balance=0)
        print(f"✅ Created wallet for user: {instance.username}")


@receiver(post_save, sender=User)
def save_user_wallet(sender, instance, **kwargs):
    """
    Save the wallet when user is saved
    """
    if hasattr(instance, 'wallet'):
        instance.wallet.save()
```

Update `/home/sameh/4th/grad_project/xBrain/api/apps.py`:

```python
from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        import api.signals  # Import signals when app is ready
```

---

## 🧪 Testing the Models

### Test in Django Shell
```bash
python manage.py shell
```

```python
from api.models import User, Specialization, UserSpecialization, PointsWallet, Certificate

# Create a user
user = User.objects.create_user(
    email='john@example.com',
    username='johndoe123',
    password='secure_password',
    first_name='John',
    last_name='Doe',
    phone_number='+1234567890',
    bio='Full-stack developer'
)

# Check wallet was auto-created
print(user.wallet.balance)  # Should print: 0

# Add specializations
backend = Specialization.objects.get(name='Back-end development')
frontend = Specialization.objects.get(name='Front-end development')

user.specializations.add(backend, frontend)

# Add points
user.wallet.add_points(100)
print(user.wallet.balance)  # Should print: 100

# Add certificate
from datetime import date
cert = Certificate.objects.create(
    user=user,
    title='AWS Certified Solutions Architect',
    issuer='Amazon Web Services',
    issue_date=date(2024, 1, 15),
    certificate_url='https://example.com/certificate/12345'
)

# Query user's data
print(f"User: {user.get_full_name()}")
print(f"Specializations: {user.specializations.count()}")
print(f"Certificates: {user.certificates.count()}")
print(f"Points: {user.wallet.balance}")
```

---

## 📊 Database Schema Overview

```
users
├── id (UUID, PK)
├── email (unique, indexed)
├── username (unique, indexed, case-insensitive)
├── password
├── first_name
├── last_name
├── phone_number (unique, validated)
├── bio
├── profile_image (URL)
├── created_at (indexed)
└── updated_at

specializations
├── id (UUID, PK)
├── name (unique, indexed)
├── description
├── created_at
└── updated_at

user_specializations (Junction Table)
├── id (UUID, PK)
├── user_id (FK -> users)
├── specialization_id (FK -> specializations)
├── added_at
└── UNIQUE(user_id, specialization_id)

points_wallets
├── id (UUID, PK)
├── user_id (FK -> users, one-to-one, unique)
├── balance (non-negative integer)
├── created_at
└── updated_at (indexed)

certificates
├── id (UUID, PK)
├── user_id (FK -> users)
├── title
├── issuer
├── issue_date (indexed)
├── certificate_url
├── created_at
└── updated_at
```

---

## 🔐 Authentication Flow with JWT

### 1. Register/Create User
```http
POST /api/auth/register/
{
  "email": "user@example.com",
  "username": "username123",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890"
}
```

### 2. Login (Get JWT Tokens)
```http
POST /api/auth/token/
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 3. Use Access Token
```http
GET /api/users/me/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 4. Refresh Token (when access expires)
```http
POST /api/auth/token/refresh/
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response:
{
  "access": "new_access_token..."
}
```

---

## 📝 Next Development Steps

After setup, you'll need to create:

1. **Serializers** (`api/serializers.py`)
   - UserSerializer
   - SpecializationSerializer
   - CertificateSerializer
   - PointsWalletSerializer

2. **ViewSets** (`api/views.py`)
   - UserViewSet
   - SpecializationViewSet
   - CertificateViewSet

3. **URLs** (`api/urls.py`)
   - REST API endpoints
   - JWT authentication endpoints

4. **Admin Panel** (`api/admin.py`)
   - Register models for Django admin

---

## ⚠️ Important Notes

1. **Username is case-insensitive**: "JohnDoe" and "johndoe" are the same
2. **Email is used for login**: Not username
3. **Phone numbers must be unique**
4. **PointsWallet is auto-created** with User (via signals)
5. **Certificates are URL links**: Not file uploads
6. **All primary keys are UUIDs**: For security and scalability
7. **Balance cannot be negative**: Use add_points() and deduct_points() methods

---

## 🐛 Troubleshooting

### Migration Errors
```bash
# Reset migrations (CAREFUL - deletes data!)
python manage.py migrate api zero
python manage.py makemigrations api
python manage.py migrate
```

### PostgreSQL Connection Error
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Import Errors
```bash
# Reinstall packages
pip install --upgrade djangorestframework djangorestframework-simplejwt django-cors-headers psycopg2-binary
```

---

## 📞 Questions Answered

✅ **Email verification?** - Skipped for now (can add OTP later)
✅ **Authentication?** - JWT (best for mobile apps)
✅ **Pagination?** - Yes, 20 items per page
✅ **Database?** - PostgreSQL
✅ **Primary Keys?** - UUIDs
✅ **Delete strategy?** - Hard delete
✅ **Timestamps?** - Added where needed
