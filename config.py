"""
Configuration for Interview Advisor application
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get(
        'FLASK_SECRET_KEY', 'interview-advisor-secret-key')
    SESSION_TYPE = 'filesystem'
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Return the appropriate configuration object based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
