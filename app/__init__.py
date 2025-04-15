"""
Interview Advisor Web Application - App Factory
"""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_app(test_config=None):
    """Create and configure the Flask application"""

    # Create app
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # Configure app
    app.secret_key = os.environ.get(
        'FLASK_SECRET_KEY', 'interview-advisor-secret-key')
    app.config['SESSION_TYPE'] = 'filesystem'

    # Enable CORS
    CORS(app, supports_credentials=True)

    # Create required directories
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)

    # Register blueprints
    from app.routes.main_routes import main_bp
    from app.routes.interview_routes import interview_bp
    from app.routes.api_routes import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(interview_bp, url_prefix='/interview')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
