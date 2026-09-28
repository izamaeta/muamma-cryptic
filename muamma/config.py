import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Europe/Istanbul")


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"