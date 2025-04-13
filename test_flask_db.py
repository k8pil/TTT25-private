import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create a simple app
app = Flask(__name__)

# Ensure instance directory exists
instance_path = os.path.join(os.getcwd(), 'instance')
os.makedirs(instance_path, exist_ok=True)

# Define absolute paths for databases
eye_db_path = os.path.join(instance_path, 'eye.sqlite')

# Configure the database with absolute paths
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{eye_db_path}'
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
        # Create test_model table if it doesn't exist
        db.create_all()
        print(f"Successfully created tables in {eye_db_path}")
        
        # Add a test record
        test = TestModel(name="SQLAlchemy Test")
        db.session.add(test)
        db.session.commit()
        print("Added test record to database")
        
        # Query to verify
        result = TestModel.query.filter_by(name="SQLAlchemy Test").first()
        print(f"Retrieved test record: ID = {result.id}, Name = {result.name}")
        
        # Now try to query the eye_metrics table
        print("\nTrying to access eye_metrics table:")
        cursor = db.session.execute("SELECT COUNT(*) FROM eye_metrics")
        count = cursor.scalar()
        print(f"Found {count} records in eye_metrics table")
        
        print("\nDatabase connection test successful!")
    except Exception as e:
        print(f"Error with SQLAlchemy database operations: {str(e)}") 