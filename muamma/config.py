import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Europe/Istanbul")


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"