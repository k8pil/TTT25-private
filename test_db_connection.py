import os
import sqlite3


def test_sqlite_connection():
    print("Testing direct SQLite connection...")

    # Calculate instance path relative to project root (2 levels up from CWD)
    cwd = os.getcwd()
    project_root = os.path.dirname(os.path.dirname(cwd))
    instance_path = os.path.join(project_root, 'instance')

    # Ensure instance directory exists
    # os.makedirs(instance_path, exist_ok=True) # Let's assume it exists from previous steps or setup

    # Define the path to the database
    db_path = os.path.join(instance_path, 'eye.sqlite')

    try:
        # Try to connect with read/write permissions
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute a simple query
        cursor.execute("SELECT COUNT(*) FROM eye_metrics")
        count = cursor.fetchone()[0]

        print(f"Successfully connected to {db_path}")
        print(f"Found {count} records in eye_metrics table")

        # Try to add a test record
        cursor.execute("""
        INSERT INTO eye_metrics 
        (user_id, session_id, hand_detection_count, looking_away_duration) 
        VALUES (999, 'test_connection', 1, 2.5)
        """)

        conn.commit()
        print("Successfully added a test record")

        # Verify the record was added
        cursor.execute("SELECT * FROM eye_metrics WHERE user_id = 999")
        record = cursor.fetchone()
        print(f"Retrieved test record: ID = {record[0]}")

        # Close the connection
        conn.close()
        return True

    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return False


def fix_permissions():
    print("Attempting to fix permissions...")

    # Calculate instance path relative to project root (2 levels up from CWD)
    cwd = os.getcwd()
    project_root = os.path.dirname(os.path.dirname(cwd))
    instance_path = os.path.join(project_root, 'instance')

    try:
        # Make sure instance directory exists and has write permissions
        os.makedirs(instance_path, exist_ok=True)

        # Set write permissions on instance directory
        os.chmod(instance_path, 0o777)  # Full permissions for testing

        # Set write permissions on all files in instance
        for file in os.listdir(instance_path):
            file_path = os.path.join(instance_path, file)
            os.chmod(file_path, 0o777)  # Full permissions for testing
            print(f"Set permissions on {file_path}")

        print("Permissions updated")
        return True

    except Exception as e:
        print(f"Error fixing permissions: {str(e)}")
        return False


# Run the tests
print("Current working directory:", os.getcwd())

success = test_sqlite_connection()
if not success:
    print("Trying to fix permissions and retry...")
    fix_permissions()
    test_sqlite_connection()
