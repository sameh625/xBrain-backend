# Questions for First Release - Option A (5 Entities Only)

## 📋 Status: [ANSWERED] / [PENDING]

---

## 1. USER MODEL

### Q1.1: Django's built-in User vs Custom User?
**Answer:** Custom User model

### Q1.2: Required user fields?
**Question:** Besides username, email, password_hash, bio, profile_image, created_at - do you need:
- `first_name` and `last_name`?
- `phone_number`?
- `is_active` flag (for account activation/deactivation)?
- `last_login` timestamp?

**Answer:** 
- `first_name` and `last_name`? yes
- `phone_number`? yes
- `is_active` flag (for account activation/deactivation)? no
- `last_login` timestamp? no

### Q1.3: Email verification?
**Question:** Do new users need to verify their email before accessing the platform?

**Answer:** 
do you mean by verify that the user verify with otp or what ?

### Q1.4: Username and email constraints?
**Question:** 
- Should username be case-sensitive?
- Any restrictions on username format (alphanumeric only, special characters allowed)?
- Minimum/maximum length for username?

**Answer:** 
- Should username be case-sensitive? no 
- Any restrictions on username format (alphanumeric only, special characters allowed)?  yes both allowed and must start with char (like all platforms)
- Minimum/maximum length for username? 8-16
---

## 2. SPECIALIZATION

### Q2.1: Who manages specializations?
**Answer:** Predefined list (admin-managed)

### Q2.2: Initial specializations?
**Question:** What are the initial specializations you want in the system? (e.g., "Python Programming", "Mathematics", "Physics", "Web Development", etc.)

**Answer:** 
Back-end development
Front-end development
Mobile development
Data science
Machine learning
Artificial intelligence
Cybersecurity
Cloud computing
DevOps
Databases

### Q2.3: Specialization constraints?
**Question:** 
- Can a user select multiple specializations?
- Any limit on number of specializations per user?
- Can specializations be added/removed later?

**Answer:** 
- Can a user select multiple specializations? yes
- Any limit on number of specializations per user? no limit
- Can specializations be added/removed later? yes 
---

## 3. POINTS WALLET

### Q3.1: Initial balance?
**Answer:** Leave it for now (will be configurable)

### Q3.2: Balance constraints?
**Question:** 
- Can balance be negative?
- Maximum balance limit?
- What happens when wallet is created (automatic with user registration)?

**Answer:** 
- Can balance be negative? no
- Maximum balance limit? no limit
- What happens when wallet is created (automatic with user registration)? yes 
### Q3.3: Manual point adjustments?
**Question:** Should admins be able to manually add/remove points from user wallets?

**Answer:** yes 

---

## 4. CERTIFICATE

### Q4.1: File upload location?
**Question:** Where should certificate files be stored?
- Local filesystem (media folder)?
- Cloud storage (AWS S3, Google Cloud Storage)?

**Answer:** it will be just a link to the certificate not the file itself 

### Q4.2: Certificate validation?
**Question:** 
- Any file type restrictions (PDF only, images allowed)?
- Maximum file size?
- Is certificate approval needed (admin review)?

**Answer:** 
- Any file type restrictions (PDF only, images allowed)?
- Maximum file size?
- Is certificate approval needed (admin review)? no 

it will be a link not a pdf file or image

### Q4.3: Certificate visibility?
**Question:** Are certificates visible on user profiles to everyone, or only to the user?

**Answer:** 
to everyone
---

## 5. GENERAL QUESTIONS

### Q5.1: Primary Key format?
**Question:** Do you want:
- Auto-incrementing integers (1, 2, 3...)?
- UUIDs for better security and scalability? 

**Answer:** 
UUIDs 
### Q5.2: Soft delete vs Hard delete?
**Question:** When users delete data (certificates, etc.), should it be:
- **Hard delete**: Permanently removed from database
- **Soft delete**: Marked as deleted but kept in database (with `is_deleted` flag)

**Answer:** 
Hard delete 
### Q5.3: Timestamps?
**Question:** Should all tables have `created_at` and `updated_at` timestamps?

**Answer:** 
depends if we need it just add it 
---

## 6. API REQUIREMENTS

### Q6.1: Authentication method?
**Question:** Which authentication will you use for REST API?
- Token-based (Django REST Framework tokens)?
- JWT (JSON Web Tokens)?
- Session-based?

**Answer:** 
choose the best for our project 


### Q6.2: Pagination?
**Question:** Default pagination settings for listing endpoints?
- Page size (e.g., 10, 20, 50 items per page)?

**Answer:** 
is it related to the endpoints 
---

## Notes & Additional Context

we will just implement the backend 
we will use postgresql as the database