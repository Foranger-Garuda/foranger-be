import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production")

    # Database - Supabase PostgreSQL
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:your_password@db.bzrntelwhrhrkyvtqysh.supabase.co:5432/postgres")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # Handle the postgres:// vs postgresql:// issue for SQLAlchemy
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Flask settings
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ["true", "1", "yes"]
    
    # Optional: Add SSL requirement for production
    SQLALCHEMY_ENGINE_OPTIONS.update({
        'connect_args': {
            'sslmode': 'require'
        }
    }) if not DEBUG else None