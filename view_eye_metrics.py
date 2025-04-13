import os
import sqlite3
from datetime import datetime

# Define the path to the eye.sqlite database
instance_path = os.path.join(os.getcwd(), 'instance')
db_path = os.path.join(instance_path, 'eye.sqlite')

# Verify the database exists
if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # This enables column access by name
cursor = conn.cursor()

# Get all records from the eye_metrics table
cursor.execute("SELECT * FROM eye_metrics ORDER BY timestamp DESC")
rows = cursor.fetchall()

print(f"Database: {db_path}")
print(f"Found {len(rows)} records in eye_metrics table.\n")

# Display each record with formatted output
for i, row in enumerate(rows):
    print(f"Record #{i+1}:")
    print(f"  ID: {row['id']}")
    print(f"  User ID: {row['user_id']}")
    print(f"  Session ID: {row['session_id']}")
    print(f"  Timestamp: {row['timestamp']}")
    print(f"  Hand Detection Count: {row['hand_detection_count']}")
    print(f"  Hand Detection Duration: {row['hand_detection_duration']:.2f}s")
    print(f"  Loss Eye Contact Count: {row['loss_eye_contact_count']}")
    print(f"  Looking Away Duration: {row['looking_away_duration']:.2f}s")
    print(f"  Bad Posture Count: {row['bad_posture_count']}")
    print(f"  Bad Posture Duration: {row['bad_posture_duration']:.2f}s")
    print(f"  Is Auto Save: {bool(row['is_auto_save'])}")
    print()

# Close the connection
conn.close() 