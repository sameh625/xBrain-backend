# Explaino Project - Complete Reference Document

## Project Overview
**Explaino** is a mobile application designed to connect users who seek explanations or clarifications on specific topics with other knowledgeable users willing to help. The application focuses on knowledge sharing through questions, answers, posts, and scheduled one-on-one explanation sessions.

### Core Functionality
- Users can ask questions that require detailed explanations
- Users can respond to others' questions
- Users can share tips or quick informational posts
- Private communication to schedule online meetings via Google Meet
- Points-based reward mechanism for active participation

### Technology Stack
- **Backend**: Django REST Framework
- **Database**: PostgreSQL (recommended for production)

---

## Database Entities & Relationships

### 1. User Entity
**Purpose**: Represents registered users of the application

**Attributes**:
- `user_id` (PK): Unique identifier for each user
- `username`: Unique username for login
- `email`: User's email address (unique)
- `password_hash`: Encrypted password
- `bio`: User's biography/description
- `profile_image`: URL/path to profile image
- `created_at`: Account creation timestamp

**Relationships**:
- Has many Specializations (many-to-many)
- Has one PointsWallet (one-to-one)
- Has many Certificates (one-to-many)
- Asks many Questions (one-to-many)
- Provides many Answers (one-to-many)
- Creates many Posts (one-to-many)
- Writes many Comments (one-to-many)
- Participates in many Chats (many-to-many)
- Sends many Messages (one-to-many)
- Schedules many Meetings (one-to-many as organizer/explainer)

---

### 2. Specialization Entity
**Purpose**: Represents areas of expertise that users can select

**Attributes**:
- `specialization_id` (PK): Unique identifier
- `name`: Name of the specialization (e.g., "Python Programming", "Calculus")
- `description`: Detailed description of the specialization

**Relationships**:
- Has many Users (many-to-many through UserSpecialization)

---

### 3. UserSpecialization Entity (Junction Table)
**Purpose**: Links users with their specializations

**Attributes**:
- `user_id` (FK, composite PK)
- `specialization_id` (FK, composite PK)

---

### 4. Question Entity
**Purpose**: Represents questions asked by users

**Attributes**:
- `question_id` (PK): Unique identifier
- `title`: Question title/subject
- `content`: Detailed question content
- `asked_by` (FK): Reference to User who asked
- `specialization_id` (FK): Related specialization
- `created_at`: When question was posted
- `updated_at`: Last modification timestamp
- `is_resolved`: Boolean flag indicating if question is answered

**Relationships**:
- Belongs to one User (asker)
- Belongs to one Specialization
- Has many Answers (one-to-many)

---

### 5. Answer Entity
**Purpose**: Represents answers/explanations to questions

**Attributes**:
- `answer_id` (PK): Unique identifier
- `question_id` (FK): Reference to Question
- `answered_by` (FK): Reference to User who answered
- `content`: Answer content/explanation
- `created_at`: When answer was posted
- `updated_at`: Last modification timestamp
- `is_accepted`: Boolean flag if answer is marked as best answer

**Relationships**:
- Belongs to one Question
- Belongs to one User (answerer)

---

### 6. Post Entity
**Purpose**: Represents informational tips and quick knowledge posts

**Attributes**:
- `post_id` (PK): Unique identifier
- `title`: Post title
- `content`: Post content
- `posted_by` (FK): Reference to User who posted
- `specialization_id` (FK): Related specialization
- `created_at`: When post was created
- `updated_at`: Last modification timestamp

**Relationships**:
- Belongs to one User (author)
- Belongs to one Specialization
- Has many Comments (one-to-many)

---

### 7. Comment Entity
**Purpose**: Represents comments on posts

**Attributes**:
- `comment_id` (PK): Unique identifier
- `post_id` (FK): Reference to Post
- `commented_by` (FK): Reference to User who commented
- `content`: Comment content
- `created_at`: When comment was posted
- `updated_at`: Last modification timestamp

**Relationships**:
- Belongs to one Post
- Belongs to one User (commenter)

---

### 8. Chat Entity
**Purpose**: Represents private one-to-one chat conversations

**Attributes**:
- `chat_id` (PK): Unique identifier
- `user1_id` (FK): First participant
- `user2_id` (FK): Second participant
- `created_at`: When chat was initiated
- `last_message_at`: Timestamp of last message

**Relationships**:
- Has two Users (participants)
- Has many Messages (one-to-many)
- May lead to one or more Meetings

---

### 9. Message Entity
**Purpose**: Represents individual messages within chats

**Attributes**:
- `message_id` (PK): Unique identifier
- `chat_id` (FK): Reference to Chat
- `sender_id` (FK): Reference to User who sent message
- `content`: Message content
- `sent_at`: When message was sent
- `is_read`: Boolean flag for read status

**Relationships**:
- Belongs to one Chat
- Belongs to one User (sender)

---

### 10. Meeting Entity
**Purpose**: Represents scheduled explanation sessions

**Attributes**:
- `meeting_id` (PK): Unique identifier
- `chat_id` (FK): Reference to Chat where meeting was scheduled
- `organizer_id` (FK): User requesting explanation
- `explainer_id` (FK): User providing explanation
- `scheduled_at`: Scheduled meeting time
- `duration_minutes`: Expected duration
- `google_meet_link`: Generated Google Meet URL
- `status`: Meeting status (scheduled, completed, cancelled)
- `created_at`: When meeting was scheduled
- `points_amount`: Points to be transferred
- `is_completed`: Boolean flag

