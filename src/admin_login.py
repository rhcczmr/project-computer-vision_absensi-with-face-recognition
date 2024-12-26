import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
import os
import json
from datetime import datetime, timedelta

class AdminLogin:
    def __init__(self, db):
        self.db = db
        self.window = tk.Toplevel()
        self.window.title("Admin Login")
        self.window.geometry("300x200")
        self.window.grab_set()  # Make window modal
        
        # Center window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Set window to be always on top
        self.window.attributes('-topmost', True)
        
        # Create login frame
        self.create_login_frame()
        
    def create_login_frame(self):
        """Create login interface"""
        frame = ttk.Frame(self.window, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Username
        ttk.Label(frame, text="Username:").grid(row=0, column=0, pady=5, sticky=tk.W)
        self.username = ttk.Entry(frame, width=30)
        self.username.grid(row=1, column=0, pady=5)
        self.username.focus()  # Set focus to username field
        
        # Password
        ttk.Label(frame, text="Password:").grid(row=2, column=0, pady=5, sticky=tk.W)
        self.password = ttk.Entry(frame, width=30, show="*")
        self.password.grid(row=3, column=0, pady=5)
        
        # Login button
        ttk.Button(
            frame,
            text="Login",
            command=self.login
        ).grid(row=4, column=0, pady=20)
        
        # Bind Enter key to login
        self.window.bind('<Return>', lambda e: self.login())
        
    def login(self):
        """Verify login credentials"""
        username = self.username.get().strip()
        password = self.password.get().strip()
        
        if not username or not password:
            messagebox.showerror(
                "Error",
                "Username dan password harus diisi!",
                parent=self.window
            )
            return
            
        # Hash password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Check credentials in database
        if self.db.verify_admin_credentials(username, hashed_password):
            # Create session
            self.create_session(username)
            
            # Close login window
            self.window.destroy()
            
            # Open admin panel
            from src.admin import AdminSystem
            AdminSystem(self.db)
        else:
            messagebox.showerror(
                "Error",
                "Username atau password salah!",
                parent=self.window
            )
            
    def create_session(self, username):
        """Create admin session"""
        session = {
            'username': username,
            'login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'expires': (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save session to file
        with open('admin_session.json', 'w') as f:
            json.dump(session, f)

def verify_admin_session():
    """Verify if admin session is valid"""
    try:
        # Check if session file exists
        if not os.path.exists('admin_session.json'):
            return False
            
        # Read session
        with open('admin_session.json', 'r') as f:
            session = json.load(f)
            
        # Check expiration
        expires = datetime.strptime(session['expires'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expires:
            os.remove('admin_session.json')
            return False
            
        return True
        
    except Exception as e:
        print(f"Error verifying session: {str(e)}")
        return False