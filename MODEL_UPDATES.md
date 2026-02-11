# 🔄 Model Updates - Changes Summary

## ✅ Changes Completed

### 1. **Profile Image Field Changed**
**From:** `URLField` (storing image URLs)
**To:** `ImageField` (storing actual image files)

```python
# Before
profile_image = models.URLField(
    _('profile image'),
    max_length=500,
    blank=True,
    null=True,
    help_text="URL to user's profile image"
)

# After
profile_image = models.ImageField(
    _('profile image'),
    upload_to='profile_images/',  # Images will be stored in media/profile_images/
    blank=True,
    null=True,
    help_text="User's profile image"
)
```

**What this means:**
- Users can now upload actual image files
- Images will be stored in `/media/profile_images/` directory
- Supports all common image formats (JPG, PNG, GIF, etc.)
- No longer using external URLs

---

### 2. **Timestamps Removed from Most Models**

**Removed `created_at` and `updated_at` from:**
- ✅ Specialization
- ✅ UserSpecialization (also removed `added_at`)
- ✅ PointsWallet
- ✅ Certificate

**Kept timestamps ONLY in:**
- ✅ User model (`created_at` and `updated_at`)

---

### 3. **Settings Configuration Updated**

**Added media files configuration:**
```python
# Media files (User uploaded files - profile images, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

**Updated URLs configuration:**
```python
# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 📊 Updated Model Structure

### User Model
```python
User
├── id (UUID)
├── email (unique, login)
├── username (8-16 chars, case-insensitive)
├── password
├── first_name
├── last_name
├── phone_number (unique, validated)
├── bio
├── profile_image (ImageField) ← CHANGED
├── specializations (ManyToMany)
├── created_at ← KEPT
└── updated_at ← KEPT
```

### Specialization Model
```python
Specialization
├── id (UUID)
├── name (unique)
└── description
    ❌ No timestamps
```

### UserSpecialization Model
```python
UserSpecialization
├── id (UUID)
├── user (FK)
└── specialization (FK)
    ❌ No timestamps (removed added_at)
```

### PointsWallet Model
```python
PointsWallet
├── id (UUID)
├── user (OneToOne)
└── balance
    ❌ No timestamps
```

### Certificate Model
```python
Certificate
├── id (UUID)
├── user (FK)
├── title
├── issuer
├── issue_date
└── certificate_url (still URL, not file)
    ❌ No timestamps
```

---

## 🚀 Next Steps - Database Migration

### ⚠️ IMPORTANT: You need to create new migrations!

```bash
# 1. Create new migration (REQUIRED)
python manage.py makemigrations api

# 2. Apply migrations
python manage.py migrate
```

**What the migration will do:**
- Change `profile_image` column from VARCHAR (URL) to VARCHAR (file path)
- Drop `created_at` and `updated_at` columns from:
  - specializations table
  - user_specializations table
  - points_wallets table
  - certificates table

---

## 📁 File Structure

After running your app, Django will create:

```
xBrain/
├── media/                          ← Created automatically
│   └── profile_images/             ← Profile images stored here
│       ├── user1_profile.jpg
│       ├── user2_profile.png
│       └── ...
├── api/
│   ├── models.py                   ← UPDATED
│   └── ...
└── xBrain/
    ├── settings.py                 ← UPDATED
    └── urls.py                     ← UPDATED
```

---

## 🧪 Testing Image Upload

### In Django Admin:
1. Run: `python manage.py runserver`
2. Go to: http://localhost:8000/admin
3. Create/Edit a user
4. You'll see a file upload button for profile_image
5. Upload an image → it saves to `/media/profile_images/`

### Via API (Future):
```python
# POST /api/users/me/
# Content-Type: multipart/form-data

{
    "first_name": "John",
    "last_name": "Doe",
    "profile_image": <FILE>  # Actual image file
}
```

### Accessing Images:
```
Image URL: http://localhost:8000/media/profile_images/filename.jpg
```

---

## 📝 Ordering Changes

### Before:
```python
Specialization: ordered by ['name']
UserSpecialization: ordered by ['added_at']
PointsWallet: ordered by ['-updated_at']
Certificate: ordered by ['-issue_date']
```

### After:
```python
Specialization: ordered by ['name'] ← Same
UserSpecialization: No ordering (removed)
PointsWallet: No ordering (removed)
Certificate: ordered by ['-issue_date'] ← Same
```

---

## ⚠️ Breaking Changes

### 1. **Profile Image Field**
- **Before:** Stored URLs (e.g., "https://example.com/image.jpg")
- **After:** Stores file paths (e.g., "profile_images/filename.jpg")
- **Impact:** Existing profile image URLs will need to be migrated or removed

### 2. **Missing Timestamps**
- **Before:** All models had `created_at` and `updated_at`
- **After:** Only User model has timestamps
- **Impact:** 
  - Can't track when specializations were created
  - Can't track when user added a specialization
  - Can't track wallet last update time
  - Can't track when certificates were added

---

## 💡 Recommendations

### For Profile Images:
1. **Set max file size** in your serializer/form validation
2. **Add image validation** (dimensions, format)
3. **Consider image optimization** (resize large images)
4. **Use cloud storage** in production (AWS S3, Cloudinary)

Example max size validation:
```python
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

def validate_image_size(image):
    file_size = image.size
    limit_mb = 5
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Max file size is {limit_mb}MB")

profile_image = models.ImageField(
    upload_to='profile_images/',
    validators=[
        FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif']),
        validate_image_size
    ]
)
```

---

## 🐛 Potential Issues

### Issue 1: Pillow not installed
**Error:** `Cannot use ImageField because Pillow is not installed.`

**Solution:**
```bash
pip install Pillow
```

**Note:** Pillow is already in `requirements.txt`, so this should be fine!

---

### Issue 2: Media files not served
**Error:** 404 when accessing `/media/profile_images/image.jpg`

**Solution:** 
- Check `settings.DEBUG = True` (media only served in development)
- Check `urls.py` has media configuration
- In production, use Nginx/Apache to serve media files

---

## ✅ Updated Requirements

Your `requirements.txt` already includes Pillow, so you're all set!

```txt
Django==5.2.5
djangorestframework==3.15.2
djangorestframework-simplejwt==5.4.0
django-cors-headers==4.6.0
psycopg2-binary==2.9.10
python-decouple==3.8
Pillow==11.0.0  ← Required for ImageField
django-filter==24.3
```

---

## 📊 Migration Preview

When you run `makemigrations`, Django will create something like:

```python
operations = [
    migrations.AlterField(
        model_name='user',
        name='profile_image',
        field=models.ImageField(upload_to='profile_images/', blank=True, null=True),
    ),
    migrations.RemoveField(
        model_name='specialization',
        name='created_at',
    ),
    migrations.RemoveField(
        model_name='specialization',
        name='updated_at',
    ),
    # ... more RemoveField operations
]
```

---

## 🎉 Summary

✅ Profile image is now `ImageField` (actual file uploads)  
✅ Timestamps removed from all models except User  
✅ Media configuration added to settings  
✅ URLs configured to serve media files  
✅ Pillow already in requirements  
✅ Ready to create migrations!

**Next command:**
```bash
python manage.py makemigrations api
python manage.py migrate
```
