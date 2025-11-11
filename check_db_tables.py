"""Check what tables exist in the database."""

import sqlite3
import sys

db_path = "/workspace/bento/app.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()

    print(f"📊 Tables in {db_path}:\n")
    if tables:
        for table in tables:
            print(f"  ✅ {table[0]}")

            # Get column info
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            print(f"     Columns: {len(columns)}")
            for col in columns[:5]:  # Show first 5 columns
                print(f"       - {col[1]} ({col[2]})")
            if len(columns) > 5:
                print(f"       ... and {len(columns) - 5} more columns")
            print()
    else:
        print("  ❌ No tables found!")

    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
