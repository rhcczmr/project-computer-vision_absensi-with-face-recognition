import sqlite3
import os
import logging
import hashlib
from datetime import datetime

class Database:
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            filename='database.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        print("Initializing database...")
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        try:
            db_path = os.path.join('data', 'attendance.db')
            db_exists = os.path.exists(db_path)
            print(f"Database exists: {db_exists}")
            
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self._cursor = self.conn.cursor()
            
            # Only create tables if database doesn't exist
            if not db_exists:
                print("New database, creating tables...")
                self.create_tables()
            else:
                print("Using existing database...")
                # Check if admin_users table exists, create if not
                self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'")
                if not self._cursor.fetchone():
                    self._create_admin_table()
            
            print("Database initialization complete")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            raise

    def _create_admin_table(self):
        """Create admin_users table and default admin account"""
        try:
            print("Creating admin_users table...")
            self._cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create default admin account
            default_password = hashlib.sha256('admin123'.encode()).hexdigest()
            self._cursor.execute("""
                INSERT INTO admin_users (username, password)
                VALUES (?, ?)
            """, ('admin', default_password))
            
            self.conn.commit()
            print("Admin table and default account created")
        except Exception as e:
            print(f"Error creating admin table: {str(e)}")
            raise

    def cursor(self):
        """Get database cursor"""
        return self._cursor

    def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Create users table
            print("Creating users table...")
            self._cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    photo_path TEXT NOT NULL,
                    home_location TEXT,
                    office_location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create attendance table
            print("Creating attendance table...")
            self._cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date DATE DEFAULT CURRENT_DATE,
                    time_in TIME DEFAULT CURRENT_TIME,
                    time_out TIME,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    location TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Create admin table and account
            self._create_admin_table()
            
            self.conn.commit()
            print("All tables created successfully")
            
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
            raise

    def add_user(self, name, photo_path, home_location, office_location):
        """Add new user"""
        try:
            print(f"Adding new user: {name}")
            self._cursor.execute("""
                INSERT INTO users (name, photo_path, home_location, office_location)
                VALUES (?, ?, ?, ?)
            """, (name, photo_path, home_location, office_location))
            self.conn.commit()
            print("User added successfully")
            return True
        except Exception as e:
            print(f"Error adding user: {str(e)}")
            self.conn.rollback()
            return False

    def get_users(self):
        """Get all users"""
        try:
            print("Fetching all users")
            self._cursor.execute("SELECT * FROM users")
            users = self._cursor.fetchall()
            print(f"Found {len(users)} users")
            return users
        except Exception as e:
            print(f"Error getting users: {str(e)}")
            return []

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            print(f"Fetching user with ID: {user_id}")
            self._cursor.execute("""
                SELECT * FROM users WHERE id = ?
            """, (user_id,))
            user = self._cursor.fetchone()
            if user:
                print(f"Found user: {user['name']}")
            else:
                print("User not found")
            return user
        except Exception as e:
            print(f"Error getting user by ID: {str(e)}")
            return None

    def update_user(self, user_id, name, photo_path=None, home_location=None, office_location=None):
        """Update user data"""
        try:
            print(f"Updating user ID {user_id}")
            if photo_path:
                self._cursor.execute("""
                    UPDATE users 
                    SET name = ?, photo_path = ?, home_location = ?, office_location = ?
                    WHERE id = ?
                """, (name, photo_path, home_location, office_location, user_id))
            else:
                self._cursor.execute("""
                    UPDATE users 
                    SET name = ?, home_location = ?, office_location = ?
                    WHERE id = ?
                """, (name, home_location, office_location, user_id))
            
            self.conn.commit()
            print(f"User {user_id} updated successfully")
            return True
            
        except Exception as e:
            print(f"Error updating user: {str(e)}")
            self.conn.rollback()
            return False

    def delete_user(self, user_id):
        """Delete user and their attendance records"""
        try:
            print(f"Deleting user ID {user_id} and their attendance records")
            
            # Delete attendance records first (due to foreign key constraint)
            self._cursor.execute("""
                DELETE FROM attendance WHERE user_id = ?
            """, (user_id,))
            
            # Delete user
            self._cursor.execute("""
                DELETE FROM users WHERE id = ?
            """, (user_id,))
            
            self.conn.commit()
            print(f"User {user_id} and their records deleted successfully")
            return True
            
        except Exception as e:
            print(f"Error deleting user: {str(e)}")
            self.conn.rollback()
            return False

    def record_attendance(self, user_id, mode, status, location=None):
        """Record attendance"""
        try:
            print(f"Recording attendance for user_id: {user_id}")
            self._cursor.execute("""
                INSERT INTO attendance (user_id, mode, status, location)
                VALUES (?, ?, ?, ?)
            """, (user_id, mode, status, location))
            self.conn.commit()
            print("Attendance recorded successfully")
            return True
        except Exception as e:
            print(f"Error recording attendance: {str(e)}")
            self.conn.rollback()
            return False

    def get_attendance(self):
        """Get all attendance records"""
        try:
            print("Fetching all attendance records")
            self._cursor.execute("""
                SELECT a.*, u.name 
                FROM attendance a 
                JOIN users u ON a.user_id = u.id
                ORDER BY a.date DESC, a.time_in DESC
            """)
            records = self._cursor.fetchall()
            print(f"Found {len(records)} attendance records")
            return records
        except Exception as e:
            print(f"Error getting attendance: {str(e)}")
            return []

    def verify_admin_credentials(self, username, password):
        """Verify admin login credentials"""
        try:
            print(f"Verifying credentials for username: {username}")
            self._cursor.execute("""
                SELECT id FROM admin_users 
                WHERE username = ? AND password = ?
            """, (username, password))
            result = self._cursor.fetchone() is not None
            print(f"Credentials verification result: {result}")
            return result
        except Exception as e:
            print(f"Error verifying admin credentials: {str(e)}")
            return False

    def __del__(self):
        """Close database connection"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
                print("Database connection closed")
        except Exception as e:
            print(f"Error closing database: {str(e)}")