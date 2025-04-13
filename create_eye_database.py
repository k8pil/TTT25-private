import os
import sqlite3
from datetime import datetime

# Define the path to the instance directory and database file
instance_path = os.path.join(os.getcwd(), 'instance')
db_path = os.path.join(instance_path, 'eye.sqlite')

# Create the instance directory if it doesn't exist
os.makedirs(instance_path, exist_ok=True)

# Create the database and the eye_metrics table
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create the eye_metrics table
cursor.execute('''
CREATE TABLE IF NOT EXISTS eye_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    session_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    hand_detection_count INTEGER DEFAULT 0,
    hand_detection_duration REAL DEFAULT 0.0,
    loss_eye_contact_count INTEGER DEFAULT 0,
    looking_away_duration REAL DEFAULT 0.0,
    bad_posture_count INTEGER DEFAULT 0,
    bad_posture_duration REAL DEFAULT 0.0,
    is_auto_save BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user(id)
)
''')

# Insert a test record to verify it's working
cursor.execute('''
INSERT INTO eye_metrics (
    user_id, 
    session_id, 
    timestamp,
    hand_detection_count,
    hand_detection_duration,
    loss_eye_contact_count,
    looking_away_duration,
    bad_posture_count,
    bad_posture_duration,
    is_auto_save
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    1,  # user_id (change if needed)
    f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    5,  # hand_detection_count
    10.5,  # hand_detection_duration
    3,  # loss_eye_contact_count
    8.2,  # looking_away_duration
    2,  # bad_posture_count
    6.7,  # bad_posture_duration
    0  # is_auto_save (0 = False)
))

# Commit and close
conn.commit()
conn.close()

print(f"Database created at: {db_path}")
print("Eye metrics table created with test data.")
print(f"Directory contents: {os.listdir(instance_path)}") 