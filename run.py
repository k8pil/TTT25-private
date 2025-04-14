"""
Entry point for the Interview Advisor application
"""

from app import create_app
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app factory

# Create application
app = create_app()

if __name__ == '__main__':
    # Create required directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('cache', exist_ok=True)

    # Get host and port
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'

    # Run the application
    app.run(host=host, port=port, debug=debug)
