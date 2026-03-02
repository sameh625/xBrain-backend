python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_specializations 2>/dev/null || true

gunicorn xBrain.wsgi --bind=0.0.0.0:8000 --workers=1 --timeout=120
