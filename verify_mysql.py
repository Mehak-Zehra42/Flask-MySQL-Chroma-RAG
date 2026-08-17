import sys
import os
from dotenv import load_dotenv

print("1. Loading dotenv...")
load_dotenv()

print("2. Importing mysql.connector...")
try:
    import mysql.connector
    print("   Successfully imported mysql.connector")
except Exception as e:
    print(f"   Failed to import: {e}")
    sys.exit(1)

host = os.getenv('MYSQL_HOST', '127.0.0.1')
user = os.getenv('MYSQL_USER', 'root')
password = os.getenv('MYSQL_PASSWORD', '')
database = os.getenv('MYSQL_DATABASE', 'cog_rag_db')

print(f"3. Parameters: host={host}, user={user}, password={password}, db={database}")

print("4. Attempting connection...")
try:
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        use_pure=True
    )
    print("5. [SUCCESS] Connected successfully!")
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    print(f"   MySQL Version: {cursor.fetchone()[0]}")
    cursor.close()
    conn.close()
except BaseException as e:
    print(f"6. [ERROR] Connection failed: {type(e).__name__} - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("7. Script finished successfully.")
