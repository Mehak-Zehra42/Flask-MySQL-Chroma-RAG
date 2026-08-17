import os
import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

# MySQL configuration from environment variables
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "cog_rag_db")

def get_mysql_connection(include_db=True):
    """
    Establishes and returns a connection to the MySQL server.
    """
    config = {
        'host': MYSQL_HOST,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'use_pure': True
    }
    if include_db:
        config['database'] = MYSQL_DATABASE
        
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"\n[DATABASE ERROR] Failed to connect to MySQL: {err}")
        print("Please ensure your MySQL server (e.g. XAMPP / WampServer) is running on localhost.\n")
        raise err

def init_db():
    """
    Initializes the MySQL database:
    1. Connects to server and creates the database if it doesn't exist.
    2. Connects to database and creates the required tables ('users', 'chat_messages').
    3. Seeds exactly two pre-configured Admin accounts.
    """
    # Step 1: Create Database if not exists
    try:
        conn = get_mysql_connection(include_db=False)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[INIT DATABASE ERROR] Could not create database: {e}")
        return False

    # Step 2: Connect to database and build tables
    try:
        conn = get_mysql_connection(include_db=True)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'user'
            ) ENGINE=InnoDB;
        """)
        
        # Create chat_messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                sender VARCHAR(10) NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)
        
        conn.commit()
        
        # Step 3: Seed exactly 2 Admin accounts
        seed_admins(cursor, conn)
        
        cursor.close()
        conn.close()
        print("[SUCCESS] MySQL database initialized and seeded successfully.")
        return True
    except Exception as e:
        print(f"[INIT DATABASE ERROR] Error creating tables or seeding admins: {e}")
        return False

def seed_admins(cursor, conn):
    """
    Inserts exactly 2 preconfigured Admin accounts into the users table.
    """
    # 2 Predefined admin accounts
    admins = [
        ("admin1@company.com", "admin123"),
        ("admin2@company.com", "admin456")
    ]
    
    for email, password in admins:
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        
        if not result:
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'admin')",
                (email, password_hash)
            )
            print(f"[SEED] Pre-seeded admin account: {email}")
            
    conn.commit()

def register_user(email, password):
    """
    Registers a new regular user account. Ensures only 'user' role is allowed.
    Returns (success_boolean, message_string).
    """
    # Check if admin email is being used to prevent spoofing
    if "admin" in email.lower():
        # Prevent manual registration of admin profiles to satisfy
        # "admin bas 2 hi honay chaiy"
        return False, "Cannot register administrative accounts."

    try:
        conn = get_mysql_connection(include_db=True)
        cursor = conn.cursor()
        
        # Check duplicate
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False, "Email address is already registered."
            
        # Hash password and insert
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'user')",
            (email, password_hash)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        return True, "User registered successfully."
    except Exception as e:
        return False, f"Database error: {str(e)}"

def verify_user(email, password):
    """
    Verifies user login credentials.
    Returns user details dictionary on success, None otherwise.
    """
    try:
        conn = get_mysql_connection(include_db=True)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            return {
                "id": user['id'],
                "email": user['email'],
                "role": user['role']
            }
        return None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return None

def save_chat_message(user_id, sender, message):
    """
    Persists a single chat message to the MySQL database.
    """
    try:
        conn = get_mysql_connection(include_db=True)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO chat_messages (user_id, sender, message) VALUES (%s, %s, %s)",
            (user_id, sender, message)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving chat log: {e}")
        return False

def get_chat_history(user_id):
    """
    Fetches all chat messages for a specific user.
    """
    try:
        conn = get_mysql_connection(include_db=True)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT sender, message, timestamp FROM chat_messages WHERE user_id = %s ORDER BY timestamp ASC",
            (user_id,)
        )
        history = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Serialize datetime timestamp to string for JSON parsing
        for msg in history:
            msg['timestamp'] = msg['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            
        return history
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def clear_chat_history(user_id):
    """
    Clears all chat logs for a specific user.
    """
    try:
        conn = get_mysql_connection(include_db=True)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error clearing chat history: {e}")
        return False

def get_last_n_messages(user_id, n=5):
    """
    Retrieves the last n messages (in order of oldest to newest) for memory context.
    """
    try:
        conn = get_mysql_connection(include_db=True)
        # We need dictionary=True to easily read columns
        cursor = conn.cursor(dictionary=True)
        
        # Get last n messages
        cursor.execute(
            "SELECT sender, message FROM chat_messages WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
            (user_id, n)
        )
        # Note: Results are in DESC order (newest first). We need to reverse them before returning.
        history = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        history.reverse()  # Reverse to ASC order (oldest first)
        return [(msg['sender'], msg['message']) for msg in history]
    except Exception as e:
        print(f"Error getting last n messages: {e}")
        return []
