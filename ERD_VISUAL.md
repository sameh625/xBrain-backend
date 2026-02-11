# Explaino Database - Entity Relationship Diagram (ERD)

## 📊 Visual Representation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATABASE SCHEMA                                 │
│                     Explaino - First Release                             │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                    📱 USER                           │
├──────────────────────────────────────────────────────┤
│ 🔑 id                    UUID (PK)                   │
│ ✉️  email                EmailField (unique, login)  │
│ 👤 username              CharField (unique, 8-16)    │
│ 🔒 password              CharField (hashed)          │
│ 📝 first_name            CharField                   │
│ 📝 last_name             CharField                   │
│ 📞 phone_number          CharField (unique)          │
│ 📄 bio                   TextField                   │
│ 🖼️  profile_image        URLField                    │
│ ⏰ created_at            DateTimeField               │
│ 🔄 updated_at            DateTimeField               │
└──────────────────────────────────────────────────────┘
           │                                  │
           │ 1                                │ 1
           │                                  │
           │ 1:1                              │ 1:N
           ▼                                  ▼
┌─────────────────────────┐        ┌────────────────────────────┐
│   💰 POINTS_WALLET      │        │   🎓 CERTIFICATE           │
├─────────────────────────┤        ├────────────────────────────┤
│ 🔑 id         UUID (PK) │        │ 🔑 id              UUID    │
│ 🔗 user_id    UUID (FK) │        │ 🔗 user_id         UUID    │
│ 💵 balance    Integer   │        │ 📜 title           Char    │
│ ⏰ created_at DateTime  │        │ 🏢 issuer          Char    │
│ 🔄 updated_at DateTime  │        │ 📅 issue_date      Date    │
└─────────────────────────┘        │ 🔗 certificate_url URL     │
   Auto-created via signal         │ ⏰ created_at      DateTime│
   Balance ≥ 0 (enforced)          │ 🔄 updated_at      DateTime│
                                    └────────────────────────────┘
                                       Visible to everyone



           ┌─────────────────────────┐
           │      📱 USER            │
           └─────────────────────────┘
                     │
                     │ N
                     │
                     ▼
        ┌──────────────────────────────┐
        │  USER_SPECIALIZATION         │
        │  (Junction Table)            │
        ├──────────────────────────────┤
        │ 🔑 id                 UUID   │
        │ 🔗 user_id            UUID   │
        │ 🔗 specialization_id  UUID   │
        │ ⏰ added_at          DateTime│
        └──────────────────────────────┘
                     │
                     │ N
                     │
                     ▼
        ┌──────────────────────────────┐
        │   🎯 SPECIALIZATION          │
        ├──────────────────────────────┤
        │ 🔑 id            UUID (PK)   │
        │ 📝 name          CharField    │
        │ 📄 description   TextField    │
        │ ⏰ created_at    DateTimeField│
        │ 🔄 updated_at    DateTimeField│
        └──────────────────────────────┘
           Predefined by admin
           10 specializations


═══════════════════════════════════════════════════════════════

## 🔗 Relationships Summary

1️⃣  **User ↔️ PointsWallet**  
   └─ One-to-One  
   └─ Auto-created when user is created  
   └─ Cascade delete (if user deleted, wallet deleted)

2️⃣  **User ↔️ Certificate**  
   └─ One-to-Many  
   └─ One user can have many certificates  
   └─ Cascade delete (if user deleted, certificates deleted)

3️⃣  **User ↔️ Specialization**  
   └─ Many-to-Many (through UserSpecialization)  
   └─ One user can have many specializations  
   └─ One specialization can have many users  
   └─ No limit on number of specializations per user


═══════════════════════════════════════════════════════════════

## 🎯 Constraints & Rules

### User
✅ Email must be unique (used for login)
✅ Username must be unique (case-insensitive)
✅ Username: 8-16 characters, starts with letter
✅ Phone number must be unique
✅ Phone number format: +1234567890 (7-15 digits)

### PointsWallet
✅ One wallet per user (enforced by OneToOneField)
✅ Balance cannot be negative (PositiveIntegerField)
✅ Automatically created when user is created

### Certificate
✅ URL must be valid
✅ Multiple certificates per user allowed
✅ Visible to everyone

### Specialization
✅ Name must be unique
✅ Admin-managed (predefined list)

### UserSpecialization
✅ Unique constraint: (user, specialization)
✅ Prevents duplicate user-specialization pairs


═══════════════════════════════════════════════════════════════

## 📈 Database Indexes (For Performance)

### User Table
├─ email (unique index)
├─ username (unique index)
└─ created_at (index)

### PointsWallet Table
├─ user_id (unique index - one-to-one)
└─ updated_at (index)

### Certificate Table
├─ user_id (index)
└─ issue_date (index)

### Specialization Table
└─ name (unique index)

### UserSpecialization Table
└─ (user_id, specialization_id) composite index


═══════════════════════════════════════════════════════════════

## 💾 Example Data Flow

### 1. User Registration
```
1. User registers with email + password
2. Django creates User record
3. Signal triggers → PointsWallet created automatically
4. User can now add specializations
5. User can now add certificates
```

### 2. Adding Specialization
```
1. Fetch available specializations
2. User selects "Back-end development"
3. UserSpecialization record created
4. User can select more (no limit)
```

### 3. Points Transaction (Future)
```
1. User A earns points from meeting
2. wallet.add_points(100) called
3. Balance updated: 0 → 100
4. Timestamp updated automatically
```


═══════════════════════════════════════════════════════════════

## 🔄 Cascade Behavior

```
DELETE User
  ├─→ DELETE PointsWallet (one-to-one, cascade)
  ├─→ DELETE all Certificates (one-to-many, cascade)
  └─→ DELETE all UserSpecializations (junction table, cascade)
      (Specialization records remain intact)

DELETE Specialization
  └─→ DELETE all UserSpecializations referencing it
      (User records remain intact)
```


═══════════════════════════════════════════════════════════════

## 📊 Table Statistics (After Seeding)

```
users                   → 0 records (until you add users)
specializations         → 10 records (predefined)
user_specializations    → 0 records (until users select)
points_wallets          → 0 records (auto-created with users)
certificates            → 0 records (until users add)
```


═══════════════════════════════════════════════════════════════

## 🎓 10 Predefined Specializations

1. Back-end development
2. Front-end development
3. Mobile development
4. Data science
5. Machine learning
6. Artificial intelligence
7. Cybersecurity
8. Cloud computing
9. DevOps
10. Databases


═══════════════════════════════════════════════════════════════

## 🔐 Authentication Flow

```
┌─────────────┐
│   Mobile    │
│     App     │
└──────┬──────┘
       │
       │ POST /api/auth/register/
       │ { email, username, password, ... }
       ▼
┌─────────────────────┐
│   Django Backend    │
│                     │
│  1. Create User     │──┐
│  2. Hash password   │  │
│  3. Save to DB      │  │ Signal triggers
└─────────────────────┘  │
       │                 │
       │                 ▼
       │         ┌──────────────────┐
       │         │ Create Wallet    │
       │         │ balance = 0      │
       │         └──────────────────┘
       │
       │ POST /api/auth/token/
       │ { email, password }
       ▼
┌─────────────────────┐
│  JWT Token Service  │
│                     │
│  Returns:           │
│  - access_token     │
│  - refresh_token    │
└─────────────────────┘
       │
       ▼
┌─────────────┐
│   Mobile    │
│   Stores    │
│   Tokens    │
└─────────────┘
```

═══════════════════════════════════════════════════════════════
