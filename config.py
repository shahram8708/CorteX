import os
from datetime import timedelta

from dotenv import load_dotenv


# Load environment variables from a local .env file so Flask picks them up when running locally.
load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///multimosaic.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = _as_bool(os.environ.get('MAIL_USE_TLS', True), default=True)
    MAIL_USE_SSL = _as_bool(os.environ.get('MAIL_USE_SSL', False), default=False)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # Fallback order ensures Flask-Mail always has a sender
    MAIL_DEFAULT_SENDER = (
        os.environ.get('MAIL_DEFAULT_SENDER')
        or os.environ.get('MAIL_USERNAME')
        or 'multimosaic.help@gmail.com'
    )

    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'cortex')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'cortex@6708')

    REMEMBER_COOKIE_DURATION = timedelta(days=int(os.environ.get('REMEMBER_COOKIE_DURATION_DAYS', 365)))
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get('PERMANENT_SESSION_LIFETIME_DAYS', 365)))

    OPENCAGE_API_KEY = os.environ.get('OPENCAGE_API_KEY')
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
    RAZORPAY_ACCOUNT_NUMBER = os.environ.get('RAZORPAY_ACCOUNT_NUMBER')