**Relationships**:
- Belongs to one Chat
- Has one organizer (User)
- Has one explainer (User)
- Creates one PointsTransaction upon completion

---

### 11. PointsWallet Entity
**Purpose**: Manages user's points balance

**Attributes**:
- `wallet_id` (PK): Unique identifier
- `user_id` (FK, unique): Reference to User (one-to-one)
- `balance`: Current points balance
- `updated_at`: Last update timestamp

**Relationships**:
- Belongs to one User (one-to-one)
- Tracks many PointsTransactions

---

### 12. PointsTransaction Entity
**Purpose**: Records all points transfers and transactions

**Attributes**:
- `transaction_id` (PK): Unique identifier
- `from_wallet_id` (FK): Source wallet (nullable for system rewards)
- `to_wallet_id` (FK): Destination wallet
- `amount`: Points transferred
- `transaction_type`: Type (meeting_completion, reward, penalty, etc.)
- `meeting_id` (FK, nullable): Related meeting if applicable
- `created_at`: Transaction timestamp
- `description`: Transaction description

**Relationships**:
- References two PointsWallets (sender and receiver)
- May reference one Meeting

---

### 13. Certificate Entity
**Purpose**: Stores user's professional certificates

**Attributes**:
- `certificate_id` (PK): Unique identifier
- `user_id` (FK): Reference to User
- `title`: Certificate name
- `issuer`: Issuing organization
- `issue_date`: When certificate was issued
- `file_url`: URL/path to certificate file/image

**Relationships**:
- Belongs to one User

---

## Business Logic & Rules

### Points System
1. **Initial Balance**: Each new user starts with a predefined initial balance
2. **Meeting Completion**: Points are automatically transferred from organizer to explainer upon meeting completion
3. **Transaction Tracking**: All point movements are logged in PointsTransaction table
4. **Transparency**: Users can view their transaction history

### Meeting Workflow
1. User initiates private chat
2. Users discuss and schedule a meeting
3. System generates Google Meet link
4. Meeting details are saved with status "scheduled"
5. After meeting, status is updated to "completed"
6. Points are automatically transferred
7. PointsTransaction record is created

### Question-Answer System
1. User posts question in specific specialization
2. Other users can provide answers
3. Question asker can mark an answer as "accepted"
4. Questions can be marked as "resolved"

---

## Questions to Clarify

### 1. User Authentication & Authorization
- Will you use Django's built-in User model or completely custom User model?
- Do you need different user roles (admin, moderator, regular user)?
- Will you implement email verification upon registration?
- Any social authentication (Google, Facebook)?

### 2. Points System Details
- What is the initial points balance for new users?
- How are meeting points calculated? (Fixed amount, duration-based, specialization-based?)
- Who sets the points amount for a meeting? (Organizer, Explainer, or System?)
- Can users manually transfer points to each other, or only through meetings?
- Are there any other ways to earn/lose points? (Daily login bonus, penalties, etc.)
- What happens if a user doesn't have enough points to schedule a meeting?

### 3. Meeting Management
- How is the Google Meet link generated? (Manual entry or API integration?)
- What happens if a meeting is cancelled? (Points refund policy?)
- Can users reschedule meetings?
- Is there a meeting review/rating system after completion?
- How do you verify that a meeting actually took place?
- Can users dispute meeting completion?

### 4. Content Moderation
- Do you need content moderation for questions, answers, posts, and comments?
- Will there be a reporting system for inappropriate content?
- Are there any restrictions on question/post length?

### 5. Specializations
- Will you have a predefined list of specializations, or can users create new ones?
- Can specializations have subcategories/hierarchies?
- Is there a limit to how many specializations a user can select?

### 6. Notifications
- What notification system will you use? (Push notifications, email, in-app?)
- What events trigger notifications? (New answer, meeting reminder, points received, etc.)

### 7. Search & Discovery
- How will users discover questions to answer?
- Will there be a search functionality for questions/posts?
- Will there be a feed/timeline showing recent activity?

### 8. Chat System
- Do you need real-time chat functionality?
- Will you use Django Channels with WebSockets or a third-party service?
- Can users send files/images in chat?
- Is there a chat history limit?

### 9. Privacy & Security
- Can users block other users?
- Can users make their profiles private?
- Are there any age restrictions?

### 10. Additional Features
- Will there be user following/followers system?
- Will there be bookmarking/saving questions or posts?
- Will answers and posts support rich text formatting or just plain text?
- Do you need file attachments for questions/answers/posts?

---

## Technical Considerations

### Database Indexes
- Composite index on (user_id, specialization_id) in UserSpecialization
- Index on question's asked_by, specialization_id, created_at
- Index on chat participants for quick lookup
- Index on transaction timestamps for reporting

### Data Validation
- Email format validation
- Username uniqueness and format
- Points balance cannot be negative
- Meeting scheduled_at must be in the future
- Transaction amounts must be positive

### API Endpoints Structure (Suggested)
```
/api/auth/register/
/api/auth/login/
/api/users/
/api/users/{id}/
/api/specializations/
/api/questions/
/api/questions/{id}/answers/
/api/posts/
/api/posts/{id}/comments/
/api/chats/
/api/chats/{id}/messages/
/api/meetings/
/api/wallet/
/api/transactions/
/api/certificates/
```

---

## Next Steps
Once you answer the clarification questions, I will:
1. Create complete Django models with all relationships
2. Add appropriate field validations
3. Include indexes for performance
4. Add Meta classes with ordering and constraints
5. Create serializers for Django REST Framework
6. Suggest additional utility methods for models
