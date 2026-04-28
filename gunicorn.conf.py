# Gunicorn configuration file
# This file is auto-detected by gunicorn regardless of how it's started

timeout = 180
# Multi-worker concurrency. Safe because shared state (OTPs, login lockout
# counters, password reset tokens, pending registrations) lives in Redis,
# not LocMemCache.
workers = 2
threads = 2
bind = "0.0.0.0:10000"
