import cv2
import numpy as np
import face_recognition
import logging
import time

class AntiSpoofingDetector:
    def __init__(self):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Movement detection parameters
        self.prev_landmarks = None
        self.movement_history = []
        self.movement_threshold = 0.15  # Sensitive enough to detect small movements
        self.required_movements = 2     # Only need 2 significant movements
        self.movement_passed = False
        
        # Performance optimization
        self.last_check_time = time.time()
        self.check_interval = 0.1  # Check every 100ms
        self.last_result = None

    def calculate_movement(self, landmarks1, landmarks2):
        """Calculate movement between two sets of landmarks"""
        if landmarks1 is None or landmarks2 is None:
            return 0
            
        try:
            # Calculate movement using nose point for simplicity
            nose_point1 = np.mean(landmarks1['nose_bridge'], axis=0)
            nose_point2 = np.mean(landmarks2['nose_bridge'], axis=0)
            
            # Calculate Euclidean distance
            movement = np.linalg.norm(nose_point1 - nose_point2)
            
            # Normalize by face size
            face_size = np.linalg.norm(
                np.mean(landmarks1['left_eye'], axis=0) - 
                np.mean(landmarks1['right_eye'], axis=0)
            )
            
            if face_size > 0:
                normalized_movement = movement / face_size
                return normalized_movement
            return 0
            
        except Exception as e:
            logging.error(f"Movement calculation error: {str(e)}")
            return 0

    def check_movement(self, frame):
        """Check for natural head movement"""
        try:
            # Get facial landmarks
            face_landmarks = face_recognition.face_landmarks(frame)
            if not face_landmarks:
                return False
                
            current_landmarks = face_landmarks[0]
            
            if self.prev_landmarks is not None:
                # Calculate movement
                movement = self.calculate_movement(
                    self.prev_landmarks, 
                    current_landmarks
                )
                
                # Add to history
                self.movement_history.append(movement)
                
                # Keep only recent history
                if len(self.movement_history) > 10:
                    self.movement_history.pop(0)
                
                # Check for significant movements
                significant_movements = sum(
                    1 for m in self.movement_history 
                    if m > self.movement_threshold
                )
                
                if significant_movements >= self.required_movements:
                    self.movement_passed = True
            
            self.prev_landmarks = current_landmarks
            return self.movement_passed
            
        except Exception as e:
            logging.error(f"Movement check error: {str(e)}")
            return False

    def check_liveness(self, frame):
        """Check liveness with only movement detection"""
        try:
            # Rate limiting
            current_time = time.time()
            if (current_time - self.last_check_time) < self.check_interval:
                return self.last_result or (False, "Processing...", frame)
            
            self.last_check_time = current_time
            
            # Create copy for visualization
            visual_frame = frame.copy()
            
            # Only check movement
            movement_status = "✓" if self.check_movement(frame) else "✗"
            is_live = self.movement_passed
            
            # Create status message
            message = f"Movement[{movement_status}]"
            
            # Add visualization
            cv2.putText(
                visual_frame,
                "REAL" if is_live else "FAKE",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0) if is_live else (0, 0, 255),
                2
            )
            
            # Store result
            self.last_result = (is_live, message, visual_frame)
            return self.last_result
            
        except Exception as e:
            logging.error(f"Liveness check error: {str(e)}")
            return False, "Error", frame

    def reset(self):
        """Reset all checks"""
        self.prev_landmarks = None
        self.movement_history = []
        self.movement_passed = False
        self.last_result = None