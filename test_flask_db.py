import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text  # Import the text function
from models import EyeMetrics # Import the EyeMetrics model

# Get the current working directory (where the script is being run from)
cwd = os.getcwd()
# Go up two levels to the intended project root (based on observed CWD)
project_root = os.path.dirname(os.path.dirname(cwd))
# Define the instance path relative to the actual project root
instance_path = os.path.join(project_root, 'instance')

# Create a simple app
# Use the correct instance_path for Flask
app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)
# app.instance_path = instance_path # Setting instance_path in constructor is preferred

# Ensure instance directory exists
os.makedirs(instance_path, exist_ok=True) # Ensure the target instance dir exists

# Define absolute path for the database within the instance folder
eye_db_path = os.path.join(app.instance_path, 'eye.sqlite')

# Configure the database with absolute paths
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{eye_db_path}'
# Add the named bind for the eye_metrics database
app.config['SQLALCHEMY_BINDS'] = {
    'eye_metrics': f'sqlite:///{eye_db_path}'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define a simple model


class TestModel(db.Model):
    __tablename__ = 'test_model'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))


# Test database operations
with app.app_context():
    try:
        # Create tables for all binds (should happen automatically)
        db.create_all()

        print(f"Attempted table creation in default: {app.config['SQLALCHEMY_DATABASE_URI']}")
        if 'eye_metrics' in app.config['SQLALCHEMY_BINDS']:
             print(f"Attempted table creation in eye_metrics bind: {app.config['SQLALCHEMY_BINDS']['eye_metrics']}")


        # Add a test record to the default database
        test = TestModel(name="SQLAlchemy Test")
        db.session.add(test)
        db.session.commit()
        print("Added test record to default database")

        # Query to verify the default database record
        result = TestModel.query.filter_by(name="SQLAlchemy Test").first()
        print(f"Retrieved test record from default: ID = {result.id}, Name = {result.name}")

        # Now try to query the eye_metrics table using the correct bind
        print("\nTrying to access eye_metrics table via named bind:")
        # Get the engine for the specific bind
        engine = db.get_engine(bind='eye_metrics') 
        with engine.connect() as connection:
            cursor = connection.execute(text("SELECT COUNT(*) FROM eye_metrics"))
            count = cursor.scalar()
            print(f"Found {count} records in eye_metrics table")

        print("\nDatabase connection test successful!")
    except Exception as e:
        print(f"Error with SQLAlchemy database operations: {str(e)}")
