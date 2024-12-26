import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import face_recognition
import numpy as np
from datetime import datetime
import os
from PIL import Image, ImageTk
import sys
import logging

# Setup logging
logging.basicConfig(
    filename='attendance.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add the project root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Now import from src
from src.database import Database
from src.anti_spoofing import AntiSpoofingDetector
from src.geolocation import calculate_distance, get_current_location

class AttendanceSystem:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Face Recognition Attendance System")
        self.window.geometry("1200x800")
        
        # Set window icon if available
        try:
            icon_path = os.path.join("assets", "icon.ico")
            if os.path.exists(icon_path):
                self.window.iconbitmap(icon_path)
        except:
            pass
            
        # Configure window scaling
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        
        # Set custom styles
        self.setup_styles()
        
        # Initialize database
        try:
            print("Initializing database...")
            self.db = Database()
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            messagebox.showerror("Error", "Failed to initialize database")
            return
            
        # Initialize anti-spoofing detector
        try:
            print("Initializing anti-spoofing detector...")
            self.spoof_detector = AntiSpoofingDetector()
        except Exception as e:
            print(f"Error initializing anti-spoofing: {str(e)}")
            messagebox.showerror("Error", "Failed to initialize anti-spoofing")
            return
        
        # Initialize face recognition variables
        self.known_face_encodings = []
        self.known_face_names = []
        self.current_user_id = None
        
        # Performance optimization variables
        self.frame_skip = 0
        self.frame_skip_threshold = 2
        self.location_check_counter = 0
        self.location_update_frequency = 30
        self.last_frame = None
        self.last_processed_result = None
        
        # Create GUI elements
        self.create_widgets()

        # Initialize camera with optimized settings
        try:
            print("Initializing camera...")
            self.camera = cv2.VideoCapture(1)  # Try index 1 first
            if not self.camera.isOpened():
                print("Camera index 1 failed, trying index 0...")
                self.camera = cv2.VideoCapture(0)  # If fails, try index 0
                
            if not self.camera.isOpened():
                raise Exception("Could not open camera on any index")
                
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            print("Camera initialized successfully")
            
        except Exception as e:
            print(f"Error starting camera: {str(e)}")
            messagebox.showerror("Error", "Failed to start camera. Please check your camera connection.")
            return
        
        # Load known faces
        self.show_loading("Loading faces...")
        self.load_known_faces()
        self.debug_user_data()
        self.hide_loading()
        
        # Initialize camera with optimized settings
        try:
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 15)
            
            if not self.camera.isOpened():
                raise Exception("Could not open camera")
                
        except Exception as e:
            print(f"Error starting camera: {str(e)}")
            messagebox.showerror("Error", "Failed to start camera")
            return
            
        self.update_camera()
        self.window.mainloop()

    def setup_styles(self):
        """Setup custom ttk styles"""
        style = ttk.Style()
        
        # Configure main styles
        style.configure(
            "Camera.TFrame",
            background="#2c3e50",
            padding=10
        )
        style.configure(
            "Info.TFrame",
            background="#ecf0f1",
            padding=10
        )
        style.configure(
            "Button.TButton",
            padding=8,
            font=('Helvetica', 10)
        )
        style.configure(
            "Record.TButton",
            padding=8,
            font=('Helvetica', 10, 'bold')
        )
        style.configure(
            "Status.TLabel",
            font=('Helvetica', 12),
            background="#ecf0f1",
            padding=5
        )
        style.configure(
            "Title.TLabel",
            font=('Helvetica', 16, 'bold'),
            background="#ecf0f1",
            padding=10
        )
        style.configure(
            "Loading.TFrame",
            background="white",
            relief="solid",
            borderwidth=1
        )

    def create_widgets(self):
        """Create GUI elements with improved styling"""
        # Main container with padding
        main_container = ttk.Frame(self.window, padding="10")
        main_container.pack(fill='both', expand=True)
        
        # Camera frame with border
        self.camera_frame = ttk.Frame(
            main_container,
            style="Camera.TFrame",
            relief="solid",
            borderwidth=1
        )
        self.camera_frame.pack(pady=10, fill='both', expand=True)
        
        # Camera display with border
        self.camera_label = ttk.Label(
            self.camera_frame,
            borderwidth=2,
            relief="solid"
        )
        self.camera_label.pack(padx=10, pady=10, expand=True)
        
        # Info frame with better spacing
        self.info_frame = ttk.Frame(
            main_container,
            style="Info.TFrame"
        )
        self.info_frame.pack(pady=10, fill='x')
        
        # Status labels with improved styling
        self.info_label = ttk.Label(
            self.info_frame,
            text="Waiting for face detection...",
            style="Status.TLabel"
        )
        self.info_label.pack(pady=5)
        
        self.spoof_label = ttk.Label(
            self.info_frame,
            text="Liveness Check: Waiting...",
            style="Status.TLabel"
        )
        self.spoof_label.pack(pady=5)
        
        self.location_label = ttk.Label(
            self.info_frame,
            text="Location: Checking...",
            style="Status.TLabel"
        )
        self.location_label.pack(pady=5)
        
        # Button frame with better spacing
        self.button_frame = ttk.Frame(main_container)
        self.button_frame.pack(pady=10)
        
        # Styled buttons
        self.record_button = ttk.Button(
            self.button_frame,
            text="Record Attendance",
            command=self.record_attendance,
            style="Record.TButton",
            state='disabled',
            width=20
        )
        self.record_button.pack(side=tk.LEFT, padx=10)
        
        self.admin_button = ttk.Button(
            self.button_frame,
            text="Admin Panel",
            command=self.open_admin_panel,
            style="Button.TButton",
            width=15
        )
        self.admin_button.pack(side=tk.LEFT, padx=10)
        
        self.reload_button = ttk.Button(
            self.button_frame,
            text="Reload Faces",
            command=self.reload_faces,
            style="Button.TButton",
            width=15
        )
        self.reload_button.pack(side=tk.LEFT, padx=10)

    def show_loading(self, message="Loading..."):
        """Show loading overlay"""
        self.loading_frame = ttk.Frame(
            self.window,
            style="Loading.TFrame"
        )
        self.loading_frame.place(
            relx=0.5,
            rely=0.5,
            anchor='center'
        )
        
        self.loading_label = ttk.Label(
            self.loading_frame,
            text=message,
            font=('Helvetica', 12),
            padding=20
        )
        self.loading_label.pack(pady=10)
        
        # Create progress bar
        self.progress = ttk.Progressbar(
            self.loading_frame,
            length=200,
            mode='indeterminate'
        )
        self.progress.pack(pady=5)
        self.progress.start()
        
        self.window.update()

    def hide_loading(self):
        """Hide loading overlay"""
        if hasattr(self, 'loading_frame'):
            self.progress.stop()
            self.loading_frame.destroy()

    def reconnect_camera(self):
        """Try to reconnect camera"""
        try:
            if hasattr(self, 'camera'):
                self.camera.release()
                
            print("Attempting to reconnect camera...")
            self.camera = cv2.VideoCapture(1)  # Try index 1 first
            if not self.camera.isOpened():
                print("Camera index 1 failed, trying index 0...")
                self.camera = cv2.VideoCapture(0)  # If fails, try index 0
                
            if not self.camera.isOpened():
                raise Exception("Could not reconnect camera")
                
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            print("Camera reconnected successfully")
            return True
            
        except Exception as e:
            print(f"Error reconnecting camera: {str(e)}")
            return False        

    def update_display(self, frame):
        """Update display with improved handling"""
        try:
            # Convert to RGB for display
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.configure(image=imgtk)
            
        except Exception as e:
            print(f"Display update error: {str(e)}")
    
    def update_camera(self):
        """Optimized camera update with reconnection"""
        try:
            ret, frame = self.camera.read()
            if not ret:
                print("Camera read failed, attempting reconnect...")
                if self.reconnect_camera():
                    ret, frame = self.camera.read()
                    if not ret:
                        raise Exception("Failed to read frame after reconnect")
                else:
                    self.info_label.configure(text="Camera error - retrying connection...")
                    self.window.after(2000, self.update_camera)  # Try again in 2 seconds
                    return
            
            # Skip frames for better performance
            if self.frame_skip > 0:
                self.frame_skip -= 1
                if self.last_processed_result is not None:
                    is_live, spoof_message, processed_frame = self.last_processed_result
                    self.update_display(processed_frame)
                else:
                    self.update_display(frame)
                self.window.after(10, self.update_camera)
                return
            
            # Reset frame skip counter
            self.frame_skip = self.frame_skip_threshold
            
            # Perform liveness check
            is_live, spoof_message, processed_frame = self.spoof_detector.check_liveness(frame)
            self.last_processed_result = (is_live, spoof_message, processed_frame)
            
            # Update spoof detection status
            self.spoof_label.configure(
                text=f"Liveness Check: {spoof_message}",
                foreground="green" if is_live else "red"
            )
            
            # Update location check less frequently
            self.location_check_counter += 1
            if self.location_check_counter >= self.location_update_frequency:
                self.location_check_counter = 0
                try:
                    current_location = get_current_location()
                    self.location_label.config(text=f"Location: {current_location}")
                except Exception as e:
                    print(f"Location check error: {str(e)}")
                    self.location_label.config(text="Location: Error checking")
            
            # Only process face recognition if liveness check passes
            if is_live:
                face_locations = face_recognition.face_locations(frame)
                if face_locations:
                    face_encodings = face_recognition.face_encodings(frame, face_locations)
                    
                    for (top, right, bottom, left), face_encoding in zip(
                        face_locations, face_encodings
                    ):
                        matches = face_recognition.compare_faces(
                            self.known_face_encodings,
                            face_encoding,
                            tolerance=0.6
                        )
                        
                        name = "Unknown"
                        self.current_user_id = None
                        
                        if True in matches:
                            first_match_index = matches.index(True)
                            name = self.known_face_names[first_match_index]
                            self.current_user_id = first_match_index + 1
                            self.record_button.config(state='normal')
                            
                            # Draw green rectangle for recognized face
                            cv2.rectangle(
                                processed_frame,
                                (left, top),
                                (right, bottom),
                                (0, 255, 0),
                                2
                            )
                        else:
                            # Draw red rectangle for unknown face
                            cv2.rectangle(
                                processed_frame,
                                (left, top),
                                (right, bottom),
                                (0, 0, 255),
                                2
                            )
                            self.record_button.config(state='disabled')
                        
                        # Add name label
                        cv2.putText(
                            processed_frame,
                            name,
                            (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.75,
                            (0, 255, 0),
                            2
                        )
                        
                        # Update info label
                        self.info_label.configure(text=f"Detected: {name}")
                else:
                    self.info_label.configure(text="No face detected")
                    self.record_button.config(state='disabled')
            else:
                self.info_label.configure(text="Warning: Possible spoofing attempt detected!")
                self.record_button.config(state='disabled')
            
            # Update display
            self.update_display(processed_frame)
            
        except Exception as e:
            print(f"Camera update error: {str(e)}")
            self.info_label.configure(text=f"Error: {str(e)}")
        
        # Schedule next update
        self.window.after(10, self.update_camera)

    def record_attendance(self):
        """Record attendance with improved visual feedback"""
        try:
            if not self.current_user_id:
                messagebox.showerror("Error", "No valid face detected")
                return
            
            self.show_loading("Recording attendance...")
            
            # Get and validate location
            try:
                current_location = get_current_location()
                print(f"Current location: {current_location}")
                
                # Get user's registered locations
                user = self.db.get_user_by_id(self.current_user_id)
                if not user:
                    self.hide_loading()
                    messagebox.showerror("Error", "User data not found")
                    return
                
                print("Calculating distances...")
                home_distance = calculate_distance(current_location, user['home_location'])
                office_distance = calculate_distance(current_location, user['office_location'])
                
                print(f"Home distance: {home_distance}m")
                print(f"Office distance: {office_distance}m")
                
                # Determine attendance mode
                mode = "WFH" if home_distance <= office_distance else "WFO"
                print(f"Attendance mode: {mode}")
                
                # Record attendance
                success = self.db.record_attendance(
                    user_id=self.current_user_id,
                    mode=mode,
                    status="Present",
                    location=current_location
                )
                
                self.hide_loading()
                if success:
                    messagebox.showinfo(
                        "Success",
                        f"Attendance recorded for {self.known_face_names[self.current_user_id-1]}"
                    )
                    self.spoof_detector.reset()
                    self.frame_skip = 0
                else:
                    raise Exception("Failed to record attendance")
                    
            except Exception as e:
                print(f"Location validation error: {str(e)}")
                self.hide_loading()
                messagebox.showerror("Error", "Failed to validate location")
                
        except Exception as e:
            print(f"Attendance recording error: {str(e)}")
            self.hide_loading()
            messagebox.showerror("Error", "Failed to record attendance")

    def load_known_faces(self):
        """Load known faces with progress display"""
        try:
            print("\n=== Loading Known Faces ===")
            self.known_face_encodings = []
            self.known_face_names = []
            
            users = self.db.get_users()
            print(f"Found {len(users)} users")
            
            # Update loading message
            if hasattr(self, 'loading_label'):
                self.loading_label.config(text=f"Loading {len(users)} faces...")
            
            for i, user in enumerate(users, 1):
                name = user['name']
                photo_path = os.path.join("data", "user_faces", user['photo_path'])
                print(f"\nProcessing user: {name}")
                
                if hasattr(self, 'loading_label'):
                    self.loading_label.config(text=f"Loading face {i}/{len(users)}: {name}")
                    self.window.update()
                
                if os.path.exists(photo_path):
                    try:
                        # Load and resize image for faster processing
                        face_image = face_recognition.load_image_file(photo_path)
                        if face_image.shape[1] > 640:  # If width > 640px
                            scale = 640 / face_image.shape[1]
                            width = int(face_image.shape[1] * scale)
                            height = int(face_image.shape[0] * scale)
                            face_image = cv2.resize(face_image, (width, height))
                        
                        face_encodings = face_recognition.face_encodings(face_image)
                        if face_encodings:
                            self.known_face_encodings.append(face_encodings[0])
                            self.known_face_names.append(name)
                            print(f"SUCCESS: Face encoded for {name}")
                        else:
                            print(f"ERROR: No face found in image for {name}")
                    except Exception as e:
                        print(f"ERROR loading face: {str(e)}")
                else:
                    print(f"ERROR: Photo file not found: {photo_path}")
            
            print(f"\nLoaded {len(self.known_face_names)} faces")
            print(f"Known names: {self.known_face_names}")
            
        except Exception as e:
            print(f"Error loading faces: {str(e)}")
            if hasattr(self, 'info_label'):
                self.info_label.configure(text="Failed to load faces")

    def debug_user_data(self):
        """Debug function for user data"""
        print("\n=== DEBUG: User Data ===")
        users = self.db.get_users()
        print(f"Total users in database: {len(users)}")
        
        for user in users:
            print(f"\nUser name: {user['name']}")
            print(f"Photo path: {user['photo_path']}")
            full_path = os.path.join("data", "user_faces", user['photo_path'])
            print(f"Full path exists: {os.path.exists(full_path)}")

    def cleanup_user_faces(self):
        """Cleanup unused face images"""
        try:
            print("\n=== Cleaning up user_faces folder ===")
            users = self.db.get_users()
            valid_photos = [user['photo_path'] for user in users]
            print(f"Valid photos in database: {valid_photos}")
            
            user_faces_dir = os.path.join("data", "user_faces")
            if os.path.exists(user_faces_dir):
                for file in os.listdir(user_faces_dir):
                    if file not in valid_photos:
                        file_path = os.path.join(user_faces_dir, file)
                        print(f"Removing unused photo: {file}")
                        try:
                            os.remove(file_path)
                            print(f"Successfully removed {file}")
                        except Exception as e:
                            print(f"Error removing {file}: {str(e)}")
            else:
                print(f"Directory not found: {user_faces_dir}")
            
            print("Cleanup complete")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    def reload_faces(self):
        """Reload faces and cleanup"""
        try:
            print("\n=== Reloading Faces ===")
            self.show_loading("Reloading faces...")
            
            # Disable buttons during reload
            self.record_button.config(state='disabled')
            self.admin_button.config(state='disabled')
            self.reload_button.config(state='disabled')
            
            self.cleanup_user_faces()
            self.load_known_faces()
            self.spoof_detector.reset()
            self.frame_skip = 0
            
            self.hide_loading()
            
            # Re-enable buttons
            self.admin_button.config(state='normal')
            self.reload_button.config(state='normal')
            
            messagebox.showinfo("Success", "Face data reloaded successfully")
            
        except Exception as e:
            print(f"Error reloading faces: {str(e)}")
            self.hide_loading()
            messagebox.showerror("Error", "Failed to reload face data")
            
            # Re-enable buttons on error
            self.admin_button.config(state='normal')
            self.reload_button.config(state='normal')

    def open_admin_panel(self):
        """Open admin panel"""
        try:
            self.show_loading("Opening admin panel...")
            from src.admin_login import AdminLogin
            AdminLogin(self.db)
            self.hide_loading()
            
        except Exception as e:
            print(f"Error opening admin panel: {str(e)}")
            self.hide_loading()
            messagebox.showerror("Error", "Failed to open admin panel")

    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'camera'):
                self.camera.release()
                cv2.destroyAllWindows()
                print("Camera resources released")
        except Exception as e:
            print(f"Error cleaning up resources: {str(e)}")


if __name__ == "__main__":
    try:
        print("\n=== Starting Face Recognition Attendance System ===")
        app = AttendanceSystem()
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        messagebox.showerror("Error", f"Failed to start application: {str(e)}")                