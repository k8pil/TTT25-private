import os
import sqlite3

# Define the path to the eye.sqlite database
instance_path = os.path.join(os.getcwd(), 'instance')
db_path = os.path.join(instance_path, 'eye.sqlite')

print(f"Checking database at: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"Tables in database:")
for table in tables:
    print(f"  - {table[0]}")
    
    # Show table schema
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print(f"    Columns:")
    for col in columns:
        print(f"      {col[1]} ({col[2]})")
    
    # Count records
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    count = cursor.fetchone()[0]
    print(f"    Record count: {count}")
    
    # Show sample data if available
    if count > 0:
        cursor.execute(f"SELECT * FROM {table[0]} LIMIT 1")
        sample = cursor.fetchone()
        print(f"    Sample data: {sample}")
    
    print()

conn.close() 