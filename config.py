import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    """Base config, uses staging database server."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE = 60

    USER_ENABLE_EMAIL = False
    USER_ENABLE_REGISTER = False
    USER_ENABLE_FORGOT_PASSWORD = False

    CSRF_ENABLED = True

    MAIL_SERVER = os.getenv('MAIL_SERVER', '127.0.0.1')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'no-reply@prioritybiz.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 1025))
    MAIL_USE_SSL = bool(int(os.getenv('MAIL_USE_SSL', False)))

    EASYPOST_API_KEY = os.getenv("EASYPOST_API_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SECRET_KEY = os.getenv("SECRET_KEY")

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')

    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')


class ProductionConfig(Config):
    """Uses production settings."""
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    DEBUG = True
    DATABASE_URI = 'sqlite:///:memory:'
