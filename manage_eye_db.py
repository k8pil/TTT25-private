import os
import sqlite3
import sys
from datetime import datetime

# Define the path to the eye.sqlite database
instance_path = os.path.join(os.getcwd(), 'instance')
db_path = os.path.join(instance_path, 'eye.sqlite')

def check_db_exists():
    """Check if the database exists"""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False
    return True

def view_data():
    """View all records in the eye_metrics table"""
    if not check_db_exists():
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get column names first
    cursor.execute("PRAGMA table_info(eye_metrics)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Now get the data
    cursor.execute("SELECT * FROM eye_metrics ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    print(f"Database: {db_path}")
    print(f"Found {len(rows)} records in eye_metrics table.\n")
    
    if len(rows) == 0:
        print("No records found.")
    else:
        # Print header
        print("Records in eye_metrics table:")
        print("-" * 80)
        
        # Print each record
        for i, row in enumerate(rows):
            print(f"Record #{i+1}:")
            for j, value in enumerate(row):
                column_name = columns[j] if j < len(columns) else f"Column {j}"
                
                if column_name in ['hand_detection_duration', 'looking_away_duration', 'bad_posture_duration']:
                    print(f"  {column_name}: {value:.2f}s")
                elif column_name == 'is_auto_save':
                    print(f"  {column_name}: {bool(value)}")
                else:
                    print(f"  {column_name}: {value}")
            print("-" * 40)
    
    conn.close()

def reset_data():
    """Delete all records from the eye_metrics table"""
    if not check_db_exists():
        return
    
    confirm = input("Are you sure you want to delete ALL records from the eye_metrics table? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM eye_metrics")
    conn.commit()
    
    print(f"All records deleted from eye_metrics table.")
    conn.close()

def add_test_data():
    """Add test records to the eye_metrics table"""
    if not check_db_exists():
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add 3 test records
    for i in range(3):
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
            1,  # user_id
            f"test_session_{i+1}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            i + 5,  # hand_detection_count
            (i + 1) * 3.5,  # hand_detection_duration
            i + 2,  # loss_eye_contact_count
            (i + 1) * 2.2,  # looking_away_duration
            i + 1,  # bad_posture_count
            (i + 1) * 1.7,  # bad_posture_duration
            i % 2 == 0  # is_auto_save
        ))
    
    conn.commit()
    print(f"Added 3 test records to eye_metrics table.")
    conn.close()

def recreate_db():
    """Recreate the database from scratch"""
    if os.path.exists(db_path):
        confirm = input(f"Database {db_path} already exists. Recreate it? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
    
    # Ensure instance directory exists
    os.makedirs(instance_path, exist_ok=True)
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
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
        is_auto_save BOOLEAN DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Database created at: {db_path}")
    print("Eye metrics table created.")

def show_help():
    """Show usage information"""
    print(f"Eye Metrics Database Management Tool")
    print(f"Database: {db_path}")
    print("\nUsage: python manage_eye_db.py [command]")
    print("\nCommands:")
    print("  view    - View all records in the database")
    print("  reset   - Delete all records from the database")
    print("  test    - Add test records to the database")
    print("  recreate - Recreate the database from scratch")
    print("  help    - Show this help message")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "view":
        view_data()
    elif command == "reset":
        reset_data()
    elif command == "test":
        add_test_data()
    elif command == "recreate":
        recreate_db()
    elif command == "help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help() 