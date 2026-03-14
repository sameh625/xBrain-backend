# xBrain API Backend

This is the backend API for the xBrain Flutter mobile application, built with Django and Django REST Framework (DRF).

## Live Application
🌍 **Live API Base URL:** `https://xbrain-backend-chbfe7hscpbqergn.francecentral-01.azurewebsites.net`

📖 **Interactive API Documentation (Swagger):** [https://xbrain-backend-chbfe7hscpbqergn.francecentral-01.azurewebsites.net/api/docs/](https://xbrain-backend-chbfe7hscpbqergn.francecentral-01.azurewebsites.net/api/docs/)

## Features
- **JWT Authentication** (Login, Register).
- **Email Verification** via 6-digit OTP codes.
- **Secure Password Reset** (3-step OTP flow).
- **User Profiles** with specialization selection.
- **Points/Wallet System** for gamification.
- **Interactive Swagger Documentation** powered by `drf-spectacular`.
- Configured for **Azure App Service** deployments.

## Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/sameh625/xBrain-backend.git
   cd xBrain-backend
   ```

2. **Create a virtual environment and activate it**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Seed initial Specializations data**
   ```bash
   python manage.py seed_specializations
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

*(Local server will run on `http://127.0.0.0:8000`)*

## Testing
To run the automated test suite (59 passing tests):
```bash
python manage.py test api
```

## Deployment
This project is configured for seamless deployment to **Azure App Service (Linux Web App)**.
* **Database:** Azure Database for PostgreSQL Flexible Server.
* **Static Files:** Served via `whitenoise`.
* **Server:** Gunicorn using `startup.sh`.
